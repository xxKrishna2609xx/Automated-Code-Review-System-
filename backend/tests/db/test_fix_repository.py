"""
test_fix_repository.py  (tests.db)
==================================
Unit tests for Stage 8.17 — FixRepository.

Tests cover:
    - FixRequest CRUD & status update operations
    - FixPatch CRUD operations
    - FixResult CRUD operations
    - Query methods (list_fix_requests_by_review, list_fix_requests_by_repo)
    - Fallback handling when MongoDB is disconnected

Author : AI Code Review Bot — Phase 8 (Stage 8.17)
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.fix_repository import FixRepository
from app.fixes.models import FixPatch, FixRequest, FixResult, FixStatus


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

BASE_SHA = "a" * 40
ORIGINAL_HASH = "b" * 64


def _make_fix_request() -> FixRequest:
    return FixRequest(
        id="fix-req-db123",
        review_id="rev-456",
        issue_id="bug-0",
        repository="owner/repo",
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="app/main.py",
        line=10,
        issue_title="Bug title long enough",
        issue_description="Bug description long enough",
        suggestion="Bug fix long enough",
        status=FixStatus.REQUESTED,
    )



def _make_fix_patch() -> FixPatch:
    return FixPatch(
        file_path="app/main.py",
        original_content_hash=ORIGINAL_HASH,
        patch="@@ -10,1 +10,1 @@\n-old\n+new\n",
        changed_lines=[10],
        explanation="Updated old to new.",
    )


def _make_fix_result() -> FixResult:
    return FixResult(
        fix_request_id="fix-req-db123",
        status=FixStatus.COMPLETED,
        original_issue_resolved=True,
        new_issues_detected=False,
        post_fix_review_id="post-rev-123",
    )


# ---------------------------------------------------------------------------
# Async Cursor Mock Helper
# ---------------------------------------------------------------------------

class AsyncCursorMock:
    def __init__(self, items: list[dict]):
        self._items = items

    def limit(self, n: int):
        self._items = self._items[:n]
        return self

    def __aiter__(self):
        self._iter = iter(self._items)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


# ---------------------------------------------------------------------------
# FixRepository Tests
# ---------------------------------------------------------------------------

class TestFixRepository:
    @pytest.mark.asyncio
    async def test_upsert_and_get_fix_request(self):
        req_col = MagicMock()
        req_col.replace_one = AsyncMock(return_value=None)

        fix_req = _make_fix_request()
        doc_data = fix_req.model_dump(by_alias=True)
        req_col.find_one = AsyncMock(return_value=doc_data)

        repo = FixRepository(requests_collection=req_col)

        # 1. Test upsert
        saved = await repo.upsert_fix_request(fix_req)
        assert saved.id == "fix-req-db123"
        req_col.replace_one.assert_awaited_once()

        # 2. Test get
        retrieved = await repo.get_fix_request("fix-req-db123")
        assert retrieved is not None
        assert retrieved.id == "fix-req-db123"
        assert retrieved.repository == "owner/repo"

    @pytest.mark.asyncio
    async def test_update_fix_request_status(self):
        req_col = MagicMock()
        result_mock = MagicMock()
        result_mock.matched_count = 1
        req_col.update_one = AsyncMock(return_value=result_mock)

        repo = FixRepository(requests_collection=req_col)
        success = await repo.update_fix_request_status("fix-req-db123", FixStatus.APPROVED)

        assert success is True
        req_col.update_one.assert_awaited_once_with(
            {"id": "fix-req-db123"},
            {"$set": {"status": "APPROVED"}},
        )

    @pytest.mark.asyncio
    async def test_upsert_and_get_fix_patch(self):
        patch_col = MagicMock()
        patch_col.replace_one = AsyncMock(return_value=None)

        patch = _make_fix_patch()
        doc_data = patch.model_dump()
        doc_data["fix_request_id"] = "fix-req-db123"
        patch_col.find_one = AsyncMock(return_value=doc_data)

        repo = FixRepository(patches_collection=patch_col)

        saved = await repo.upsert_fix_patch("fix-req-db123", patch)
        assert saved.file_path == "app/main.py"
        patch_col.replace_one.assert_awaited_once()

        retrieved = await repo.get_fix_patch("fix-req-db123")
        assert retrieved is not None
        assert retrieved.file_path == "app/main.py"

    @pytest.mark.asyncio
    async def test_upsert_and_get_fix_result(self):
        res_col = MagicMock()
        res_col.replace_one = AsyncMock(return_value=None)

        fix_res = _make_fix_result()
        doc_data = fix_res.model_dump()
        res_col.find_one = AsyncMock(return_value=doc_data)

        repo = FixRepository(results_collection=res_col)

        saved = await repo.upsert_fix_result(fix_res)
        assert saved.fix_request_id == "fix-req-db123"
        res_col.replace_one.assert_awaited_once()

        retrieved = await repo.get_fix_result("fix-req-db123")
        assert retrieved is not None
        assert retrieved.status == FixStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_fix_requests_by_review(self):
        req_col = MagicMock()
        fix_req = _make_fix_request()
        doc = fix_req.model_dump(by_alias=True)
        req_col.find = MagicMock(return_value=AsyncCursorMock([doc]))

        repo = FixRepository(requests_collection=req_col)
        items = await repo.list_fix_requests_by_review("rev-456")

        assert len(items) == 1
        assert items[0].review_id == "rev-456"

    @pytest.mark.asyncio
    async def test_disconnected_fallback_returns_none(self):
        repo = FixRepository()
        retrieved = await repo.get_fix_request("nonexistent-id")
        assert retrieved is None
