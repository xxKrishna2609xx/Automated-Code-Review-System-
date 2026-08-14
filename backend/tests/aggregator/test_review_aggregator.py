"""
test_review_aggregator.py
=========================
Unit tests for Stage 6.9 + 6.10 ReviewAggregator.

Tests cover:
- Flattening issues from multiple successful agents.
- Excluding issues from failed agents.
- Deterministic deduplication (same category + line + title prefix).
- Duplicate resolution: highest severity wins.
- Severity ranking: CRITICAL → HIGH → MEDIUM → LOW.
- Category ranking within same severity: SECURITY > BUG > PERFORMANCE > BEST_PRACTICE.
- Breakdowns by category and severity (all 4 severity levels always present).
- Combined summary narrative from successful agents.
- Failed agents noted in summary and tracked in FinalReview.
- Empty agent list produces a valid empty FinalReview.
"""

from __future__ import annotations

import pytest

from app.aggregator.review_aggregator import ReviewAggregator
from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.review_models import Issue, IssueCategory, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue(
    title: str,
    severity: Severity,
    category: IssueCategory,
    line: int | None = None,
) -> Issue:
    return Issue(
        title=title,
        severity=severity,
        line=line,
        category=category,
        description=f"Description for {title}.",
        suggestion=f"Fix for {title}.",
    )


def _agent_review(
    name: str,
    category: AgentCategory,
    issues: list[Issue],
    success: bool = True,
    summary: str = "",
) -> AgentReview:
    return AgentReview(
        agent_name=name,
        category=category,
        issues=issues,
        summary=summary or f"{name} summary.",
        execution_time_ms=10.0,
        success=success,
        error=None if success else "Simulated error",
    )


# ---------------------------------------------------------------------------
# Stage 6.9 — Flattening & Collection
# ---------------------------------------------------------------------------

def test_aggregator_flattens_issues_from_all_agents():
    """All issues from successful agents are merged into a single list."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Off-by-one", Severity.HIGH, IssueCategory.BUG, line=10),
            _issue("Null pointer", Severity.MEDIUM, IssueCategory.BUG, line=20),
        ]),
        _agent_review("security_agent", AgentCategory.SECURITY, [
            _issue("SQL Injection", Severity.CRITICAL, IssueCategory.SECURITY, line=5),
        ]),
        _agent_review("performance_agent", AgentCategory.PERFORMANCE, []),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.total_issues == 3
    assert len(result.issues) == 3


def test_aggregator_excludes_failed_agent_issues():
    """Issues from failed agents are NOT included in the final review."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Real Bug", Severity.HIGH, IssueCategory.BUG, line=7),
        ], success=True),
        _agent_review("security_agent", AgentCategory.SECURITY, [
            _issue("This should be excluded", Severity.CRITICAL, IssueCategory.SECURITY),
        ], success=False),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.total_issues == 1
    assert result.issues[0].title == "Real Bug"
    assert "security_agent" in result.failed_agents
    assert "bug_agent" in result.successful_agents


def test_aggregator_empty_agent_list():
    """Empty input produces a valid FinalReview with zero issues."""
    result: FinalReview = ReviewAggregator().aggregate([])

    assert result.total_issues == 0
    assert result.issues == []
    assert result.successful_agents == []
    assert result.failed_agents == []
    assert result.overall_score == -1  # unscored until ScoreEngine runs


