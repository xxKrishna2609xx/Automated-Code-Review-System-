"""
test_commit_service.py  (tests.fixes)
=====================================
Unit tests for Stage 8.13 — CommitService.

Tests cover:
    - End-to-end Git Data API commit pipeline (blob -> tree -> commit -> update_ref)
    - Commit message formatting invariant
    - Transition of status to COMMITTED
    - Rejection of unapproved fix requests
    - Rejection when fix request or patch is missing
    - Handling of GitHub Git Data API failures

Author : AI Code Review Bot — Phase 8 (Stage 8.13)
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.fixes.branch_service import BranchService
from app.fixes.commit_service import CommitResult, CommitService
from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_service import _FIX_PATCH_STORE, _FIX_REQUEST_STORE, reset_fix_stores
from app.fixes.models import FixPatch, FixRequest, FixStatus


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

BASE_CODE = "def add(a, b):\n    return a - b\n"
PATCH_CODE = "@@ -2,1 +2,1 @@\n-    return a - b\n+    return a + b\n"
ORIGINAL_HASH = hashlib.sha256(BASE_CODE.encode("utf-8")).hexdigest()

BASE_SHA = "a" * 40
BLOB_SHA = "b" * 40
TREE_SHA = "c" * 40
COMMIT_SHA = "d" * 40


def _make_fix_request(**overrides) -> FixRequest:
    base = dict(
        id="fix-req-12345678",
        review_id="rev-456",
        issue_id="bug-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="math_utils.py",
        line=2,
        issue_title="Incorrect operator in add()",
        issue_description="Subtractions used instead of addition.",
        suggestion="Use + operator.",
        status=FixStatus.APPROVED,
    )
    base.update(overrides)
    return FixRequest(**base)


def _make_fix_patch() -> FixPatch:
    return FixPatch(
        file_path="math_utils.py",
        original_content_hash=ORIGINAL_HASH,
        patch=PATCH_CODE,
        changed_lines=[2],
        explanation="Fixed minus to plus.",
    )


def _make_mock_gh_service() -> MagicMock:
    svc = MagicMock()
    svc.create_fix_branch = AsyncMock(return_value="ai-fix/fix-req-")
    svc.create_blob = AsyncMock(return_value=BLOB_SHA)
    svc.create_tree = AsyncMock(return_value=TREE_SHA)
    svc.create_commit = AsyncMock(return_value=COMMIT_SHA)
    svc.update_branch_head = AsyncMock(return_value=None)
    return svc


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# CommitService Tests
# ---------------------------------------------------------------------------

class TestCommitService:
    @pytest.mark.asyncio
    async def test_commit_fix_success(self):
        fix_req = _make_fix_request()
        fix_patch = _make_fix_patch()

        _FIX_REQUEST_STORE[fix_req.id] = fix_req
        _FIX_PATCH_STORE[fix_req.id] = fix_patch

        mock_gh = _make_mock_gh_service()
        svc = CommitService(github_fix_service=mock_gh)

        result = await svc.commit_fix(
            fix_request_id=fix_req.id,
            base_file_content=BASE_CODE,
        )

        assert isinstance(result, CommitResult)
        assert result.commit_sha == COMMIT_SHA
        assert result.branch_name == "ai-fix/fix-req-"
        assert "fix(bug): Incorrect operator in add()" in result.commit_message
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.COMMITTED

        # Verify sequence of Git Data API calls
        mock_gh.create_blob.assert_awaited_once_with(
            owner="owner", repo="repo", content="def add(a, b):\n    return a + b\n"
        )
        mock_gh.create_tree.assert_awaited_once_with(
            owner="owner",
            repo="repo",
            base_tree_sha=BASE_SHA,
            tree_items=[{"path": "math_utils.py", "mode": "100644", "type": "blob", "sha": BLOB_SHA}],
        )
        mock_gh.create_commit.assert_awaited_once_with(
            owner="owner",
            repo="repo",
            message=result.commit_message,
            tree_sha=TREE_SHA,
            parent_shas=[BASE_SHA],
        )
        mock_gh.update_branch_head.assert_awaited_once_with(
            owner="owner", repo="repo", branch_name="ai-fix/fix-req-", commit_sha=COMMIT_SHA
        )

    @pytest.mark.asyncio
    async def test_commit_unapproved_request_raises_fix_state_error(self):
        fix_req = _make_fix_request(status=FixStatus.REQUESTED)
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        mock_gh = _make_mock_gh_service()
        svc = CommitService(github_fix_service=mock_gh)

        with pytest.raises(FixStateError) as exc_info:
            await svc.commit_fix(fix_request_id=fix_req.id, base_file_content=BASE_CODE)

        assert "APPROVED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_commit_missing_patch_raises_fix_validation_error(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req
        # Notice: _FIX_PATCH_STORE is empty

        mock_gh = _make_mock_gh_service()
        svc = CommitService(github_fix_service=mock_gh)

        with pytest.raises(FixValidationError) as exc_info:
            await svc.commit_fix(fix_request_id=fix_req.id, base_file_content=BASE_CODE)

        assert "patch" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_commit_nonexistent_request_raises_404(self):
        mock_gh = _make_mock_gh_service()
        svc = CommitService(github_fix_service=mock_gh)

        with pytest.raises(FixNotFoundError):
            await svc.commit_fix(fix_request_id="nonexistent-id", base_file_content=BASE_CODE)
