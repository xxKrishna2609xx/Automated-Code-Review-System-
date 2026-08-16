"""
history_router.py
==================
FastAPI router for Review History and Stats endpoints (Phase 7 Stage 7.6).

Endpoints:
- GET /reviews            : Paginated list of persisted reviews with filtering.
- GET /reviews/stats      : Aggregated overview statistics.
- GET /reviews/{review_id}: Detailed persisted review document by ID or review_key.

Author : AI Code Review Bot — Phase 7 (Stage 7.6)
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.review_repository import ReviewFilter, ReviewRepository, get_review_repository
from app.models.persistence_models import PersistedReview

router = APIRouter()


def get_review_repository() -> ReviewRepository:
    """Dependency factory for ReviewRepository."""
    return ReviewRepository()


# ---------------------------------------------------------------------------
# API DTO Models
# ---------------------------------------------------------------------------

class PaginatedReviewsResponse(BaseModel):
    """Paginated list response wrapper."""

    items: list[PersistedReview] = Field(..., description="List of persisted reviews.")
    page: int = Field(..., ge=1, description="Current page number.")
    page_size: int = Field(..., ge=1, description="Page size.")
    total: int = Field(..., ge=0, description="Total matching document count.")
    total_pages: int = Field(..., ge=0, description="Total pages count.")


class ReviewStatsResponse(BaseModel):
    """Aggregate statistics response for code review history."""

    total_reviews: int = Field(..., ge=0, description="Total review documents count.")
    total_issues: int = Field(..., ge=0, description="Sum of all detected issues.")
    average_score: float = Field(..., ge=0.0, le=100.0, description="Average quality score.")
    status_counts: dict[str, int] = Field(..., description="Count of reviews by status.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/reviews",
    response_model=PaginatedReviewsResponse,
    summary="List code review history with pagination and filtering",
    tags=["Review History"],
)
async def list_reviews(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    repository: Optional[str] = Query(default=None, description="Repository slug ('owner/repo')."),
    author: Optional[str] = Query(default=None, description="PR author GitHub username."),
    severity: Optional[str] = Query(default=None, description="Filter by issue severity (Critical, High, etc.)."),
    category: Optional[str] = Query(default=None, description="Filter by issue category (Security, Bug, etc.)."),
    agent: Optional[str] = Query(default=None, description="Filter by executing agent name."),
    review_status: Optional[str] = Query(default=None, alias="status", description="Filter by status (COMPLETED, PARTIAL, FAILED)."),
    min_score: Optional[int] = Query(default=None, ge=0, le=100, description="Minimum score filter."),
    max_score: Optional[int] = Query(default=None, ge=0, le=100, description="Maximum score filter."),
    start_date: Optional[datetime] = Query(default=None, description="Created at start ISO timestamp."),
    end_date: Optional[datetime] = Query(default=None, description="Created at end ISO timestamp."),
    search: Optional[str] = Query(default=None, description="Search term in PR title or summary."),
    sort_by: str = Query(default="created_at", description="Field to sort by."),
    sort_order: str = Query(default="desc", description="Sort direction ('asc' or 'desc')."),
    repo: ReviewRepository = Depends(get_review_repository),
) -> PaginatedReviewsResponse:
    """Fetch paginated review history with multi-field search & filters."""
    filter_params = ReviewFilter(
        page=page,
        page_size=page_size,
        repository=repository,
        author=author,
        severity=severity,
        category=category,
        agent=agent,
        status=review_status,
        min_score=min_score,
        max_score=max_score,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items, total = await repo.list_reviews(filter_params)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedReviewsResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/reviews/stats",
    response_model=ReviewStatsResponse,
    summary="Get aggregated code review statistics",
    tags=["Review History"],
)
async def get_review_stats(
    repository: Optional[str] = Query(default=None, description="Optional repository slug filter."),
    repo: ReviewRepository = Depends(get_review_repository),
) -> ReviewStatsResponse:
    """Get high-level summary metrics across review history."""
    filter_params = ReviewFilter(page=1, page_size=100, repository=repository)
    items, total = await repo.list_reviews(filter_params)

    if total == 0:
        return ReviewStatsResponse(
            total_reviews=0,
            total_issues=0,
            average_score=100.0,
            status_counts={"COMPLETED": 0, "PARTIAL": 0, "FAILED": 0},
        )

    total_issues = sum(item.total_issues for item in items)
    valid_scores = [item.overall_score for item in items if item.overall_score >= 0]
    avg_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 100.0

    status_counts: dict[str, int] = {}
    for item in items:
        st = str(item.review_status).upper()
        status_counts[st] = status_counts.get(st, 0) + 1

    return ReviewStatsResponse(
        total_reviews=total,
        total_issues=total_issues,
        average_score=avg_score,
        status_counts=status_counts,
    )


@router.get(
    "/reviews/{review_id}",
    response_model=PersistedReview,
    summary="Get detailed review document by ID or review_key",
    tags=["Review History"],
)
async def get_review_by_id(
    review_id: str,
    repo: ReviewRepository = Depends(get_review_repository),
) -> PersistedReview:
    """Fetch a single review document by MongoDB ObjectId string or review_key."""
    review = await repo.get_review_by_id(review_id)
    if not review:
        review = await repo.get_review_by_key(review_id)

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review '{review_id}' not found.",
        )

    return review
