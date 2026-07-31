"""
review_router.py
================
FastAPI router exposing the AI code-review endpoints.

Routes
------
POST /api/v1/review
    Accepts a ReviewRequest body, runs the full review pipeline,
    and returns a structured ReviewResponse.

GET  /api/v1/review/health
    Lightweight liveness check for the review subsystem.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.gemini_service import (
    EmptyDiffError,
    GeminiAuthError,
    GeminiParseError,
    GeminiRateLimitError,
    GeminiServiceError,
    GeminiTimeoutError,
)
from app.models.review_models import ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService, get_review_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/review",
    response_model=ReviewResponse,
    summary="Review a Git diff with Gemini AI",
    description=(
        "Accepts a raw Git unified diff and returns a structured JSON review "
        "containing a summary and a list of issues (bugs, security, performance, etc.). "
        "Large diffs are automatically split and reviewed in chunks."
    ),
    responses={
        200: {"description": "Successful review response."},
        422: {"description": "Validation error or empty diff."},
        429: {"description": "Gemini API rate limit exceeded."},
        500: {"description": "Internal server error (auth, config)."},
        502: {"description": "Upstream Gemini error or malformed response."},
        504: {"description": "Gemini API timeout."},
    },
)
async def review_diff(
    request: ReviewRequest,
    svc: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Run the AI code-review pipeline on the supplied diff.

    Args:
        request : Validated ``ReviewRequest`` (diff + optional metadata).
        svc     : Injected ``ReviewService`` instance.

    Returns:
        Structured ``ReviewResponse`` with summary and issue list.
    """
    logger.info(
        "POST /review — diff_chars=%d pr_title=%r",
        len(request.diff),
        request.pr_title,
    )

    try:
        return await svc.review(request)

    except EmptyDiffError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except GeminiAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini authentication failed.  Contact the system administrator.",
        ) from exc
    except GeminiRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini API quota exhausted.  Please retry in a few moments.",
        ) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The Gemini API did not respond in time.  Please retry.",
        ) from exc
    except GeminiParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse AI response: {exc}",
        ) from exc
    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get(
    "/review/health",
    summary="Review subsystem health check",
    tags=["Health"],
)
async def review_health():
    """Lightweight health probe for the review subsystem.

    Returns:
        JSON confirming the review router is reachable.
    """
    return {"status": "ok", "subsystem": "review"}
