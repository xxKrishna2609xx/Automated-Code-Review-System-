"""
test_fix_pr_service.py  (tests.fixes)
=======================================
Unit tests for Stage 8.14 — FixPRService.

Tests cover:
    - Successful Pull Request creation on GitHub
    - Standardized PR title formatting
    - PR body formatting with mandatory Safety & Governance Notice
    - Status transition to PR_CREATED
    - Rejection of PR creation for unapproved/uncommitted fix requests
    - Nonexistent fix request 404 handling

Author : AI Code Review Bot — Phase 8 (Stage 8.14)
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_pr_service import FixPRResult, FixPRService, format_fix_pr_body
from app.fixes.fix_service import _FIX_PATCH_STORE, _FIX_REQUEST_STORE, reset_fix_stores
from app.fixes.models import FixPatch, FixRequest, FixStatus


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

BASE_SHA = "a" * 40
ORIGINAL_HASH = "b" * 64

def _make_fix_request(**overrides) -> FixRequest:
    base = dict(
        id="fix-req-pr12345",
        review_id="rev-456",
        issue_id="security-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="app/auth.py",
        line=15,
        issue_title="Insecure password hash",
        issue_description="MD5 hashing used instead of bcrypt.",
        suggestion="Switch to bcrypt.",
        status=FixStatus.COMMITTED,
    )
    base.update(overrides)
    return FixRequest(**base)


def _make_fix_patch() -> FixPatch:
    return FixPatch(
        file_path="app/auth.py",
        original_content_hash=ORIGINAL_HASH,
        patch="@@ -15,1 +15,1 @@\n-import md5\n+import bcrypt\n",
        changed_lines=[15],
        explanation="Replaced MD5 with bcrypt for secure hashing.",
    )


def _make_mock_gh_service() -> MagicMock:
    svc = MagicMock()
    svc.create_fix_pull_request = AsyncMock(return_value=(202, "https://github.com/owner/repo/pull/202"))
    return svc


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# FixPRService Unit Tests
# ---------------------------------------------------------------------------

class TestFixPRService:
    @pytest.mark.asyncio
    async def test_create_fix_pr_success(self):
        fix_req = _make_fix_request()
        fix_patch = _make_fix_patch()

        _FIX_REQUEST_STORE[fix_req.id] = fix_req
        _FIX_PATCH_STORE[fix_req.id] = fix_patch

        mock_gh = _make_mock_gh_service()
        svc = FixPRService(github_fix_service=mock_gh)

        result = await svc.create_fix_pr(fix_request_id=fix_req.id)

        assert isinstance(result, FixPRResult)
        assert result.pr_number == 202
        assert result.pr_url == "https://github.com/owner/repo/pull/202"
        assert result.title == "[AI Auto-Fix] Insecure password hash (Security)"
        assert result.head_branch == "ai-fix/fix-req-"
        assert result.base_branch == "main"
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.PR_CREATED

        mock_gh.create_fix_pull_request.assert_awaited_once()

    def test_format_fix_pr_body_includes_safety_notice(self):
        fix_req = _make_fix_request()
        fix_patch = _make_fix_patch()

        body = format_fix_pr_body(fix_req, fix_patch)

        assert "AI Code Remediation Proposal" in body
        assert "Insecure password hash" in body
        assert "Replaced MD5 with bcrypt" in body
        assert "Autonomous self-merging is strictly disabled" in body
        assert "Never automatically merged" in body

    @pytest.mark.asyncio
    async def test_create_pr_uncommitted_request_raises_fix_state_error(self):
        fix_req = _make_fix_request(status=FixStatus.REQUESTED)
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        mock_gh = _make_mock_gh_service()
        svc = FixPRService(github_fix_service=mock_gh)

        with pytest.raises(FixStateError) as exc_info:
            await svc.create_fix_pr(fix_request_id=fix_req.id)

        assert "COMMITTED" in str(exc_info.value) or "APPROVED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_pr_nonexistent_request_raises_404(self):
        mock_gh = _make_mock_gh_service()
        svc = FixPRService(github_fix_service=mock_gh)

        with pytest.raises(FixNotFoundError):
            await svc.create_fix_pr(fix_request_id="nonexistent-id-999")
