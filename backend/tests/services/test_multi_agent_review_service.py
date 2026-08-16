"""
test_multi_agent_review_service.py
===================================
Unit tests for MultiAgentReviewService (Phase 6 & Phase 7 Integration).

Tests cover:
- End-to-end multi-agent pipeline execution (Orchestrator → Aggregator → ScoreEngine → Adapter).
- ``review_raw()`` returns a scored native ``FinalReview``.
- ``review()`` returns a Phase 5-compatible ``ReviewResponse``.
- ``review_full()`` returns both ``FinalReview`` and ``ReviewResponse``.
- Stage 7.5: ``review_and_persist()`` success, failure handling, duplicate execution, and partial failure.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.gemini_service import EmptyDiffError
from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.persistence_models import ReviewStatus
from app.models.review_models import Issue, IssueCategory, ReviewRequest, ReviewResponse, Severity
from app.services.multi_agent_review_service import MultiAgentReviewService
from app.services.review_persistence_service import ReviewPersistenceError


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
# Phase 6 Core Tests
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


# ---------------------------------------------------------------------------
# Stage 7.5 Integration Tests (Phase 6 + Persistence)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_and_persist_success(mock_orchestrator):
    """review_and_persist executes review and persists doc successfully."""
    mock_persist_svc = MagicMock()
    mock_persist_svc.save_final_review = AsyncMock(
        side_effect=lambda final_review, **kwargs: MagicMock(
            review_key=f"{kwargs['owner']}/{kwargs['repo_name']}#{kwargs['pull_request_number']}@{kwargs.get('commit_sha') or 'head'}",
            review_status=ReviewStatus.COMPLETED,
        )
    )

    service = MultiAgentReviewService(
        orchestrator=mock_orchestrator,
        persistence_service=mock_persist_svc,
    )
    request = ReviewRequest(diff=VALID_DIFF, pr_title="PR title")

    final_review, persisted = await service.review_and_persist(
        request=request,
        owner="myorg",
        repo_name="myrepo",
        pull_request_number=10,
        commit_sha="c1c2c3",
        author="alice",
    )

    assert final_review.total_issues == 2
    assert persisted.review_key == "myorg/myrepo#10@c1c2c3"
    assert mock_persist_svc.save_final_review.called


@pytest.mark.asyncio
async def test_review_and_persist_failure_handling(mock_orchestrator):
    """When persistence fails, ReviewPersistenceError is raised (never silently masked)."""
    mock_persist_svc = MagicMock()
    mock_persist_svc.save_final_review = AsyncMock(side_effect=RuntimeError("MongoDB write error"))

    service = MultiAgentReviewService(
        orchestrator=mock_orchestrator,
        persistence_service=mock_persist_svc,
    )
    request = ReviewRequest(diff=VALID_DIFF)

    with pytest.raises(ReviewPersistenceError, match="Review persistence failed"):
        await service.review_and_persist(
            request=request,
            owner="myorg",
            repo_name="myrepo",
            pull_request_number=10,
        )


@pytest.mark.asyncio
async def test_review_and_persist_duplicate_execution(mock_orchestrator):
    """Duplicate review_and_persist calls for same PR commit use identical review_key."""
    mock_persist_svc = MagicMock()
    saved_keys = []

    async def _mock_save(final_review, **kwargs):
        key = f"{kwargs['owner']}/{kwargs['repo_name']}#{kwargs['pull_request_number']}@{kwargs['commit_sha']}"
        saved_keys.append(key)
        return MagicMock(review_key=key)

    mock_persist_svc.save_final_review = AsyncMock(side_effect=_mock_save)

    service = MultiAgentReviewService(
        orchestrator=mock_orchestrator,
        persistence_service=mock_persist_svc,
    )
    request = ReviewRequest(diff=VALID_DIFF)

    _, p1 = await service.review_and_persist(
        request=request, owner="org", repo_name="repo", pull_request_number=5, commit_sha="abc1234"
    )
    _, p2 = await service.review_and_persist(
        request=request, owner="org", repo_name="repo", pull_request_number=5, commit_sha="abc1234"
    )

    assert p1.review_key == p2.review_key == "org/repo#5@abc1234"
    assert len(saved_keys) == 2


@pytest.mark.asyncio
async def test_review_and_persist_partial_agent_failure():
    """Partial agent failure persists review with PARTIAL status."""
    mock_orch = MagicMock()
    reviews = [
        _make_agent_review("bug_agent", AgentCategory.BUG, issues=[], success=True),
        _make_agent_review("security_agent", AgentCategory.SECURITY, issues=[], success=False),
    ]
    mock_orch.run = AsyncMock(return_value=reviews)

    mock_persist_svc = MagicMock()

    async def _mock_save(final_review, **kwargs):
        status = ReviewStatus.PARTIAL if final_review.failed_agents else ReviewStatus.COMPLETED
        return MagicMock(review_status=status)

    mock_persist_svc.save_final_review = AsyncMock(side_effect=_mock_save)

    service = MultiAgentReviewService(
        orchestrator=mock_orch,
        persistence_service=mock_persist_svc,
    )
    request = ReviewRequest(diff=VALID_DIFF)

    final_review, persisted = await service.review_and_persist(
        request=request, owner="org", repo_name="repo", pull_request_number=1
    )

    assert "security_agent" in final_review.failed_agents
    assert persisted.review_status == ReviewStatus.PARTIAL
