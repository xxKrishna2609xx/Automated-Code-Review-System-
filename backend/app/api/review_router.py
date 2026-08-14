"""
review_router.py
================
FastAPI router exposing both single-agent (Phase 4/5) and multi-agent (Phase 6)
code-review endpoints.

Routes
------
POST /api/v1/review
    (Phase 4/5) Single-agent review returning a ReviewResponse.

POST /api/v1/review/publish
    (Phase 5) Single-agent review and publish directly to GitHub PR.

POST /api/v1/multi-agent/review
    (Phase 6) Multi-agent review returning native FinalReview.

POST /api/v1/multi-agent/review/publish
    (Phase 6) Multi-agent review adapted and published directly to GitHub PR.

GET  /api/v1/review/health
    Lightweight liveness check for the review subsystem.

Author : AI Code Review Bot — Phase 6
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
from app.models.agent_models import FinalReview
from app.models.github_models import GitHubPublishResult
from app.models.review_models import ReviewRequest, ReviewResponse
from app.services.multi_agent_review_service import (
    MultiAgentReviewService,
    get_multi_agent_review_service,
)
from app.services.publish_service import PublishService
from app.services.review_service import ReviewService, get_review_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Phase 4/5 Endpoints (Preserved UNCHANGED for backward compatibility)
# ---------------------------------------------------------------------------

@router.post(
    "/review",
    response_model=ReviewResponse,
    summary="Review a Git diff with Gemini AI (Single Agent)",
    description=(
        "Accepts a raw Git unified diff and returns a structured JSON review "
        "containing a summary and a list of issues."
    ),
    responses={
        200: {"description": "Successful review response."},
        422: {"description": "Validation error or empty diff."},
        429: {"description": "Gemini API rate limit exceeded."},
        500: {"description": "Internal server error."},
        502: {"description": "Upstream Gemini error or malformed response."},
        504: {"description": "Gemini API timeout."},
    },
)
async def review_diff(
    request: ReviewRequest,
    svc: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Run the single-agent AI code-review pipeline on the supplied diff."""
    logger.info("POST /review — diff_chars=%d pr_title=%r", len(request.diff), request.pr_title)
    try:
        return await svc.review(request)
    except EmptyDiffError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GeminiAuthError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gemini authentication failed.") from exc
    except GeminiRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Gemini API rate limit exceeded.") from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Gemini API timeout.") from exc
    except GeminiParseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to parse AI response: {exc}") from exc
    except GeminiServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def get_publish_service(
    svc: ReviewService = Depends(get_review_service),
) -> PublishService:
    """Dependency provider for Phase 5 PublishService."""
    return PublishService(review_service=svc)


@router.post(
    "/review/publish",
    response_model=GitHubPublishResult,
    summary="Review a Git diff and publish findings to a GitHub PR (Single Agent)",
)
async def review_and_publish_pr(
    request: ReviewRequest,
    owner: str,
    repo: str,
    pull_number: int,
    publish_svc: PublishService = Depends(get_publish_service),
) -> GitHubPublishResult:
    """Run single-agent review and publish findings directly to GitHub PR."""
    logger.info("POST /review/publish — owner=%s repo=%s pr=%d", owner, repo, pull_number)
    try:
        return await publish_svc.review_and_publish(
            request=request,
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
    except EmptyDiffError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to execute review and publish pipeline: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Phase 6 Multi-Agent Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/multi-agent/review",
    response_model=FinalReview,
    summary="Multi-Agent AI Code Review (Phase 6)",
    description=(
        "Executes 5 specialized AI agents concurrently (Bug, Security, Performance, "
        "Documentation, Testing), aggregates & deduplicates findings, scores quality (0-100), "
        "and returns a structured FinalReview."
    ),
    tags=["Multi-Agent Review"],
)
async def multi_agent_review(
    request: ReviewRequest,
    svc: MultiAgentReviewService = Depends(get_multi_agent_review_service),
) -> FinalReview:
    """Execute parallel multi-agent review and return native FinalReview."""
    logger.info("POST /multi-agent/review — diff_chars=%d pr_title=%r", len(request.diff), request.pr_title)
    try:
        return await svc.review_raw(request)
    except EmptyDiffError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GeminiAuthError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gemini authentication failed.") from exc
    except GeminiRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Gemini API rate limit exceeded.") from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Gemini API timeout.") from exc
    except GeminiParseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to parse AI response: {exc}") from exc
    except GeminiServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def get_multi_agent_publish_service(
    svc: MultiAgentReviewService = Depends(get_multi_agent_review_service),
) -> PublishService:
    """Dependency provider for PublishService using MultiAgentReviewService."""
    # MultiAgentReviewService implements review(request) -> ReviewResponse via Phase5Adapter
    return PublishService(review_service=svc)  # type: ignore[arg-type]


@router.post(
    "/multi-agent/review/publish",
    response_model=GitHubPublishResult,
    summary="Multi-Agent AI Code Review and Publish to GitHub PR (Phase 6)",
    description=(
        "Runs the 5-agent parallel review pipeline, aggregates & scores findings, "
        "adapts output to Phase 5 format, and publishes review + inline comments to GitHub PR."
    ),
    tags=["Multi-Agent Review"],
)
async def multi_agent_review_and_publish(
    request: ReviewRequest,
    owner: str,
    repo: str,
    pull_number: int,
    publish_svc: PublishService = Depends(get_multi_agent_publish_service),
) -> GitHubPublishResult:
    """Run multi-agent review and publish findings directly to GitHub PR."""
    logger.info("POST /multi-agent/review/publish — owner=%s repo=%s pr=%d", owner, repo, pull_number)
    try:
        return await publish_svc.review_and_publish(
            request=request,
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
    except EmptyDiffError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to execute multi-agent review and publish pipeline: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/review/health",
    summary="Review subsystem health check",
    tags=["Health"],
)
async def review_health():
    """Lightweight health probe for the review subsystem."""
    return {"status": "ok", "subsystem": "review", "phase": "6-multi-agent"}
