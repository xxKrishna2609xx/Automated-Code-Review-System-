"""
test_branch_service.py  (tests.fixes)
=====================================
Unit tests for Stage 8.10 — Safe Branch Creation Service.

Tests cover:
    - Standardized branch naming convention (ai-fix/{fix_id_short})
    - Protection of default branch names (main, master, develop, etc.)
    - Successful branch creation for APPROVED fix requests
    - Status transition to APPLYING after branch creation
    - Rejection of branch creation when status is not APPROVED
    - Pre-creation staleness check (HEAD SHA mismatch -> status STALE & error)
    - GitHubClient create_git_ref integration & error handling

Author : AI Code Review Bot — Phase 8 (Stage 8.10)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.fixes.branch_service import (
    PROTECTED_BRANCH_NAMES,
    BranchService,
    generate_branch_name,
)
from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_service import _FIX_REQUEST_STORE, reset_fix_stores
from app.fixes.models import FixRequest, FixStatus


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

VALID_SHA = "a" * 40


def _make_fix_request(**overrides) -> FixRequest:
    base = dict(
        id="fix-req-12345678",
        review_id="rev-456",
        issue_id="security-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=VALID_SHA,
        file_path="app/database.py",
        line=42,
        issue_title="SQL Injection Risk",
        issue_description="Unsanitized user input in query.",
        suggestion="Use parameterized query.",
        status=FixStatus.APPROVED,
    )
    base.update(overrides)
    return FixRequest(**base)


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# Branch Name Generation Tests
# ---------------------------------------------------------------------------

class TestGenerateBranchName:
    def test_standard_branch_name_format(self):
        fix_req = _make_fix_request(id="a1b2c3d4e5f6")
        name = generate_branch_name(fix_req)
        assert name == "ai-fix/a1b2c3d4"

    def test_protected_branch_name_rejection(self):
        fix_req = _make_fix_request()
        for protected in ["main", "master", "develop", "production"]:
            with pytest.raises(FixValidationError):
                generate_branch_name(FixRequest.model_construct(
                    id=protected,
                    review_id="r",
                    issue_id="i",
                    repository="owner/repo",
                    pull_request_number=1,
                    base_commit_sha=VALID_SHA,
                    file_path="f.py",
                    issue_title="title",
                    issue_description="desc",
                ))


# ---------------------------------------------------------------------------
# BranchService Tests
# ---------------------------------------------------------------------------

class TestBranchService:
    @pytest.mark.asyncio
    async def test_create_fix_branch_success(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        mock_gh = MagicMock()
        mock_gh.get_latest_commit_sha = AsyncMock(return_value=VALID_SHA)
        mock_gh.create_git_ref = AsyncMock(return_value={"ref": "refs/heads/ai-fix/fix-req-", "object": {"sha": VALID_SHA}})

        service = BranchService(github_client=mock_gh)
        branch_name = await service.create_fix_branch(fix_req.id)

        assert branch_name == "ai-fix/fix-req-"
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.APPLYING

        mock_gh.get_latest_commit_sha.assert_awaited_once_with(
            owner="owner", repo="repo", pull_number=42
        )
        mock_gh.create_git_ref.assert_awaited_once_with(
            owner="owner",
            repo="repo",
            ref="refs/heads/ai-fix/fix-req-",
            sha=VALID_SHA,
        )

    @pytest.mark.asyncio
    async def test_create_branch_unapproved_status_raises_fix_state_error(self):
        fix_req = _make_fix_request(status=FixStatus.REQUESTED)
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        service = BranchService()
        with pytest.raises(FixStateError) as exc_info:
            await service.create_fix_branch(fix_req.id)
        assert "APPROVED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_branch_stale_commit_aborts(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        new_sha = "b" * 40
        mock_gh = MagicMock()
        mock_gh.get_latest_commit_sha = AsyncMock(return_value=new_sha)

        service = BranchService(github_client=mock_gh)

        with pytest.raises(FixStateError) as exc_info:
            await service.create_fix_branch(fix_req.id)

        assert "Stale commit detected" in str(exc_info.value)
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.STALE

    @pytest.mark.asyncio
    async def test_create_branch_nonexistent_request_raises_404(self):
        service = BranchService()
        with pytest.raises(FixNotFoundError):
            await service.create_fix_branch("nonexistent-id")

    @pytest.mark.asyncio
    async def test_create_branch_protected_override_raises_validation_error(self):
        fix_req = _make_fix_request()
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        service = BranchService()
        with pytest.raises(FixValidationError) as exc_info:
            await service.create_fix_branch(fix_req.id, override_branch_name="main")
        assert "protected" in str(exc_info.value).lower()
