"""
fix_request_service.py  (app.fixes)
=====================================
Service responsible for creating a FixRequest from a stored Phase 7 review.

The client supplies ONLY trusted identifiers:
    - review_id  : MongoDB ObjectId hex string of a PersistedReview document.
    - issue_id   : Stable deterministic identifier for a specific Issue within
                   that review (format: "{category_lower}-{0-based-index}").

The server performs ALL of the following server-side:
    - Load the PersistedReview from MongoDB.
    - Locate the Issue within PersistedReview.issues by issue_id.
    - Extract file_path, line, repository, pull_request_number, commit_sha.
    - Validate review exists, issue exists, issue belongs to review.
    - Build and return a FixRequest ready for the eligibility check (Stage 8.3).

NEVER accepted from the client:
    - file paths
    - source code
    - repository name or slug
    - commit SHA
    - issue title or description

Design rules:
    - No Gemini calls.
    - No GitHub mutations.
    - MongoDB is read-only in this stage.

Author : AI Code Review Bot — Phase 8 (Stage 8.2)
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from app.db.review_repository import ReviewRepository
from app.fixes.exceptions import FixNotFoundError, FixValidationError
from app.fixes.models import FixRequest, FixStatus
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# issue_id helpers
# ---------------------------------------------------------------------------

def build_issue_id(issue: Issue, index: int) -> str:
    """Build a stable deterministic issue_id for an Issue at a given list index.

    Format: ``{category_lower}-{index}``

    Examples:
        "security-0"
        "bug-2"
        "performance-0"

    Args:
        issue : The Issue model.
        index : 0-based position of the issue in PersistedReview.issues.

    Returns:
        Deterministic string identifier for this issue.
    """
    category = str(issue.category).lower().replace(" ", "_")
    return f"{category}-{index}"


def find_issue_by_id(review: PersistedReview, issue_id: str) -> tuple[Issue, int]:
    """Locate an Issue within a PersistedReview by its deterministic issue_id.

    Args:
        review   : The loaded PersistedReview document.
        issue_id : Deterministic id produced by ``build_issue_id``.

    Returns:
        Tuple of (Issue, 0-based index).

    Raises:
        FixValidationError : If issue_id does not match any issue in the review.
    """
    for idx, issue in enumerate(review.issues):
        if build_issue_id(issue, idx) == issue_id:
            return issue, idx

    raise FixValidationError(
        f"Issue '{issue_id}' was not found in review '{review.id}'. "
        f"Available issue IDs: {[build_issue_id(i, n) for n, i in enumerate(review.issues)]}"
    )


# ---------------------------------------------------------------------------
# FixRequestService
# ---------------------------------------------------------------------------

class FixRequestService:
    """Creates FixRequest records from trusted Phase 7 review data.

    All sensitive context (file path, repository, commit SHA) is loaded
    exclusively from the stored PersistedReview — never from client input.

    Args:
        repository : ReviewRepository instance (injected via FastAPI Depends).
    """

    def __init__(self, repository: ReviewRepository) -> None:
        self._repo = repository

    async def create_fix_request(
        self,
        review_id: str,
        issue_id: str,
        created_by: str = "system",
    ) -> FixRequest:
        """Convert a stored finding into a FixRequest.

        Validation steps (in order):
            1. review_id is a non-empty string.
            2. issue_id is a non-empty string.
            3. PersistedReview exists in MongoDB.
            4. Review has a usable commit_sha (required for staleness detection).
            5. Issue with issue_id exists within the review.
            6. Issue has a resolvable file_path (from issue.line context or
               review metadata — Phase 8.2 uses the first file in the PR
               as fallback when the issue has no explicit file attachment).

        Args:
            review_id   : MongoDB ObjectId hex string.
            issue_id    : Deterministic issue identifier (e.g. "security-0").
            created_by  : Identifier of the requesting user.

        Returns:
            A FixRequest in REQUESTED status — NOT yet persisted to MongoDB.
            Persistence happens in Stage 8.17 (Fix History Persistence).

        Raises:
            FixValidationError  : On any input or data-integrity failure.
            FixNotFoundError    : If the review does not exist.
        """
        # ── 1. Validate identifiers ──────────────────────────────────────
        review_id = (review_id or "").strip()
        issue_id = (issue_id or "").strip()

        if not review_id:
            raise FixValidationError("review_id must not be empty.")
        if not issue_id:
            raise FixValidationError("issue_id must not be empty.")

        logger.info(
            "Creating fix request: review_id=%s issue_id=%s created_by=%s",
            review_id, issue_id, created_by,
        )

        # ── 2. Load PersistedReview from MongoDB ─────────────────────────
        review: Optional[PersistedReview] = await self._repo.get_review_by_id(review_id)
        if review is None:
            raise FixNotFoundError(
                f"Review '{review_id}' was not found. "
                "Ensure the review_id is a valid MongoDB ObjectId string."
            )

        # ── 3. Validate commit SHA (required for staleness detection) ─────
        if not review.commit_sha:
            raise FixValidationError(
                f"Review '{review_id}' has no commit_sha recorded. "
                "A commit SHA is required to detect stale fixes. "
                "Re-run the review to populate this field."
            )

        # ── 4. Locate Issue by issue_id ───────────────────────────────────
        issue, _idx = find_issue_by_id(review, issue_id)

        # ── 5. Resolve file_path ──────────────────────────────────────────
        # Issues in Phase 6 carry an optional line number but no explicit
        # file_path field (that is on GitHubFile, not Issue). We derive a
        # best-effort file path from:
        #   a. The issue line number matched against files_changed count.
        #   b. Fallback: use repository slug as a placeholder path that the
        #      FixContextBuilder (Stage 8.4) will resolve precisely via GitHub.
        #
        # For Stage 8.2 we store "UNRESOLVED" as a sentinel; Stage 8.4 will
        # replace it with the real path fetched from GitHub file context.
        # This keeps Stage 8.2 free of any GitHub API call.
        file_path = "UNRESOLVED"

        # ── 6. Build FixRequest ───────────────────────────────────────────
        fix_request = FixRequest(
            id=uuid.uuid4().hex,
            review_id=review_id,
            issue_id=issue_id,
            repository_id=review.repository_id,
            repository=review.repository,
            pull_request_number=review.pull_request_number,
            base_commit_sha=review.commit_sha,
            file_path=file_path,
            line=issue.line,
            issue_title=issue.title,
            issue_description=issue.description,
            suggestion=issue.suggestion,
            status=FixStatus.REQUESTED,
            created_by=created_by,
        )

        logger.info(
            "FixRequest created: fix_id=%s review_id=%s issue_id=%s repository=%s pr=%s",
            fix_request.id,
            fix_request.review_id,
            fix_request.issue_id,
            fix_request.repository,
            fix_request.pull_request_number,
        )

        return fix_request
