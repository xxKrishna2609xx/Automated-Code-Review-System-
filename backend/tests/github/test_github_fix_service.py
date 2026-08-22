"""
test_github_fix_service.py  (tests.github)
===========================================
Unit tests for Stage 8.12 — GitHubFixService.

Tests cover:
    - Branch creation off base SHA
    - Rejection of operations targeting protected branches (main, master, develop)
    - Creation of blobs, trees, commits via low-level Git Data API
    - Updating branch heads with force=False invariant verified
    - Pull Request creation returning PR number and HTML URL

Author : AI Code Review Bot — Phase 8 (Stage 8.12)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.fixes.exceptions import FixValidationError
from app.github.github_fix_service import GitHubFixService


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

VALID_SHA = "a" * 40
BLOB_SHA = "b" * 40
TREE_SHA = "c" * 40
COMMIT_SHA = "d" * 40

def _make_mock_client() -> MagicMock:
    client = MagicMock()
    client.create_git_ref = AsyncMock(return_value={"ref": "refs/heads/ai-fix/123", "object": {"sha": VALID_SHA}})
    client.create_blob = AsyncMock(return_value={"sha": BLOB_SHA})
    client.create_tree = AsyncMock(return_value={"sha": TREE_SHA})
    client.create_commit = AsyncMock(return_value={"sha": COMMIT_SHA})
    client.update_ref = AsyncMock(return_value={"ref": "refs/heads/ai-fix/123", "object": {"sha": COMMIT_SHA}})
    client.create_pull_request = AsyncMock(return_value={"number": 101, "html_url": "https://github.com/owner/repo/pull/101"})
    return client


# ---------------------------------------------------------------------------
# GitHubFixService Tests
# ---------------------------------------------------------------------------

class TestGitHubFixService:
    @pytest.mark.asyncio
    async def test_create_fix_branch_success(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        branch_name = await svc.create_fix_branch("owner", "repo", "ai-fix/test1234", VALID_SHA)
        assert branch_name == "ai-fix/test1234"
        client.create_git_ref.assert_awaited_once_with(
            owner="owner", repo="repo", ref="refs/heads/ai-fix/test1234", sha=VALID_SHA
        )

    @pytest.mark.asyncio
    async def test_create_fix_branch_protected_rejected(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        with pytest.raises(FixValidationError) as exc_info:
            await svc.create_fix_branch("owner", "repo", "main", VALID_SHA)
        assert "protected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_blob_success(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        sha = await svc.create_blob("owner", "repo", "def hello(): pass\n")
        assert sha == BLOB_SHA
        client.create_blob.assert_awaited_once_with(
            owner="owner", repo="repo", content="def hello(): pass\n", encoding="utf-8"
        )

    @pytest.mark.asyncio
    async def test_create_tree_success(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        items = [{"path": "app/main.py", "mode": "100644", "type": "blob", "sha": BLOB_SHA}]
        sha = await svc.create_tree("owner", "repo", base_tree_sha=VALID_SHA, tree_items=items)
        assert sha == TREE_SHA
        client.create_tree.assert_awaited_once_with(
            owner="owner", repo="repo", base_tree=VALID_SHA, tree_items=items
        )

    @pytest.mark.asyncio
    async def test_create_commit_success(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        sha = await svc.create_commit("owner", "repo", "Fix security flaw", TREE_SHA, [VALID_SHA])
        assert sha == COMMIT_SHA
        client.create_commit.assert_awaited_once_with(
            owner="owner", repo="repo", message="Fix security flaw", tree=TREE_SHA, parents=[VALID_SHA]
        )

    @pytest.mark.asyncio
    async def test_update_branch_head_force_false_invariant(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        await svc.update_branch_head("owner", "repo", "ai-fix/test1234", COMMIT_SHA)
        # Verify force is explicitly False
        client.update_ref.assert_awaited_once_with(
            owner="owner", repo="repo", ref="refs/heads/ai-fix/test1234", sha=COMMIT_SHA, force=False
        )

    @pytest.mark.asyncio
    async def test_update_branch_head_protected_rejected(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        with pytest.raises(FixValidationError):
            await svc.update_branch_head("owner", "repo", "master", COMMIT_SHA)

    @pytest.mark.asyncio
    async def test_create_fix_pull_request_success(self):
        client = _make_mock_client()
        svc = GitHubFixService(client=client)

        num, url = await svc.create_fix_pull_request(
            owner="owner",
            repo="repo",
            title="Fix SQL injection",
            body="Automated fix",
            head_branch="ai-fix/test1234",
            base_branch="main",
        )

        assert num == 101
        assert url == "https://github.com/owner/repo/pull/101"
        client.create_pull_request.assert_awaited_once_with(
            owner="owner",
            repo="repo",
            title="Fix SQL injection",
            body="Automated fix",
            head="ai-fix/test1234",
            base="main",
            draft=False,
        )
