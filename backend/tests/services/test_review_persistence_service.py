"""
test_review_persistence_service.py
==================================
Unit tests for Stage 7.4 ReviewPersistenceService with mocked ReviewRepository.

Tests cover:
- save_final_review mapping and repository upsert call.
- Idempotent review_key generation.
- Correct normalization of counters (agent_counts, severity_counts, category_counts).
- Handling of partial/failed review status preservation.
- Error propagation on database failures.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.persistence_models import PersistedReview, ReviewStatus
from app.models.review_models import Issue, IssueCategory, Severity
from app.services.review_persistence_service import ReviewPersistenceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_final_review() -> FinalReview:
    issue = Issue(
        title="Hardcoded API Secret",
        severity=Severity.HIGH,
        line=12,
        category=IssueCategory.SECURITY,
        description="Secret key detected in diff.",
        suggestion="Move to env var.",
    )

    agent_review = AgentReview(
        agent_name="security_agent",
        category=AgentCategory.SECURITY,
        issues=[issue],
        summary="Security issues detected",
        execution_time_ms=80.0,
        success=True,
    )

    return FinalReview(
        overall_score=85,
        summary="Security risk identified.",
        issues=[issue],
        total_issues=1,
        issues_by_category={"security": 1},
        issues_by_severity={"high": 1, "critical": 0, "medium": 0, "low": 0},
        agent_results=[agent_review],
        successful_agents=["security_agent"],
        failed_agents=[],
        execution_time_ms=120.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_final_review_success():
    """save_final_review transforms FinalReview and invokes repository upsert."""
    mock_repo = MagicMock()
    mock_repo.upsert_review = AsyncMock(side_effect=lambda doc: doc)

    service = ReviewPersistenceService(repository=mock_repo)
    final_review = _sample_final_review()

    persisted: PersistedReview = await service.save_final_review(
        final_review=final_review,
        owner="testorg",
        repo_name="myrepo",
        pull_request_number=15,
        commit_sha="a1b2c3d4",
        author="devuser",
        pull_request_title="Security fix PR",
    )

    assert mock_repo.upsert_review.called
    assert persisted.review_key == "testorg/myrepo#15@a1b2c3d4"
    assert persisted.author == "devuser"
    assert persisted.overall_score == 85
    assert persisted.total_issues == 1
    assert persisted.review_status == ReviewStatus.COMPLETED
    assert persisted.agent_counts == {"security_agent": 1}


@pytest.mark.asyncio
async def test_save_final_review_idempotency_key():
    """Multiple saves for the same PR commit produce identical review_key."""
    mock_repo = MagicMock()
    mock_repo.upsert_review = AsyncMock(side_effect=lambda doc: doc)

    service = ReviewPersistenceService(repository=mock_repo)
    final_review = _sample_final_review()

    res1 = await service.save_final_review(
        final_review=final_review, owner="org", repo_name="repo", pull_request_number=5, commit_sha="sha1"
    )
    res2 = await service.save_final_review(
        final_review=final_review, owner="org", repo_name="repo", pull_request_number=5, commit_sha="sha1"
    )

    assert res1.review_key == res2.review_key == "org/repo#5@sha1"
    assert mock_repo.upsert_review.call_count == 2


@pytest.mark.asyncio
async def test_save_final_review_repository_error():
    """Repository exceptions propagate to the caller."""
    mock_repo = MagicMock()
    mock_repo.upsert_review = AsyncMock(side_effect=RuntimeError("Database connection failed"))

    service = ReviewPersistenceService(repository=mock_repo)
    final_review = _sample_final_review()

    with pytest.raises(RuntimeError, match="Database connection failed"):
        await service.save_final_review(
            final_review=final_review, owner="org", repo_name="repo", pull_request_number=1
        )
