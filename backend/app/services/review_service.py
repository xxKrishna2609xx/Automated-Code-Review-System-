"""
review_service.py
=================
High-level orchestration layer for the AI code-review pipeline.

This service sits between the API layer and the low-level GeminiService.
Its responsibilities are:

1. Validate the incoming ReviewRequest.
2. Pre-process the diff (normalise, detect language, emit metrics).
3. Delegate to GeminiService for AI-powered review.
4. Post-process the ReviewResponse (sort issues by severity, deduplicate).
5. Emit structured audit logs for every review.
6. Surface domain-level errors with caller-friendly messages.

By keeping orchestration here — and not inside GeminiService or the API
route — we maintain a clean separation of concerns and make the pipeline
easy to unit-test independently of the HTTP layer.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.ai.gemini_service import (
    EmptyDiffError,
    GeminiAuthError,
    GeminiParseError,
    GeminiRateLimitError,
    GeminiService,
    GeminiServiceError,
    GeminiTimeoutError,
)
from app.models.review_models import Issue, ReviewRequest, ReviewResponse, Severity
from app.utils import (
    detect_language_from_diff,
    normalise_diff,
    sort_and_deduplicate_issues,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Severity ordering (used for post-processing sort)
# ---------------------------------------------------------------------------

_SEVERITY_ORDER: dict[str, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


# ---------------------------------------------------------------------------
# ReviewService
# ---------------------------------------------------------------------------


class ReviewService:
    """Orchestrates the end-to-end AI code-review pipeline.

    Inject via FastAPI's ``Depends`` — see ``get_review_service()``.

    Args:
        gemini_service: Low-level Gemini API wrapper.
    """

    def __init__(self, gemini_service: GeminiService) -> None:
        self._gemini = gemini_service
        logger.info("ReviewService initialised.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def review(self, request: ReviewRequest) -> ReviewResponse:
        """Execute a full code-review pipeline for the supplied diff.

        Steps
        -----
        1. Pre-process: normalise diff, extract metadata.
        2. Call Gemini via GeminiService.
        3. Post-process: sort, deduplicate, annotate.
        4. Emit audit log entry.

        Args:
            request: Validated ``ReviewRequest`` DTO.

        Returns:
            Post-processed ``ReviewResponse`` ready for serialisation.

        Raises:
            EmptyDiffError       : The diff is empty after normalisation.
            GeminiAuthError      : API key is invalid.
            GeminiRateLimitError : Quota exhausted after retries.
            GeminiTimeoutError   : API call timed out after retries.
            GeminiParseError     : Model response could not be parsed.
            GeminiServiceError   : Any other unrecoverable Gemini error.
            ReviewServiceError   : Any orchestration-layer error.
        """
        start_ts = time.monotonic()

        # ── Step 1: Pre-process ─────────────────────────────────────────
        diff, language_hint = self._pre_process(request)

        logger.info(
            "Starting review — diff_chars=%d language=%s pr_title=%r",
            len(diff),
            language_hint or "unknown",
            request.pr_title,
        )

        # ── Step 2: AI review ───────────────────────────────────────────
        try:
            raw_response = await self._gemini.review_code(
                diff=diff,
                pr_title=request.pr_title,
                pr_description=request.pr_description,
                language_hint=language_hint,
            )
        except EmptyDiffError:
            raise  # Already a clean domain error; surface as-is.
        except GeminiAuthError as exc:
            logger.error("Authentication failure — check GEMINI_API_KEY: %s", exc)
            raise
        except GeminiRateLimitError as exc:
            logger.warning("Gemini rate limit hit: %s", exc)
            raise
        except GeminiTimeoutError as exc:
            logger.warning("Gemini request timed out: %s", exc)
            raise
        except GeminiParseError as exc:
            logger.error("Failed to parse Gemini response: %s", exc)
            raise
        except GeminiServiceError as exc:
            logger.error("Unexpected Gemini error: %s", exc)
            raise

        # ── Step 3: Post-process ────────────────────────────────────────
        processed = self._post_process(raw_response)

        # ── Step 4: Audit log ────────────────────────────────────────────
        elapsed = time.monotonic() - start_ts
        self._emit_audit_log(request, processed, elapsed_seconds=elapsed)

        return processed

    # ------------------------------------------------------------------
    # Private: Pre-processing
    # ------------------------------------------------------------------

    def _pre_process(
        self, request: ReviewRequest
    ) -> tuple[str, Optional[str]]:
        """Normalise the diff and infer metadata before sending to Gemini.

        Args:
            request: Incoming ``ReviewRequest``.

        Returns:
            Tuple of ``(normalised_diff, language_hint)``.

        Raises:
            EmptyDiffError: Diff is empty after normalisation.
        """
        diff = normalise_diff(request.diff)

        if not diff.strip():
            raise EmptyDiffError(
                "The diff became empty after normalisation.  "
                "Ensure the patch is a valid unified diff."
            )

        language_hint = request.language_hint or detect_language_from_diff(diff)
        return diff, language_hint

    # ------------------------------------------------------------------
    # Private: Post-processing
    # ------------------------------------------------------------------

    def _post_process(self, response: ReviewResponse) -> ReviewResponse:
        """Enhance and normalise the raw ReviewResponse.

        Operations performed:
        1. Sort issues by severity (Critical → Low).
        2. Deduplicate near-identical issues.
        3. Rebuild ``ReviewResponse``.

        Args:
            response: Raw ``ReviewResponse`` from Gemini.

        Returns:
            Post-processed ``ReviewResponse``.
        """
        processed_issues = sort_and_deduplicate_issues(response.issues)
        return ReviewResponse(
            summary=response.summary,
            issues=processed_issues,
            reviewed_chunks=response.reviewed_chunks,
        )

    # ------------------------------------------------------------------
    # Private: Audit logging
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_audit_log(
        request: ReviewRequest,
        response: ReviewResponse,
        elapsed_seconds: float,
    ) -> None:
        """Emit a structured audit log entry for every completed review.

        This is intentionally a separate method so it can be easily replaced
        with a structured logging sink (e.g. Cloud Logging, DataDog) without
        touching business logic.

        Args:
            request        : Original review request.
            response       : Final post-processed response.
            elapsed_seconds: Wall-clock time for the review pipeline.
        """
        severity_breakdown: dict[str, int] = {}
        for issue in response.issues:
            severity_breakdown[issue.severity] = (
                severity_breakdown.get(issue.severity, 0) + 1
            )

        logger.info(
            "Review complete — "
            "pr_title=%r diff_chars=%d chunks=%d total_issues=%d "
            "severity_breakdown=%s elapsed=%.2fs",
            request.pr_title,
            len(request.diff),
            response.reviewed_chunks,
            response.total_issues,
            severity_breakdown,
            elapsed_seconds,
        )


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ReviewServiceError(Exception):
    """Raised for orchestration-layer failures not covered by Gemini errors."""


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------


def get_review_service() -> ReviewService:
    """FastAPI dependency that returns a ``ReviewService`` instance.

    Resolves the ``GeminiService`` dependency internally so route handlers
    only need to declare a single dependency::

        @router.post("/review")
        async def review_endpoint(
            request: ReviewRequest,
            svc: ReviewService = Depends(get_review_service),
        ) -> ReviewResponse:
            return await svc.review(request)

    Returns:
        Application-scoped ``ReviewService`` instance.
    """
    from app.ai.gemini_service import get_gemini_service

    return ReviewService(gemini_service=get_gemini_service())
