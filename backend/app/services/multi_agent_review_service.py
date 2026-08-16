"""
multi_agent_review_service.py
==============================
High-level service orchestrator for the Phase 6 Multi-Agent AI Code Review System
with Phase 7 MongoDB Persistence integration.

Pipeline Flow:
--------------
ReviewRequest
    ↓
1. Pre-process Diff (normalisation, language detection)
    ↓
2. ReviewOrchestrator (parallel execution of 5 specialized agents -> list[AgentReview])
    ↓
3. ReviewAggregator (flattening, deduplication, severity ranking -> FinalReview)
    ↓
4. ScoreEngine (calculates overall quality score 0–100 -> FinalReview)
    ↓
5. ReviewPersistenceService (Phase 7: persists FinalReview -> PersistedReview in MongoDB)
    ↓
6. Phase5Adapter (transforms FinalReview -> ReviewResponse for Phase 5 compatibility)
    ↓
Structured Audit Logging & Return

Author : AI Code Review Bot — Phase 7 (Stage 7.5)
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

from app.aggregator.review_aggregator import ReviewAggregator
from app.ai.gemini_service import EmptyDiffError, GeminiService, get_gemini_service
from app.models.agent_models import AgentReview, FinalReview
from app.models.persistence_models import PersistedReview
from app.models.review_models import ReviewRequest, ReviewResponse
from app.orchestrator.review_orchestrator import ReviewOrchestrator
from app.scoring.score_engine import ScoreEngine, ScoringWeights
from app.services.phase5_adapter import Phase5Adapter
from app.services.review_persistence_service import (
    ReviewPersistenceError,
    ReviewPersistenceService,
)
from app.utils import detect_language_from_diff, normalise_diff

logger = logging.getLogger(__name__)


class MultiAgentReviewService:
    """Orchestrates the complete end-to-end Multi-Agent AI Code Review pipeline."""

    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        orchestrator: Optional[ReviewOrchestrator] = None,
        aggregator: Optional[ReviewAggregator] = None,
        score_engine: Optional[ScoreEngine] = None,
        adapter: Optional[Phase5Adapter] = None,
        persistence_service: Optional[ReviewPersistenceService] = None,
    ) -> None:
        self._gemini = gemini_service or get_gemini_service()
        self._orchestrator = orchestrator or ReviewOrchestrator(gemini_service=self._gemini)
        self._aggregator = aggregator or ReviewAggregator()
        self._score_engine = score_engine or ScoreEngine()
        self._adapter = adapter or Phase5Adapter()
        self._persistence_service = persistence_service or ReviewPersistenceService()

        logger.info("MultiAgentReviewService initialized with Phase 7 persistence.")

    async def review_raw(self, request: ReviewRequest) -> FinalReview:
        """Execute multi-agent review pipeline and return native Phase 6 ``FinalReview``.

        Args:
            request: Incoming validated ``ReviewRequest``.

        Returns:
            Native Phase 6 ``FinalReview`` containing scores, breakdowns, and per-agent results.
        """
        start_ts = time.monotonic()

        # ── Step 1: Pre-process ─────────────────────────────────────────
        diff, language_hint = self._pre_process(request)
        req_with_hint = request.model_copy(update={"diff": diff, "language_hint": language_hint})

        # ── Step 2: Orchestration (Parallel Agent Execution) ───────────
        agent_reviews: list[AgentReview] = await self._orchestrator.run(req_with_hint)

        orch_elapsed_ms = (time.monotonic() - start_ts) * 1000.0

        # ── Step 3: Aggregation (Flatten, Dedup, Severity Rank) ─────────
        final_unscored: FinalReview = self._aggregator.aggregate(
            agent_reviews=agent_reviews,
            execution_time_ms=orch_elapsed_ms,
        )

        # ── Step 4: Quality Scoring (0-100) ─────────────────────────────
        final_scored, breakdown = self._score_engine.score(final_unscored)

        total_elapsed_sec = time.monotonic() - start_ts
        self._emit_audit_log(request, final_scored, total_elapsed_sec)

        return final_scored

    async def review_and_persist(
        self,
        request: ReviewRequest,
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
    ) -> tuple[FinalReview, PersistedReview]:
        """Execute multi-agent review AND persist result into MongoDB (Phase 7).

        Order of operations:
        1. Run multi-agent review pipeline -> FinalReview.
        2. Persist FinalReview into MongoDB -> PersistedReview.
        3. If persistence fails, raise ReviewPersistenceError (never mask failure).

        Returns:
            Tuple of (FinalReview, PersistedReview).
        """
        final_review = await self.review_raw(request)

        try:
            persisted = await self._persistence_service.save_final_review(
                final_review=final_review,
                owner=owner,
                repo_name=repo_name,
                pull_request_number=pull_request_number,
                commit_sha=commit_sha,
                author=author,
                pull_request_title=pull_request_title or request.pr_title,
                pull_request_url=pull_request_url,
                base_branch=base_branch,
                head_branch=head_branch,
                files_changed=files_changed,
                additions=additions,
                deletions=deletions,
            )
            return final_review, persisted
        except Exception as exc:
            logger.error("Failed to persist review for %s/%s#%d: %s", owner, repo_name, pull_request_number, exc)
            raise ReviewPersistenceError(f"Review persistence failed: {exc}") from exc

    async def review(self, request: ReviewRequest) -> ReviewResponse:
        """Execute multi-agent review pipeline and return Phase 5-compatible ``ReviewResponse``."""
        final_review = await self.review_raw(request)
        return self._adapter.adapt(final_review)

    async def review_full(self, request: ReviewRequest) -> Tuple[FinalReview, ReviewResponse]:
        """Execute pipeline and return BOTH native ``FinalReview`` and adapted ``ReviewResponse``."""
        final_review = await self.review_raw(request)
        review_response = self._adapter.adapt(final_review)
        return final_review, review_response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pre_process(self, request: ReviewRequest) -> tuple[str, Optional[str]]:
        """Normalise the diff and infer language hint."""
        diff = normalise_diff(request.diff)

        if not diff.strip():
            raise EmptyDiffError(
                "The diff became empty after normalisation. "
                "Ensure the patch is a valid unified diff."
            )

        language_hint = request.language_hint or detect_language_from_diff(diff)
        return diff, language_hint

    @staticmethod
    def _emit_audit_log(
        request: ReviewRequest,
        final_review: FinalReview,
        elapsed_seconds: float,
    ) -> None:
        """Emit structured audit log entry for multi-agent review."""
        logger.info(
            "MultiAgentReview complete — pr_title=%r score=%d total_issues=%d "
            "successful_agents=%d failed_agents=%d severity_breakdown=%s elapsed=%.2fs",
            request.pr_title,
            final_review.overall_score,
            final_review.total_issues,
            len(final_review.successful_agents),
            len(final_review.failed_agents),
            final_review.issues_by_severity,
            elapsed_seconds,
        )


def get_multi_agent_review_service() -> MultiAgentReviewService:
    """FastAPI dependency factory for MultiAgentReviewService."""
    from app.ai.gemini_service import get_gemini_service

    return MultiAgentReviewService(gemini_service=get_gemini_service())
