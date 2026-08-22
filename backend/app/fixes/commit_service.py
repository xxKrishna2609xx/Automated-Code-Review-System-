"""
commit_service.py  (app.fixes)
==============================
Stage 8.13 — Commit Fix Patch via Git Data API.

Applies an APPROVED FixPatch in memory, creates Git blobs/trees/commits via
GitHubFixService, and updates the dedicated fix branch HEAD.

Design principles (Phase 8 spec §16):
    1. Only APPROVED / APPLYING fix requests can be committed.
    2. Commit message format: ``fix({category}): {issue_title} [AI Fix #{fix_request_id_short}]``
    3. Low-level Git Data API calls:
       - create_blob -> blob_sha
       - create_tree(base_tree=base_commit_sha) -> tree_sha
       - create_commit(parents=[base_commit_sha]) -> new_commit_sha
       - update_branch_head(force=False)
    4. Status advances to COMMITTED upon success.

Author : AI Code Review Bot — Phase 8 (Stage 8.13)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.fixes.branch_service import BranchService
from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_service import _FIX_PATCH_STORE, _FIX_REQUEST_STORE
from app.fixes.models import FixPatch, FixRequest, FixStatus
from app.fixes.patch_applier import InMemoryPatchService
from app.github.github_fix_service import GitHubFixService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommitResult:
    """Outcome of committing a fix patch to GitHub.

    Attributes:
        fix_request_id : Target FixRequest ID.
        branch_name    : Target fix branch (e.g. 'ai-fix/a1b2c3d4').
        commit_sha     : Created commit SHA hex string.
        file_path      : Target file path modified.
        commit_message : Commit message applied.
    """

    fix_request_id: str
    branch_name: str
    commit_sha: str
    file_path: str
    commit_message: str


# ---------------------------------------------------------------------------
# CommitService
# ---------------------------------------------------------------------------


class CommitService:
    """Orchestrates Git Data API commit creation for approved fix patches.

    Args:
        github_fix_service : Service handling low-level GitHub Git Data API calls.
        patch_applier      : Service handling in-memory patch application.
        branch_service     : Service handling safe branch creation.
    """

    def __init__(
        self,
        github_fix_service: GitHubFixService,
        patch_applier: Optional[InMemoryPatchService] = None,
        branch_service: Optional[BranchService] = None,
    ) -> None:
        self._gh_fix_svc = github_fix_service
        self._patch_applier = patch_applier or InMemoryPatchService()
        self._branch_svc = branch_service or BranchService()

    async def commit_fix(
        self,
        fix_request_id: str,
        base_file_content: str,
        custom_commit_message: Optional[str] = None,
    ) -> CommitResult:
        """Apply patch in memory and create commit on dedicated fix branch.

        Args:
            fix_request_id        : Unique FixRequest ID.
            base_file_content     : Raw source file content at base_commit_sha.
            custom_commit_message : Optional custom commit message override.

        Returns:
            CommitResult detailing created commit SHA and branch name.

        Raises:
            FixNotFoundError   : If FixRequest does not exist.
            FixStateError      : If status is not APPROVED or APPLYING.
            FixValidationError : If patch is missing or Git Data API fails.
        """
        logger.info("Initiating commit pipeline for fix request %s", fix_request_id)

        # ── 1. Fetch FixRequest & Patch ───────────────────────────────
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")

        current_status = fix_req.status.value if hasattr(fix_req.status, "value") else str(fix_req.status)
        if current_status not in (FixStatus.APPROVED.value, FixStatus.APPLYING.value):
            raise FixStateError(
                f"Cannot commit fix request '{fix_request_id}' in state '{current_status}'. "
                "Fix request must be APPROVED or APPLYING."
            )

        patch = _FIX_PATCH_STORE.get(fix_request_id)
        if not patch:
            raise FixValidationError(f"No generated patch found for fix request '{fix_request_id}'.")

        owner, repo = fix_req.repository.split("/", 1)

        # ── 2. Create or Resolve Fix Branch ───────────────────────────
        branch_name = await self._branch_svc.create_fix_branch(fix_request_id=fix_req.id)

        # ── 3. Apply Patch In Memory ──────────────────────────────────
        applied_patch = self._patch_applier.apply_patch(
            fix_request=fix_req,
            fix_patch=patch,
            base_file_content=base_file_content,
        )

        # ── 4. Create Blob via Git Data API ───────────────────────────
        blob_sha = await self._gh_fix_svc.create_blob(
            owner=owner,
            repo=repo,
            content=applied_patch.updated_content,
        )

        # ── 5. Create Tree via Git Data API ───────────────────────────
        tree_item = {
            "path": applied_patch.file_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        }

        tree_sha = await self._gh_fix_svc.create_tree(
            owner=owner,
            repo=repo,
            base_tree_sha=fix_req.base_commit_sha,
            tree_items=[tree_item],
        )

        # ── 6. Create Commit via Git Data API ─────────────────────────
        req_short = (fix_req.id or "00000000")[:8]
        category_slug = fix_req.issue_id.split("-")[0]
        default_message = f"fix({category_slug}): {fix_req.issue_title} [AI Fix #{req_short}]"
        commit_msg = custom_commit_message or default_message

        commit_sha = await self._gh_fix_svc.create_commit(
            owner=owner,
            repo=repo,
            message=commit_msg,
            tree_sha=tree_sha,
            parent_shas=[fix_req.base_commit_sha],
        )

        # ── 7. Update Branch HEAD (force=False invariant) ─────────────
        await self._gh_fix_svc.update_branch_head(
            owner=owner,
            repo=repo,
            branch_name=branch_name,
            commit_sha=commit_sha,
        )

        # Advance status to COMMITTED
        fix_req.status = FixStatus.COMMITTED
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        logger.info(
            "Fix request %s committed successfully: branch=%s, commit_sha=%s",
            fix_req.id,
            branch_name,
            commit_sha[:8],
        )

        return CommitResult(
            fix_request_id=fix_req.id,
            branch_name=branch_name,
            commit_sha=commit_sha,
            file_path=applied_patch.file_path,
            commit_message=commit_msg,
        )
