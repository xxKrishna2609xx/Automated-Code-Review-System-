"""
test_post_fix_review_service.py  (tests.fixes)
================================================
Unit tests for Stage 8.15 — PostFixReviewService.

Tests cover:
    - Post-fix Phase 6 multi-agent review execution
    - Construction and aggregation of post-fix FinalReview
    - Formatting into PersistedReview with correct review_key and metadata
    - Repository upsert integration
    - Error handling for missing fix requests

Author : AI Code Review Bot — Phase 8 (Stage 8.15)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.fixes.exceptions import FixNotFoundError
from app.fixes.fix_service import _FIX_REQUEST_STORE, reset_fix_stores
from app.fixes.models import FixRequest, FixStatus
from app.fixes.post_fix_review_service import PostFixReviewService
from app.models.agent_models import AgentCategory, AgentReview
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

BASE_SHA = "a" * 40
POST_FIX_DIFF = "@@ -2,1 +2,1 @@\n-    return a - b\n+    return a + b\n"


def _make_fix_request() -> FixRequest:
    return FixRequest(
        id="fix-req-postfix123",
        review_id="rev-456",
        issue_id="bug-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="math_utils.py",
        issue_title="Incorrect operator",
        issue_description="Subtractions used instead of addition.",
        suggestion="Use + operator.",
        status=FixStatus.COMMITTED,
    )


def _make_agent_reviews(issues: list[Issue] | None = None) -> list[AgentReview]:
    return [
        AgentReview(
            agent_name="bug_agent",
            category=AgentCategory.BUG,
            success=True,
            issues=issues or [],
            summary="Post-fix bug review clean.",
        ),
        AgentReview(
            agent_name="security_agent",
            category=AgentCategory.SECURITY,
            success=True,
            issues=[],
            summary="Post-fix security review clean.",
        ),
    ]



@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# PostFixReviewService Tests
# ---------------------------------------------------------------------------

class TestPostFixReviewService:
    @pytest.mark.asyncio
    async def test_execute_post_fix_review_success(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=_make_agent_reviews())

        mock_repo = MagicMock()
        mock_repo.upsert_review = AsyncMock(side_effect=lambda r: r)

        svc = PostFixReviewService(
            orchestrator=mock_orchestrator,
            repository=mock_repo,
        )

        persisted = await svc.execute_post_fix_review(
            fix_request_id=fix_req.id,
            post_fix_diff=POST_FIX_DIFF,
            commit_sha="b" * 40,
        )

        assert isinstance(persisted, PersistedReview)
        assert persisted.repository == "owner/repo"
        assert persisted.pull_request_number == 42
        assert persisted.commit_sha == "b" * 40
        assert persisted.review_key == "owner/repo#42@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

        mock_orchestrator.run.assert_awaited_once()
        mock_repo.upsert_review.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_post_fix_review_detects_new_issues(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        new_issue = Issue(
            title="New unused import introduced",
            severity="Low",
            category="Code Smell",
            description="Unused import os added.",
            suggestion="Remove unused import.",
            line=1,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=_make_agent_reviews([new_issue]))

        svc = PostFixReviewService(orchestrator=mock_orchestrator)

        persisted = await svc.execute_post_fix_review(
            fix_request_id=fix_req.id,
            post_fix_diff=POST_FIX_DIFF,
        )

        assert len(persisted.issues) >= 1
        assert any(i.title == "New unused import introduced" for i in persisted.issues)

    @pytest.mark.asyncio
    async def test_execute_post_fix_review_nonexistent_request_raises_404(self):
        svc = PostFixReviewService()
        with pytest.raises(FixNotFoundError):
            await svc.execute_post_fix_review("nonexistent-id", POST_FIX_DIFF)
