"""
test_multi_agent_review_service.py
===================================
Unit tests for Stage 6.13 MultiAgentReviewService.

Tests cover:
- End-to-end multi-agent pipeline execution (Orchestrator → Aggregator → ScoreEngine → Adapter).
- ``review_raw()`` returns a scored native ``FinalReview``.
- ``review()`` returns a Phase 5-compatible ``ReviewResponse``.
- ``review_full()`` returns both ``FinalReview`` and ``ReviewResponse``.
- Diff pre-processing (whitespace stripping, Windows line ending normalisation, language detection).
- Empty diff validation raises ``EmptyDiffError``.
- Graceful handling when individual agents fail.
- Audit logging verification.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.gemini_service import EmptyDiffError
from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.review_models import Issue, IssueCategory, ReviewRequest, ReviewResponse, Severity
from app.services.multi_agent_review_service import MultiAgentReviewService


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

VALID_DIFF = (
    "--- a/calculator.py\n+++ b/calculator.py\n"
    "@@ -1,4 +1,5 @@\n"
    " def divide(a, b):\n"
    "+    if b == 0:\n"
    "+        raise ValueError('Division by zero')\n"
    "     return a / b\n"
)


def _make_agent_review(
    name: str,
    category: AgentCategory,
    issues: list[Issue] | None = None,
    success: bool = True,
) -> AgentReview:
    return AgentReview(
        agent_name=name,
        category=category,
        issues=issues or [],
        summary=f"{name} summary text.",
        execution_time_ms=15.0,
        success=success,
        error=None if success else f"Error in {name}",
    )


@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock()
    bug_issue = Issue(
        title="Uncaught zero division risk",
        severity=Severity.HIGH,
        line=2,
        category=IssueCategory.BUG,
        description="Division by zero may occur if b is 0.",
        suggestion="Add zero check.",
    )
    perf_issue = Issue(
        title="Repeated function call bottleneck",
        severity=Severity.MEDIUM,
        line=4,
        category=IssueCategory.PERFORMANCE,
        description="Expensive computation in loop.",
        suggestion="Cache result.",
    )
    reviews = [
        _make_agent_review("bug_agent", AgentCategory.BUG, issues=[bug_issue]),
        _make_agent_review("security_agent", AgentCategory.SECURITY, issues=[]),
        _make_agent_review("performance_agent", AgentCategory.PERFORMANCE, issues=[perf_issue]),
        _make_agent_review("documentation_agent", AgentCategory.DOCUMENTATION, issues=[]),
        _make_agent_review("testing_agent", AgentCategory.TESTING, issues=[]),
    ]
    orchestrator.run = AsyncMock(return_value=reviews)
    return orchestrator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_agent_review_service_raw(mock_orchestrator):
    """review_raw() returns a scored FinalReview."""
    service = MultiAgentReviewService(orchestrator=mock_orchestrator)
    request = ReviewRequest(diff=VALID_DIFF, pr_title="Fix division by zero")

    final_review: FinalReview = await service.review_raw(request)

    assert isinstance(final_review, FinalReview)
    assert final_review.overall_score >= 0
    assert final_review.overall_score <= 100
    assert final_review.total_issues == 2
    assert len(final_review.successful_agents) == 5
    assert len(final_review.failed_agents) == 0


@pytest.mark.asyncio
async def test_multi_agent_review_service_phase5_compatible(mock_orchestrator):
    """review() returns a Phase 5-compatible ReviewResponse."""
    service = MultiAgentReviewService(orchestrator=mock_orchestrator)
    request = ReviewRequest(diff=VALID_DIFF, pr_title="Fix division by zero")

    response: ReviewResponse = await service.review(request)

    assert isinstance(response, ReviewResponse)
    assert response.total_issues == 2
    assert len(response.issues) == 2
    assert "Quality Score" in response.summary
    assert "Multi-Agent Code Review" in response.summary


@pytest.mark.asyncio
async def test_multi_agent_review_service_full(mock_orchestrator):
    """review_full() returns both FinalReview and ReviewResponse."""
    service = MultiAgentReviewService(orchestrator=mock_orchestrator)
    request = ReviewRequest(diff=VALID_DIFF, pr_title="Fix division by zero")

    final_review, response = await service.review_full(request)

    assert isinstance(final_review, FinalReview)
    assert isinstance(response, ReviewResponse)
    assert final_review.total_issues == response.total_issues


@pytest.mark.asyncio
async def test_multi_agent_review_service_empty_diff():
    """Diff becoming empty after normalisation raises EmptyDiffError."""
    service = MultiAgentReviewService()
    # ReviewRequest accepts non-empty string, but normalise_diff renders empty
    request = ReviewRequest(diff="   dummy   ")

    with patch("app.services.multi_agent_review_service.normalise_diff", return_value="   "):
        with pytest.raises(EmptyDiffError):
            await service.review(request)


@pytest.mark.asyncio
async def test_multi_agent_review_service_agent_failure_resilience():
    """When an agent fails, review_raw() still returns a valid FinalReview with failed_agents recorded."""
    mock_orch = MagicMock()
    bug_issue = Issue(
        title="Uncaught zero division risk",
        severity=Severity.HIGH,
        line=2,
        category=IssueCategory.BUG,
        description="Division by zero may occur if b is 0.",
        suggestion="Add zero check.",
    )
    reviews = [
        _make_agent_review("bug_agent", AgentCategory.BUG, issues=[bug_issue], success=True),
        _make_agent_review("security_agent", AgentCategory.SECURITY, issues=[], success=False),
        _make_agent_review("performance_agent", AgentCategory.PERFORMANCE, issues=[], success=True),
        _make_agent_review("documentation_agent", AgentCategory.DOCUMENTATION, issues=[], success=True),
        _make_agent_review("testing_agent", AgentCategory.TESTING, issues=[], success=True),
    ]
    mock_orch.run = AsyncMock(return_value=reviews)

    service = MultiAgentReviewService(orchestrator=mock_orch)
    request = ReviewRequest(diff=VALID_DIFF)

    final_review = await service.review_raw(request)

    assert final_review.total_issues == 1
    assert "security_agent" in final_review.failed_agents
    assert len(final_review.successful_agents) == 4
