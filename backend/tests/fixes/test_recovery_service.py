"""
test_recovery_service.py  (tests.fixes)
========================================
Unit tests for Stage 8.25 — FixRecoveryService.

Tests cover:
    - Marking FixRequest as FAILED with error audit payload
    - Marking FixRequest as STALE
    - Resetting FAILED/STALE FixRequest to REQUESTED for clean retry
    - State transition validation guard on non-retriable requests

Author : AI Code Review Bot — Phase 8 (Stage 8.25)
"""

from __future__ import annotations

import pytest

from app.fixes.exceptions import FixNotFoundError, FixStateError
from app.fixes.fix_service import _FIX_REQUEST_STORE, _FIX_RESULT_STORE, reset_fix_stores
from app.fixes.models import FixRequest, FixStatus
from app.fixes.recovery_service import FixRecoveryService

BASE_SHA = "a" * 40


def _make_fix_request(req_id: str, status: FixStatus = FixStatus.REQUESTED) -> FixRequest:
    return FixRequest(
        id=req_id,
        review_id="rev-123",
        issue_id="bug-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="app/main.py",
        line=10,
        issue_title="Bug title long enough",
        issue_description="Bug description long enough",
        suggestion="Fix suggestion long enough",
        status=status,
    )


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


class TestFixRecoveryService:
    @pytest.mark.asyncio
    async def test_mark_fix_failed(self):
        _FIX_REQUEST_STORE["f1"] = _make_fix_request("f1", FixStatus.GENERATING)
        svc = FixRecoveryService()

        failed_req = await svc.mark_fix_failed("f1", "LLM API timeout", "TIMEOUT_ERROR")

        assert failed_req.status == FixStatus.FAILED
        assert _FIX_REQUEST_STORE["f1"].status == FixStatus.FAILED
        assert _FIX_RESULT_STORE["f1"].status == FixStatus.FAILED
        assert _FIX_RESULT_STORE["f1"].original_issue_resolved is False

    @pytest.mark.asyncio
    async def test_mark_fix_stale(self):
        _FIX_REQUEST_STORE["f2"] = _make_fix_request("f2", FixStatus.READY_FOR_APPROVAL)
        svc = FixRecoveryService()

        stale_req = await svc.mark_fix_stale("f2", "Base commit updated on GitHub")

        assert stale_req.status == FixStatus.STALE
        assert _FIX_REQUEST_STORE["f2"].status == FixStatus.STALE

    @pytest.mark.asyncio
    async def test_retry_fix_request_success(self):
        _FIX_REQUEST_STORE["f3"] = _make_fix_request("f3", FixStatus.FAILED)
        svc = FixRecoveryService()

        reset_req = await svc.retry_fix_request("f3")

        assert reset_req.status == FixStatus.REQUESTED
        assert _FIX_REQUEST_STORE["f3"].status == FixStatus.REQUESTED
        assert "f3" not in _FIX_RESULT_STORE

    @pytest.mark.asyncio
    async def test_retry_fix_request_invalid_state_raises_error(self):
        _FIX_REQUEST_STORE["f4"] = _make_fix_request("f4", FixStatus.COMPLETED)
        svc = FixRecoveryService()

        with pytest.raises(FixStateError, match="Cannot retry"):
            await svc.retry_fix_request("f4")
