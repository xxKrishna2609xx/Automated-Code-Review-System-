"""
dashboard_router.py
===================
FastAPI router for Dashboard Overview & Analytics endpoints (Phase 7 Stage 7.7/7.9).

Endpoints:
- GET /dashboard/overview : Comprehensive SaaS metrics, score trends, and distributions.

Author : AI Code Review Bot — Phase 7 (Stage 7.9)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.models.persistence_models import PersistedReview
from app.services.analytics_service import AnalyticsService, get_analytics_service

router = APIRouter()


# ---------------------------------------------------------------------------
# DTO Models
# ---------------------------------------------------------------------------

class ScoreTrendPoint(BaseModel):
    """Daily summary point for score trends."""

    date: str = Field(..., description="ISO Date string (YYYY-MM-DD).")
    average_score: float = Field(..., ge=0.0, le=100.0, description="Average quality score for the day.")
    review_count: int = Field(..., ge=0, description="Number of reviews completed on this day.")


class DashboardOverviewResponse(BaseModel):
    """Comprehensive dashboard summary metrics."""

    total_prs_reviewed: int = Field(..., ge=0, description="Total PRs reviewed across history.")
    total_issues: int = Field(..., ge=0, description="Total issues detected.")
    average_score: float = Field(..., ge=0.0, le=100.0, description="Average overall quality score.")
    security_issues: int = Field(..., ge=0, description="Total security category findings.")
    severity_distribution: dict[str, int] = Field(..., description="Counts per severity level.")
    category_distribution: dict[str, int] = Field(..., description="Counts per issue category.")
    reviews_last_7_days: int = Field(..., ge=0, description="Reviews completed in past 7 days.")
    reviews_last_30_days: int = Field(..., ge=0, description="Reviews completed in past 30 days.")
    average_review_duration_ms: float = Field(..., ge=0.0, description="Average review wall-clock time.")
    recent_reviews: list[PersistedReview] = Field(..., description="Top 5 most recent reviews.")
    score_trend: list[ScoreTrendPoint] = Field(..., description="Daily score trends.")


# ---------------------------------------------------------------------------
# Endpoint Implementation
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/overview",
    response_model=DashboardOverviewResponse,
    summary="Get real dashboard overview metrics and analytics",
    tags=["Dashboard"],
)
async def get_dashboard_overview(
    repository: Optional[str] = Query(default=None, description="Optional repository slug filter."),
    analytics_svc: AnalyticsService = Depends(get_analytics_service),
) -> DashboardOverviewResponse:
    """Fetch real aggregated metrics, distributions, and recent activity via AnalyticsService."""
    raw_data = await analytics_svc.get_overview_metrics(repository=repository)
    return DashboardOverviewResponse(**raw_data)
