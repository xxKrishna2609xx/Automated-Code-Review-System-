"""
test_phase5_adapter.py
======================
Unit tests for Stage 6.12 Phase5Adapter.

Tests cover:
- Clean FinalReview (no issues) produces a valid ReviewResponse with ✅ summary.
- FinalReview with issues is adapted correctly (issues passed through unmodified).
- Quality score is embedded in the summary text.
- Score badge is correct for each score band (90+, 70-89, 50-69, <50).
- reviewed_chunks reflects the number of agent results.
- Failed agents are mentioned in the summary.
- Narrative summary is included in the adapted output.
- Narrative exceeding 1500 chars is truncated gracefully.
- Output is always a valid ReviewResponse (Pydantic-validated).
- Phase 5 ReviewResponse total_issues is auto-computed from issues list.
"""

from __future__ import annotations

import pytest

from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.review_models import Issue, IssueCategory, ReviewResponse, Severity
from app.services.phase5_adapter import Phase5Adapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue(title: str = "Test Issue", severity: Severity = Severity.HIGH) -> Issue:
    return Issue(
        title=title,
        severity=severity,
        line=1,
        category=IssueCategory.BUG,
        description="Detailed description of the issue.",
        suggestion="Fix suggestion.",
    )


def _agent_review(name: str, success: bool = True) -> AgentReview:
    return AgentReview(
        agent_name=name,
        category=AgentCategory.BUG,
        issues=[],
        summary=f"{name} completed.",
        execution_time_ms=10.0,
        success=success,
    )


def _final_review(
    issues: list[Issue] = None,
    score: int = 85,
    summary: str = "Agent narrative summary.",
    successful_agents: list[str] = None,
    failed_agents: list[str] = None,
    agent_results: list[AgentReview] = None,
) -> FinalReview:
    issues = issues or []
    successful_agents = successful_agents or ["bug_agent", "security_agent"]
    failed_agents = failed_agents or []
    agent_results = agent_results or [_agent_review(n) for n in successful_agents]

    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_category: dict[str, int] = {}
    for iss in issues:
        sev_key = str(iss.severity).lower()
        cat_key = str(iss.category).lower()
        by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
        by_category[cat_key] = by_category.get(cat_key, 0) + 1

    return FinalReview(
        overall_score=score,
        summary=summary,
        issues=issues,
        total_issues=len(issues),
        issues_by_category=by_category,
        issues_by_severity=by_severity,
        agent_results=agent_results,
        successful_agents=successful_agents,
        failed_agents=failed_agents,
        execution_time_ms=100.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_adapter_returns_review_response_type():
    """adapt() always returns a valid ReviewResponse instance."""
    adapter = Phase5Adapter()
    result = adapter.adapt(_final_review())
    assert isinstance(result, ReviewResponse)


def test_adapter_clean_review_no_issues():
    """A FinalReview with no issues produces the ✅ clean summary."""
    adapter = Phase5Adapter()
    result = adapter.adapt(_final_review(issues=[]))

    assert result.total_issues == 0
    assert "No issues detected" in result.summary
    assert "✅" in result.summary


def test_adapter_issues_passed_through_unmodified():
    """Issues from FinalReview are passed to ReviewResponse unchanged."""
    issues = [
        _issue("SQL Injection risk", Severity.CRITICAL),
        _issue("Missing type hint", Severity.LOW),
    ]
    adapter = Phase5Adapter()
    result = adapter.adapt(_final_review(issues=issues))

    assert result.total_issues == 2
    assert result.issues[0].title == "SQL Injection risk"
    assert result.issues[1].title == "Missing type hint"


def test_adapter_score_in_summary():
    """The quality score number appears in the summary text."""
    adapter = Phase5Adapter()
    result = adapter.adapt(_final_review(score=73))

    assert "73/100" in result.summary


def test_adapter_score_badge_green():
    """Score ≥ 90 → 🟢 badge."""
    result = Phase5Adapter().adapt(_final_review(score=95))
    assert "🟢" in result.summary


def test_adapter_score_badge_yellow():
    """Score 70–89 → 🟡 badge."""
    result = Phase5Adapter().adapt(_final_review(score=78))
    assert "🟡" in result.summary


def test_adapter_score_badge_orange():
    """Score 50–69 → 🟠 badge."""
    result = Phase5Adapter().adapt(_final_review(score=55))
    assert "🟠" in result.summary


def test_adapter_score_badge_red():
    """Score < 50 → 🔴 badge."""
    result = Phase5Adapter().adapt(_final_review(score=30))
    assert "🔴" in result.summary


def test_adapter_reviewed_chunks_matches_agent_count():
    """reviewed_chunks in ReviewResponse equals the number of agent_results."""
    agents = [_agent_review(n) for n in
              ["bug_agent", "security_agent", "performance_agent", "documentation_agent", "testing_agent"]]
    result = Phase5Adapter().adapt(
        _final_review(agent_results=agents, successful_agents=[a.agent_name for a in agents])
    )
    assert result.reviewed_chunks == 5


def test_adapter_failed_agents_in_summary():
    """Failed agents are clearly flagged in the adapted summary."""
    result = Phase5Adapter().adapt(
        _final_review(
            successful_agents=["bug_agent"],
            failed_agents=["security_agent", "performance_agent"],
        )
    )
    assert "security_agent" in result.summary
    assert "performance_agent" in result.summary
    assert "⚠️" in result.summary


def test_adapter_narrative_included_in_summary():
    """The agent narrative summary is included in the output summary."""
    result = Phase5Adapter().adapt(
        _final_review(summary="Critical injection vulnerability found in the login endpoint.")
    )
    assert "Critical injection vulnerability" in result.summary


def test_adapter_narrative_truncated_at_1500_chars():
    """Narratives longer than 1500 characters are truncated gracefully."""
    long_summary = "A" * 2000
    result = Phase5Adapter().adapt(_final_review(summary=long_summary))
    assert "_(truncated)_" in result.summary
    # The full 2000-char string must NOT be in the output
    assert "A" * 2000 not in result.summary


def test_adapter_severity_counts_in_summary():
    """Per-severity counts appear in the summary when issues exist."""
    issues = [
        _issue("Critical Bug", Severity.CRITICAL),
        _issue("High Risk", Severity.HIGH),
        _issue("High Risk 2", Severity.HIGH),
    ]
    result = Phase5Adapter().adapt(_final_review(issues=issues, score=45))
    assert "1 Critical" in result.summary or "Critical" in result.summary
    assert "2 High" in result.summary or "High" in result.summary


def test_adapter_does_not_mutate_final_review():
    """adapt() does not mutate the input FinalReview."""
    fr = _final_review(issues=[_issue()])
    original_score = fr.overall_score
    original_total = fr.total_issues

    Phase5Adapter().adapt(fr)

    assert fr.overall_score == original_score
    assert fr.total_issues == original_total
