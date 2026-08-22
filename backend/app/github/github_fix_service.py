"""
github_fix_service.py  (app.github)
====================================
Stage 8.12 — GitHub Fix Service Interface.

Provides a dedicated high-level service layer for GitHub Git Data API
and Pull Request mutations required by Phase 8 fix automation.

Design principles (Phase 8 spec §15):
    1. Encapsulates low-level Git Data API operations (blobs, trees, commits, refs, PRs).
    2. Enforces safety invariant: `force=False` is hardcoded for branch ref updates (no force pushing).
    3. Enforces safety invariant: protected branches (main/master/develop) are forbidden target branches.
    4. Cleanly decouples fix logic from HTTP transport details.

Author : AI Code Review Bot — Phase 8 (Stage 8.12)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.exceptions import GitHubAPIError, GitHubValidationError
from app.fixes.exceptions import FixValidationError
from app.github.github_client import GitHubClient

logger = logging.getLogger(__name__)

PROTECTED_BRANCHES = {"main", "master", "develop", "development", "staging", "prod", "production"}


class GitHubFixService:
    """Service wrapping GitHub Git Data API operations for AI Code Fixes.

    Args:
        client: ``GitHubClient`` instance for issuing authenticated REST API calls.
    """

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    async def create_fix_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        base_commit_sha: str,
    ) -> str:
        """Create a dedicated fix branch off base_commit_sha.

        Args:
            owner           : Repository owner.
            repo            : Repository name.
            branch_name     : Name of branch to create (e.g. 'ai-fix/a1b2c3d4').
            base_commit_sha : Commit SHA to branch off of.

        Returns:
            The created branch name.
        """
        self._assert_non_protected_branch(branch_name)

        ref_path = f"refs/heads/{branch_name.replace('refs/heads/', '')}"
        logger.info("Creating Git branch %s on %s/%s off %s", ref_path, owner, repo, base_commit_sha[:8])

        await self._client.create_git_ref(
            owner=owner,
            repo=repo,
            ref=ref_path,
            sha=base_commit_sha,
        )
        return branch_name

    async def create_blob(
        self,
        owner: str,
        repo: str,
        content: str,
    ) -> str:
        """Create a Git blob object for file content.

        Returns:
            Created blob SHA hex string.
        """
        data = await self._client.create_blob(
            owner=owner,
            repo=repo,
            content=content,
            encoding="utf-8",
        )
        blob_sha = data.get("sha")
        if not blob_sha:
            raise FixValidationError("GitHub blob creation returned response without 'sha' field.")
        return blob_sha

    async def create_tree(
        self,
        owner: str,
        repo: str,
        base_tree_sha: str,
        tree_items: list[dict[str, Any]],
    ) -> str:
        """Create a new Git tree object extending base_tree_sha.

        Returns:
            Created tree SHA hex string.
        """
        data = await self._client.create_tree(
            owner=owner,
            repo=repo,
            base_tree=base_tree_sha,
            tree_items=tree_items,
        )
        tree_sha = data.get("sha")
        if not tree_sha:
            raise FixValidationError("GitHub tree creation returned response without 'sha' field.")
        return tree_sha

    async def create_commit(
        self,
        owner: str,
        repo: str,
        message: str,
        tree_sha: str,
        parent_shas: list[str],
    ) -> str:
        """Create a Git commit object referencing tree_sha and parent_shas.

        Returns:
            Created commit SHA hex string.
        """
        data = await self._client.create_commit(
            owner=owner,
            repo=repo,
            message=message,
            tree=tree_sha,
            parents=parent_shas,
        )
        commit_sha = data.get("sha")
        if not commit_sha:
            raise FixValidationError("GitHub commit creation returned response without 'sha' field.")
        return commit_sha

    async def update_branch_head(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        commit_sha: str,
    ) -> None:
        """Update branch reference to point to commit_sha.

        SAFETY GUARANTEE: force=False is hardcoded. Force pushes are strictly forbidden.
        """
        self._assert_non_protected_branch(branch_name)

        ref = f"refs/heads/{branch_name.replace('refs/heads/', '')}"
        logger.info("Updating ref %s to commit %s on %s/%s", ref, commit_sha[:8], owner, repo)

        # Force is ALWAYS False
        await self._client.update_ref(
            owner=owner,
            repo=repo,
            ref=ref,
            sha=commit_sha,
            force=False,
        )

    async def create_fix_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool = False,
    ) -> tuple[int, str]:
        """Create a Pull Request for the fix branch against target base_branch.

        Returns:
            Tuple of (pr_number: int, pr_url: str).
        """
        self._assert_non_protected_branch(head_branch)

        logger.info("Creating fix PR '%s' (%s -> %s) on %s/%s", title, head_branch, base_branch, owner, repo)

        data = await self._client.create_pull_request(
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
            draft=draft,
        )

        pr_number = data.get("number")
        pr_url = data.get("html_url", "")

        if not pr_number:
            raise FixValidationError("GitHub PR creation returned response without 'number' field.")

        return pr_number, pr_url

    @staticmethod
    def _assert_non_protected_branch(branch_name: str) -> None:
        """Verify branch_name is not a protected default branch."""
        clean = branch_name.lower().replace("refs/heads/", "").strip()
        if clean in PROTECTED_BRANCHES:
            raise FixValidationError(
                f"Operation forbidden: branch '{branch_name}' is a protected branch."
            )
