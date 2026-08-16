"""
repository_router.py
====================
FastAPI router for Repository level APIs and Analytics (Phase 7 Stage 7.8/7.9).

Endpoints:
- GET /repositories                         : Paginated list of tracked repositories.
- GET /repositories/{repository_id:path}/reviews   : Paginated review history for a specific repository.
- GET /repositories/{repository_id:path}/analytics : Comprehensive repository health & analytics metrics.
- GET /repositories/{repository_id:path}           : Single repository summary.

Author : AI Code Review Bot — Phase 7 (Stage 7.9)
"""

from __future__ import annotations

import datetime
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.dashboard_router import ScoreTrendPoint
from app.db.review_repository import ReviewFilter, ReviewRepository, get_review_repository
from app.services.analytics_service import AnalyticsService, calculate_health_score, get_analytics_service

router = APIRouter()


# ---------------------------------------------------------------------------
# DTO Models
# ---------------------------------------------------------------------------

class RepositorySummary(BaseModel):
    """High-level metrics for a single tracked repository."""

    repository_id: str = Field(..., description="Repository slug ('owner/repo').")
    owner: str = Field(..., description="Repository owner.")
    repo_name: str = Field(..., description="Repository name.")
    health_score: float = Field(..., ge=0.0, le=100.0, description="Calculated repository health score (0-100).")
    average_score: float = Field(..., ge=0.0, le=100.0, description="Average quality score across reviews.")
    pr_count: int = Field(..., ge=0, description="Total PRs reviewed.")
    issue_count: int = Field(..., ge=0, description="Total detected issues.")
    last_reviewed_at: Optional[datetime.datetime] = Field(default=None, description="Timestamp of latest review.")


class PaginatedRepositoriesResponse(BaseModel):
    """Paginated list of repositories."""

    items: list[RepositorySummary] = Field(..., description="List of repository summaries.")
    page: int = Field(..., ge=1, description="Current page number.")
    page_size: int = Field(..., ge=1, description="Page size.")
    total: int = Field(..., ge=0, description="Total repositories count.")
    total_pages: int = Field(..., ge=0, description="Total pages count.")


class RepositoryAnalyticsResponse(BaseModel):
    """Detailed analytics breakdown for a single repository."""

    repository_id: str = Field(..., description="Repository slug ('owner/repo').")
    owner: str = Field(..., description="Repository owner.")
    repo_name: str = Field(..., description="Repository name.")
    health_score: float = Field(..., ge=0.0, le=100.0, description="Calculated repository health score.")
    average_score: float = Field(..., ge=0.0, le=100.0, description="Average quality score.")
    pr_count: int = Field(..., ge=0, description="Total PRs reviewed.")
    issue_count: int = Field(..., ge=0, description="Total detected issues.")
    security_issues: int = Field(..., ge=0, description="Total security category issues.")
    bug_issues: int = Field(..., ge=0, description="Total bug category issues.")
    performance_issues: int = Field(..., ge=0, description="Total performance category issues.")
    testing_issues: int = Field(..., ge=0, description="Total testing category issues.")
    documentation_issues: int = Field(..., ge=0, description="Total documentation category issues.")
    severity_distribution: dict[str, int] = Field(..., description="Counts per severity level.")
    category_distribution: dict[str, int] = Field(..., description="Counts per issue category.")
    score_trend: list[ScoreTrendPoint] = Field(..., description="Daily score trends for repository.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/repositories",
    response_model=PaginatedRepositoriesResponse,
    summary="List tracked repositories with summary health & score metrics",
    tags=["Repositories"],
)
async def list_repositories(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: Optional[str] = Query(default=None, description="Optional search term for repo name or owner."),
    repo: ReviewRepository = Depends(get_review_repository),
) -> PaginatedRepositoriesResponse:
    """Fetch paginated summary of all tracked repositories with real health scores."""
    filter_params = ReviewFilter(page=1, page_size=100, search=search)
    reviews, _ = await repo.list_reviews(filter_params)

    repo_groups: dict[str, list] = {}
    for r in reviews:
        repo_groups.setdefault(r.repository.lower(), []).append(r)

    repo_summaries: list[RepositorySummary] = []

    for repo_slug, r_list in repo_groups.items():
        parts = repo_slug.split("/")
        owner = parts[0] if len(parts) > 1 else r_list[0].owner
        repo_name = parts[1] if len(parts) > 1 else r_list[0].repo_name

        pr_count = len(r_list)
        total_issues = sum(r.total_issues for r in r_list)
        valid_scores = [r.overall_score for r in r_list if r.overall_score >= 0]
        avg_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 100.0

        crit_count = sum(r.severity_counts.get("critical", 0) for r in r_list)
        high_count = sum(r.severity_counts.get("high", 0) for r in r_list)
        health_score = calculate_health_score(avg_score, crit_count, high_count, pr_count)

        last_rev = max(r.created_at for r in r_list) if r_list else None

        repo_summaries.append(
            RepositorySummary(
                repository_id=r_list[0].repository,
                owner=owner,
                repo_name=repo_name,
                health_score=health_score,
                average_score=avg_score,
                pr_count=pr_count,
                issue_count=total_issues,
                last_reviewed_at=last_rev,
            )
        )

    repo_summaries.sort(key=lambda s: s.health_score, reverse=True)

    total = len(repo_summaries)
    skip = (page - 1) * page_size
    paged_items = repo_summaries[skip : skip + page_size]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedRepositoriesResponse(
        items=paged_items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/repositories/{repository_id:path}/analytics",
    response_model=RepositoryAnalyticsResponse,
    summary="Get detailed analytics and breakdown for a repository",
    tags=["Repositories"],
)
async def get_repository_analytics(
    repository_id: str,
    analytics_svc: AnalyticsService = Depends(get_analytics_service),
) -> RepositoryAnalyticsResponse:
    """Get real-time analytics breakdown via AnalyticsService."""
    raw_data = await analytics_svc.get_repository_metrics(repository_id=repository_id)
    return RepositoryAnalyticsResponse(**raw_data)


@router.get(
    "/repositories/{repository_id:path}/reviews",
    response_model=dict,
    summary="Get paginated review history for a specific repository",
    tags=["Repositories"],
)
async def get_repository_reviews(
    repository_id: str,
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size."),
    repo: ReviewRepository = Depends(get_review_repository),
):
    """Fetch review history filtered strictly for repository_id ('owner/repo')."""
    clean_repo_id = repository_id.strip().lower()
    filter_params = ReviewFilter(page=page, page_size=page_size, repository=clean_repo_id)
    items, total = await repo.list_reviews(filter_params)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "repository_id": repository_id,
        "items": [item.model_dump() for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.get(
    "/repositories/{repository_id:path}",
    response_model=RepositorySummary,
    summary="Get repository summary by ID",
    tags=["Repositories"],
)
async def get_repository_by_id(
    repository_id: str,
    analytics_svc: AnalyticsService = Depends(get_analytics_service),
) -> RepositorySummary:
    """Fetch single repository summary metrics."""
    analytics = await get_repository_analytics(repository_id=repository_id, analytics_svc=analytics_svc)
    return RepositorySummary(
        repository_id=analytics.repository_id,
        owner=analytics.owner,
        repo_name=analytics.repo_name,
        health_score=analytics.health_score,
        average_score=analytics.average_score,
        pr_count=analytics.pr_count,
        issue_count=analytics.issue_count,
    )
