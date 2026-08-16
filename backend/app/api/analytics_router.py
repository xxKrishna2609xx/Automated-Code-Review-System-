"""
analytics_router.py
===================
FastAPI router for Security and Agent analytics endpoints (Phase 7 Stage 7.11 & 7.12).

Endpoints:
- GET /analytics/security : Security analytics, vulnerability trends, and common finding types.
- GET /analytics/agents   : Agent execution counts, success rates, and duration metrics.

Author : AI Code Review Bot — Phase 7 (Stage 7.12)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.services.analytics_service import AnalyticsService, get_analytics_service

router = APIRouter()


# ---------------------------------------------------------------------------
# DTO Models
# ---------------------------------------------------------------------------

class SecurityTrendPoint(BaseModel):
    """Daily count of security issues detected."""

    date: str = Field(..., description="ISO Date string (YYYY-MM-DD).")
    security_issue_count: int = Field(..., ge=0, description="Security issues count.")


class VulnerableRepository(BaseModel):
    """Repository vulnerability metric."""

    repository_id: str = Field(..., description="Repository slug ('owner/repo').")
    security_issue_count: int = Field(..., ge=0, description="Count of security findings.")


class CommonSecurityType(BaseModel):
    """Common security issue title summary."""

    title: str = Field(..., description="Issue title.")
    count: int = Field(..., ge=0, description="Occurrences count.")


class SecurityAnalyticsResponse(BaseModel):
    """Security analytics summary response."""

    total_security_issues: int = Field(..., ge=0, description="Total security findings.")
    critical_security_issues: int = Field(..., ge=0, description="Critical severity security issues.")
    high_security_issues: int = Field(..., ge=0, description="High severity security issues.")
    security_trend: list[SecurityTrendPoint] = Field(..., description="Daily security issue trend.")
    top_vulnerable_repositories: list[VulnerableRepository] = Field(..., description="Top vulnerable repositories.")
    common_security_types: list[CommonSecurityType] = Field(..., description="Top recurring security finding titles.")


class AgentAnalyticsResponse(BaseModel):
    """Multi-agent performance & distribution metrics."""

    total_agent_executions: int = Field(..., ge=0, description="Total individual agent runs across all reviews.")
    agent_distribution: dict[str, int] = Field(..., description="Execution count per agent.")
    agent_success_rates: dict[str, float] = Field(..., description="Success rate percentage (0-100) per agent.")
    agent_average_durations_ms: dict[str, float] = Field(..., description="Average execution wall-clock time per agent.")


# ---------------------------------------------------------------------------
# Endpoint Implementations
# ---------------------------------------------------------------------------

@router.get(
    "/analytics/security",
    response_model=SecurityAnalyticsResponse,
    summary="Get security analytics, vulnerability trends, and common finding types",
    tags=["Analytics"],
)
async def get_security_analytics(
    repository: Optional[str] = Query(default=None, description="Optional repository slug filter."),
    analytics_svc: AnalyticsService = Depends(get_analytics_service),
) -> SecurityAnalyticsResponse:
    """Fetch security metrics across review history."""
    raw_data = await analytics_svc.get_security_metrics(repository=repository)
    return SecurityAnalyticsResponse(**raw_data)


@router.get(
    "/analytics/agents",
    response_model=AgentAnalyticsResponse,
    summary="Get multi-agent distribution, success rates, and duration analytics",
    tags=["Analytics"],
)
async def get_agent_analytics(
    analytics_svc: AnalyticsService = Depends(get_analytics_service),
) -> AgentAnalyticsResponse:
    """Fetch agent performance and distribution metrics."""
    raw_data = await analytics_svc.get_agent_metrics()
    return AgentAnalyticsResponse(**raw_data)
