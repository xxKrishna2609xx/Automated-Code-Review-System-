"""
review_persistence_service.py
==============================
Service layer for persisting Phase 6 FinalReview outputs into MongoDB (Phase 7).

Responsibilities:
- Transform Phase 6 ``FinalReview`` + PR metadata into a ``PersistedReview`` document.
- Normalize counters (severity, category, agent counts).
- Delegate database operations to ``ReviewRepository``.
- Guarantee idempotency via deterministic ``review_key`` upsert.
- Emit structured audit logging.

Author : AI Code Review Bot — Phase 7 (Stage 7.4)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.db.review_repository import ReviewRepository
from app.models.agent_models import FinalReview
from app.models.persistence_models import PersistedReview

logger = logging.getLogger(__name__)


class ReviewPersistenceError(Exception):
    """Raised when persistence of a review fails."""


class ReviewPersistenceService:
    """Orchestrates the persistence of code reviews into MongoDB."""

    def __init__(self, repository: Optional[ReviewRepository] = None) -> None:
        self._repo = repository or ReviewRepository()

    async def save_final_review(
        self,
        final_review: FinalReview,
        owner: str,
        repo_name: str,
        pull_request_number: int,
        commit_sha: Optional[str] = None,
        author: str = "unknown",
        pull_request_title: Optional[str] = None,
        pull_request_url: Optional[str] = None,
        base_branch: Optional[str] = None,
        head_branch: Optional[str] = None,
        files_changed: int = 1,
        additions: int = 0,
        deletions: int = 0,
    ) -> PersistedReview:
        """Persist a Phase 6 ``FinalReview`` into MongoDB.

        Args:
            final_review: Populated and scored ``FinalReview`` from Phase 6.
            owner: Repository owner / organization.
            repo_name: Repository name.
            pull_request_number: Target PR number.
            commit_sha: Head commit SHA.
            author: PR author GitHub handle.
            pull_request_title: PR title.
            pull_request_url: Web URL of the PR.
            base_branch: Target base branch.
            head_branch: Source head branch.
            files_changed: Files changed count.
            additions: Total lines added.
            deletions: Total lines deleted.

        Returns:
            The saved ``PersistedReview`` model.
        """
        start_ts = time.monotonic()

        persisted_doc = PersistedReview.from_final_review(
            final_review=final_review,
            owner=owner,
            repo_name=repo_name,
            pull_request_number=pull_request_number,
            commit_sha=commit_sha,
            author=author,
            pull_request_title=pull_request_title,
            pull_request_url=pull_request_url,
            base_branch=base_branch,
            head_branch=head_branch,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
        )

        saved = await self._repo.upsert_review(persisted_doc)
        elapsed_ms = (time.monotonic() - start_ts) * 1000.0

        logger.info(
            "Persisted review — key=%s status=%s score=%d issues=%d elapsed=%.2fms",
            saved.review_key,
            saved.review_status,
            saved.overall_score,
            saved.total_issues,
            elapsed_ms,
        )

        return saved


def get_review_persistence_service() -> ReviewPersistenceService:
    """FastAPI dependency factory for ReviewPersistenceService."""
    return ReviewPersistenceService()
