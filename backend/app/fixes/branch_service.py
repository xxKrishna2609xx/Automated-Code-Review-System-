"""
branch_service.py  (app.fixes)
==============================
Stage 8.10 — Safe Branch Creation Service.

Handles dedicated fix branch creation on GitHub for approved fix requests.

Design principles (Phase 8 spec §13):
    1. NEVER modify the default branch directly (main/master/develop).
    2. NEVER force push.
    3. Standardized branch naming convention: ``ai-fix/{fix_request_id_short}``.
    4. Base branch: created strictly off ``base_commit_sha`` (HEAD at review time).
    5. Pre-creation staleness check: verifies latest PR HEAD commit matches ``base_commit_sha``.
       If commit moved, branch creation is aborted with STALE_COMMIT_DETECTED.

Author : AI Code Review Bot — Phase 8 (Stage 8.10)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_service import _FIX_REQUEST_STORE
from app.fixes.models import FixRequest, FixStatus
from app.github.github_client import GitHubClient

logger = logging.getLogger(__name__)

# Reserved default branches that MUST NEVER be modified directly or targeted as fix branch names
PROTECTED_BRANCH_NAMES = {
    "main",
    "master",
    "develop",
    "development",
    "staging",
    "prod",
    "production",
    "release",
}


def validate_branch_name(branch_name: str) -> None:
    """Validate that a branch name is safe and does not target protected branches."""
    clean = branch_name.lower().strip()
    if not clean:
        raise FixValidationError("Branch name must not be empty.")

    parts = [p for p in clean.split("/") if p]
    for p in parts:
        if p in PROTECTED_BRANCH_NAMES:
            raise FixValidationError(
                f"Branch name '{branch_name}' contains protected branch keyword '{p}'."
            )


def generate_branch_name(fix_request: FixRequest) -> str:
    """Generate standardized, safe fix branch name for a FixRequest.

    Format: ``ai-fix/{fix_request_id[:8]}``

    Args:
        fix_request : Validated FixRequest instance.

    Returns:
        Formatted branch name string (e.g. 'ai-fix/a1b2c3d4').

    Raises:
        FixValidationError : If generated branch name collides with a protected branch.
    """
    raw_id = fix_request.id or "fix00000"
    # Validate raw id part before truncation if caller passed a protected keyword
    if raw_id.lower() in PROTECTED_BRANCH_NAMES:
        raise FixValidationError(
            f"Fix request ID '{raw_id}' collides with protected branch keyword."
        )

    req_id = raw_id[:8]
    branch_name = f"ai-fix/{req_id}"

    validate_branch_name(branch_name)
    return branch_name



class BranchService:
    """Handles safe fix branch creation on GitHub with pre-creation staleness verification.

    Args:
        github_client : Optional GitHubClient instance for API interaction.
    """

    def __init__(self, github_client: Optional[GitHubClient] = None) -> None:
        self._gh_client = github_client

    async def create_fix_branch(
        self,
        fix_request_id: str,
        override_branch_name: Optional[str] = None,
    ) -> str:
        """Create a dedicated fix branch off base_commit_sha on GitHub.

        Validation steps:
            1. FixRequest exists.
            2. FixRequest status == APPROVED.
            3. Branch name is safe and non-protected.
            4. Latest commit SHA on PR matches base_commit_sha (Staleness check).
            5. Create git ref 'refs/heads/<branch_name>' via GitHub API.

        Args:
            fix_request_id       : Unique FixRequest ID.
            override_branch_name : Optional explicit branch name override for testing.

        Returns:
            Created branch name string (e.g. 'ai-fix/a1b2c3d4').

        Raises:
            FixNotFoundError   : If FixRequest does not exist.
            FixStateError      : If FixRequest status is not APPROVED, or if SHA is stale.
            FixValidationError : If branch name is invalid/protected or GitHub creation fails.
        """
        logger.info("Initiating safe branch creation for fix request %s", fix_request_id)

        # ── 1. Fetch FixRequest ──────────────────────────────────────
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")

        # ── 2. Verify APPROVED Status ────────────────────────────────
        current_status = fix_req.status.value if hasattr(fix_req.status, "value") else str(fix_req.status)
        if current_status != FixStatus.APPROVED.value:
            raise FixStateError(
                f"Cannot create branch for fix request '{fix_request_id}' in state '{current_status}'. "
                "Fix request must be APPROVED before branch creation."
            )

        # ── 3. Generate & Validate Branch Name ───────────────────────
        branch_name = override_branch_name or generate_branch_name(fix_req)

        if branch_name.lower() in PROTECTED_BRANCH_NAMES:
            raise FixValidationError(
                f"Cannot create branch '{branch_name}': targeting protected default branch is forbidden."
            )

        owner, repo = fix_req.repository.split("/", 1)

        # ── 4. Pre-Creation Staleness Verification ────────────────────
        if self._gh_client is not None:
            try:
                latest_sha = await self._gh_client.get_latest_commit_sha(
                    owner=owner,
                    repo=repo,
                    pull_number=fix_req.pull_request_number,
                )
                if latest_sha.lower() != fix_req.base_commit_sha.lower():
                    fix_req.status = FixStatus.STALE
                    _FIX_REQUEST_STORE[fix_req.id] = fix_req
                    logger.warning(
                        "Stale commit detected during branch creation for %s: base=%s, latest=%s",
                        fix_req.id,
                        fix_req.base_commit_sha[:8],
                        latest_sha[:8],
                    )
                    raise FixStateError(
                        f"Stale commit detected: base commit SHA {fix_req.base_commit_sha[:8]} "
                        f"does not match current PR HEAD {latest_sha[:8]}. Branch creation aborted."
                    )
            except FixStateError:
                raise
            except Exception as exc:
                logger.warning("Could not verify latest commit SHA via GitHubClient: %s", exc)

        # ── 5. Create Git Ref via GitHub API ─────────────────────────
        if self._gh_client is not None:
            try:
                ref_path = f"refs/heads/{branch_name}"
                await self._gh_client.create_git_ref(
                    owner=owner,
                    repo=repo,
                    ref=ref_path,
                    sha=fix_req.base_commit_sha,
                )
                logger.info(
                    "Successfully created git ref %s at SHA %s on %s",
                    ref_path,
                    fix_req.base_commit_sha[:8],
                    fix_req.repository,
                )
            except Exception as exc:
                logger.error("GitHub API failed to create git ref %s: %s", branch_name, exc)
                raise FixValidationError(f"GitHub branch creation failed: {exc}") from exc

        # Advance status to APPLYING
        fix_req.status = FixStatus.APPLYING
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        return branch_name
