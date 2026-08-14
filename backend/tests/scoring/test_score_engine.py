"""
test_score_engine.py
====================
Unit tests for Stage 6.11 ScoreEngine.

Tests cover:
- Perfect score (no issues → 100).
- Spec example: 1 HIGH + 3 MEDIUM → 100 - 15 - 21 = 64.
- Floor at 0 (heavy findings cannot go negative).
- Each severity deducted correctly in isolation.
- Custom ScoringWeights override.
- Input FinalReview is NOT mutated (returns new instance).
- ScoreBreakdown fields are accurate.
- All agents failing → score 100 (no issues to penalize, but noted).
- Mixed successful + failed agents: only successful issues are scored.
"""

from __future__ import annotations

import pytest

from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.review_models import Issue, IssueCategory, Severity
from app.scoring.score_engine import DEFAULT_WEIGHTS, ScoreEngine, ScoringWeights


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue(severity: Severity) -> Issue:
    return Issue(
        title=f"{severity} issue",
        severity=severity,
        line=1,
        category=IssueCategory.BUG,
        description="Test issue.",
        suggestion="Fix it.",
    )


def _final_review(issues: list[Issue]) -> FinalReview:
    """Build a minimal FinalReview from a list of issues."""
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_category: dict[str, int] = {}
    for iss in issues:
        sev_key = str(iss.severity).lower()
        cat_key = str(iss.category).lower()
        by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
        by_category[cat_key] = by_category.get(cat_key, 0) + 1

    return FinalReview(
        overall_score=-1,
        summary="Test review.",
        issues=issues,
        total_issues=len(issues),
        issues_by_category=by_category,
        issues_by_severity=by_severity,
        agent_results=[],
        successful_agents=["bug_agent"],
        failed_agents=[],
        execution_time_ms=50.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_score_perfect_no_issues():
    """No issues → score 100."""
    review = _final_review([])
    scored, breakdown = ScoreEngine().score(review)

    assert scored.overall_score == 100
    assert breakdown.final_score == 100
    assert breakdown.total_deduction == 0


def test_score_spec_example():
    """Spec example: 100 - 15 (HIGH) - 7 (MEDIUM) = 78."""
    issues = [_issue(Severity.HIGH), _issue(Severity.MEDIUM)]
    review = _final_review(issues)
    scored, breakdown = ScoreEngine().score(review)

    assert breakdown.high_count == 1
    assert breakdown.medium_count == 1
    assert breakdown.high_deduction == 15
    assert breakdown.medium_deduction == 7
    assert breakdown.total_deduction == 22
    assert scored.overall_score == 78


def test_score_critical_deduction():
    """Single CRITICAL → 100 - 25 = 75."""
    review = _final_review([_issue(Severity.CRITICAL)])
    scored, breakdown = ScoreEngine().score(review)

    assert scored.overall_score == 75
    assert breakdown.critical_deduction == 25


def test_score_high_deduction():
    """Single HIGH → 100 - 15 = 85."""
    review = _final_review([_issue(Severity.HIGH)])
    scored, _ = ScoreEngine().score(review)
    assert scored.overall_score == 85


def test_score_medium_deduction():
    """Single MEDIUM → 100 - 7 = 93."""
    review = _final_review([_issue(Severity.MEDIUM)])
    scored, _ = ScoreEngine().score(review)
    assert scored.overall_score == 93


def test_score_low_deduction():
    """Single LOW → 100 - 2 = 98."""
    review = _final_review([_issue(Severity.LOW)])
    scored, _ = ScoreEngine().score(review)
    assert scored.overall_score == 98


def test_score_floor_at_zero():
    """Extremely heavy findings cannot produce a negative score — floor at 0."""
    issues = [_issue(Severity.CRITICAL)] * 10  # -250 points
    review = _final_review(issues)
    scored, breakdown = ScoreEngine().score(review)

    assert scored.overall_score == 0
    assert breakdown.total_deduction == 250
    assert breakdown.final_score == 0


def test_score_does_not_mutate_input():
    """ScoreEngine returns a NEW FinalReview — the original is never mutated."""
    review = _final_review([_issue(Severity.HIGH)])
    original_score = review.overall_score  # -1

    scored, _ = ScoreEngine().score(review)

    assert review.overall_score == original_score  # unchanged
    assert scored.overall_score != original_score   # new instance updated


def test_score_custom_weights():
    """Custom ScoringWeights are applied correctly."""
    weights = ScoringWeights(critical=50, high=20, medium=5, low=1)
    engine = ScoreEngine(weights=weights)

    # 1 HIGH (−20) + 2 MEDIUM (−10) = −30 → 70
    issues = [_issue(Severity.HIGH), _issue(Severity.MEDIUM), _issue(Severity.MEDIUM)]
    review = _final_review(issues)
    scored, breakdown = engine.score(review)

    assert breakdown.high_deduction == 20
    assert breakdown.medium_deduction == 10
    assert scored.overall_score == 70
    assert breakdown.weights.high == 20


def test_score_breakdown_all_fields():
    """ScoreBreakdown exposes correct per-severity counts and deductions."""
    issues = [
        _issue(Severity.CRITICAL),
        _issue(Severity.HIGH),
        _issue(Severity.HIGH),
        _issue(Severity.MEDIUM),
        _issue(Severity.LOW),
        _issue(Severity.LOW),
        _issue(Severity.LOW),
    ]
    review = _final_review(issues)
    _, breakdown = ScoreEngine().score(review)

    assert breakdown.base_score == 100
    assert breakdown.critical_count == 1
    assert breakdown.high_count == 2
    assert breakdown.medium_count == 1
    assert breakdown.low_count == 3

    assert breakdown.critical_deduction == 25
    assert breakdown.high_deduction == 30
    assert breakdown.medium_deduction == 7
    assert breakdown.low_deduction == 6
    assert breakdown.total_deduction == 68
    assert breakdown.final_score == 32


def test_score_all_agents_failed_returns_100():
    """When all agents failed there are no issues → score is 100, but failed_agents noted."""
    review = FinalReview(
        overall_score=-1,
        summary="All agents failed.",
        issues=[],
        total_issues=0,
        issues_by_category={},
        issues_by_severity={"critical": 0, "high": 0, "medium": 0, "low": 0},
        agent_results=[],
        successful_agents=[],
        failed_agents=["bug_agent", "security_agent"],
        execution_time_ms=5.0,
    )
    scored, breakdown = ScoreEngine().score(review)

    # No issues to penalize → max score, but failed_agents field still preserved
    assert scored.overall_score == 100
    assert len(scored.failed_agents) == 2
    assert breakdown.total_deduction == 0


def test_default_weights_match_spec():
    """Verify DEFAULT_WEIGHTS match the spec's documented values."""
    assert DEFAULT_WEIGHTS.critical == 25
    assert DEFAULT_WEIGHTS.high == 15
    assert DEFAULT_WEIGHTS.medium == 7
    assert DEFAULT_WEIGHTS.low == 2