def test_aggregator_all_agents_fail():
    """All agents failing produces empty FinalReview with all names in failed_agents."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [], success=False),
        _agent_review("security_agent", AgentCategory.SECURITY, [], success=False),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.total_issues == 0
    assert len(result.failed_agents) == 2
    assert len(result.successful_agents) == 0
    assert "failed" in result.summary.lower()


# ---------------------------------------------------------------------------
# Stage 6.9 — Deduplication
# ---------------------------------------------------------------------------

def test_aggregator_deduplicates_identical_key():
    """Two issues with same (category, line, title prefix) are deduplicated to one."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Null pointer dereference", Severity.HIGH, IssueCategory.BUG, line=15),
        ]),
        _agent_review("security_agent", AgentCategory.SECURITY, [
            _issue("Null pointer dereference", Severity.MEDIUM, IssueCategory.BUG, line=15),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    # Should be deduplicated to 1 issue
    assert result.total_issues == 1


def test_aggregator_dedup_keeps_highest_severity():
    """When deduplicating, the issue with higher severity is preserved."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Null pointer dereference", Severity.MEDIUM, IssueCategory.BUG, line=15),
        ]),
        _agent_review("security_agent", AgentCategory.SECURITY, [
            _issue("Null pointer dereference", Severity.CRITICAL, IssueCategory.BUG, line=15),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.total_issues == 1
    assert result.issues[0].severity == Severity.CRITICAL


def test_aggregator_different_lines_not_deduplicated():
    """Issues on different lines are NOT considered duplicates even with same title."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Null pointer", Severity.HIGH, IssueCategory.BUG, line=10),
            _issue("Null pointer", Severity.HIGH, IssueCategory.BUG, line=20),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.total_issues == 2


# ---------------------------------------------------------------------------
# Stage 6.10 — Severity Ranking
# ---------------------------------------------------------------------------

def test_aggregator_ranks_severity_descending():
    """Issues are ordered CRITICAL → HIGH → MEDIUM → LOW."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Low issue", Severity.LOW, IssueCategory.BUG, line=1),
            _issue("Critical issue", Severity.CRITICAL, IssueCategory.BUG, line=2),
            _issue("Medium issue", Severity.MEDIUM, IssueCategory.BUG, line=3),
            _issue("High issue", Severity.HIGH, IssueCategory.BUG, line=4),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    severities = [i.severity for i in result.issues]
    assert severities[0] == Severity.CRITICAL
    assert severities[1] == Severity.HIGH
    assert severities[2] == Severity.MEDIUM
    assert severities[3] == Severity.LOW


def test_aggregator_category_rank_within_same_severity():
    """Within same severity, SECURITY comes before BUG before PERFORMANCE."""
    reviews = [
        _agent_review("mixed_agent", AgentCategory.BUG, [
            _issue("Performance problem", Severity.HIGH, IssueCategory.PERFORMANCE, line=5),
            _issue("Security vulnerability", Severity.HIGH, IssueCategory.SECURITY, line=6),
            _issue("Logic bug", Severity.HIGH, IssueCategory.BUG, line=7),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    categories = [i.category for i in result.issues]
    assert categories[0] == IssueCategory.SECURITY
    assert categories[1] == IssueCategory.BUG
    assert categories[2] == IssueCategory.PERFORMANCE


# ---------------------------------------------------------------------------
# Breakdowns & Summary
# ---------------------------------------------------------------------------

def test_aggregator_builds_severity_breakdown():
    """issues_by_severity always has all 4 severity levels present."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Critical bug", Severity.CRITICAL, IssueCategory.BUG),
            _issue("High bug", Severity.HIGH, IssueCategory.BUG),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.issues_by_severity["critical"] == 1
    assert result.issues_by_severity["high"] == 1
    assert result.issues_by_severity["medium"] == 0
    assert result.issues_by_severity["low"] == 0


def test_aggregator_builds_category_breakdown():
    """issues_by_category correctly groups counts by category."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [
            _issue("Bug A", Severity.HIGH, IssueCategory.BUG),
            _issue("Bug B", Severity.MEDIUM, IssueCategory.BUG),
        ]),
        _agent_review("security_agent", AgentCategory.SECURITY, [
            _issue("Sec A", Severity.CRITICAL, IssueCategory.SECURITY),
        ]),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert result.issues_by_category.get("Bug", 0) + result.issues_by_category.get("bug", 0) >= 2


def test_aggregator_summary_notes_failed_agents():
    """Failed agents are mentioned in the combined summary."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, [], success=True,
                      summary="No bugs found."),
        _agent_review("security_agent", AgentCategory.SECURITY, [], success=False),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews)

    assert "security_agent" in result.summary


def test_aggregator_preserves_agent_results():
    """All original AgentReview objects are preserved in agent_results for traceability."""
    reviews = [
        _agent_review("bug_agent", AgentCategory.BUG, []),
        _agent_review("security_agent", AgentCategory.SECURITY, []),
    ]

    result: FinalReview = ReviewAggregator().aggregate(reviews, execution_time_ms=123.4)

    assert len(result.agent_results) == 2
    assert result.execution_time_ms == 123.4
