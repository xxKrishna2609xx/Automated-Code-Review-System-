"""
post_fix_review_service.py  (app.fixes)
========================================
Stage 8.15 — Post-Fix Phase 6 Review Service.

Performs a fresh Phase 6 multi-agent code review on the post-fix codebase / diff
to verify whether the original finding was resolved and whether any new issues
were introduced by the auto-remediation patch.

Design principles (Phase 8 spec §18):
    1. "Do not claim a fix worked until Phase 6 re-reviews it."
    2. Re-runs multi-agent pipeline (Bug, Security, Performance, etc.).
    3. Aggregates results into a fresh FinalReview.
    4. Persists the post-fix review into ReviewRepository as a PersistedReview.
    5. Returns post_fix_review_id for downstream verification (Stage 8.16).

Author : AI Code Review Bot — Phase 8 (Stage 8.15)
"""

from __future__ import annotations

import logging
from typing import Optional

from app.aggregator.review_aggregator import ReviewAggregator
from app.db.review_repository import ReviewRepository
from app.fixes.exceptions import FixNotFoundError, FixStateError
from app.fixes.fix_service import _FIX_REQUEST_STORE
from app.fixes.models import FixRequest, FixStatus
from app.models.agent_models import FinalReview
from app.models.persistence_models import PersistedReview
from app.models.review_models import ReviewRequest
from app.orchestrator.review_orchestrator import ReviewOrchestrator

logger = logging.getLogger(__name__)


class PostFixReviewService:
    """Runs a fresh Phase 6 multi-agent review on a post-fix code patch.

    Args:
        orchestrator : Optional ReviewOrchestrator instance.
        aggregator   : Optional ReviewAggregator instance.
        repository   : Optional ReviewRepository instance for saving the review.
    """

    def __init__(
        self,
        orchestrator: Optional[ReviewOrchestrator] = None,
        aggregator: Optional[ReviewAggregator] = None,
        repository: Optional[ReviewRepository] = None,
    ) -> None:
        self._orchestrator = orchestrator or ReviewOrchestrator()
        self._aggregator = aggregator or ReviewAggregator()
        self._repository = repository

    async def execute_post_fix_review(
        self,
        fix_request_id: str,
        post_fix_diff: str,
        commit_sha: Optional[str] = None,
    ) -> PersistedReview:
        """Execute a post-fix Phase 6 review on the modified code.

        Args:
            fix_request_id : Unique FixRequest ID.
            post_fix_diff  : Unified diff or code snippet representing the post-fix state.
            commit_sha     : Optional commit SHA of the post-fix commit.

        Returns:
            Saved post-fix PersistedReview object.

        Raises:
            FixNotFoundError : If FixRequest does not exist.
            FixStateError    : If FixRequest is not in a reviewable state.
        """
        logger.info("Executing post-fix Phase 6 review for fix request %s", fix_request_id)

        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")

        # Construct ReviewRequest for Phase 6 pipeline
        owner, repo_name = fix_req.repository.split("/", 1)
        rev_req = ReviewRequest(
            diff=post_fix_diff,
            pr_title=f"Post-fix review for FixRequest {fix_req.id}",
        )


        # ── Step 1: Run Multi-Agent Review Pipeline ───────────────────
        agent_reviews = await self._orchestrator.run(rev_req)

        # ── Step 2: Aggregate Findings into FinalReview ───────────────
        final_review: FinalReview = self._aggregator.aggregate(
            agent_reviews=agent_reviews,
        )


        # ── Step 3: Convert to PersistedReview DTO ───────────────────
        target_sha = commit_sha or fix_req.base_commit_sha
        persisted = PersistedReview.from_final_review(
            final_review=final_review,
            owner=owner,
            repo_name=repo_name,
            pull_request_number=fix_req.pull_request_number,
            commit_sha=target_sha,
        )



        # ── Step 4: Upsert into Persistence Layer ────────────────────
        if self._repository is not None:
            persisted = await self._repository.upsert_review(persisted)
            logger.info("Persisted post-fix review %s to MongoDB repository", persisted.id)
        else:
            logger.info("No repository attached; returning in-memory post-fix review %s", persisted.id)

        return persisted
