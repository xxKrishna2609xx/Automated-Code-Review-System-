"""
test_analytics_service.py
==========================
Unit tests for Stage 7.9 AnalyticsService.

Tests cover:
- get_overview_metrics on empty and populated databases.
- get_repository_metrics metrics and health score calculations.
- calculate_health_score formula validation.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.persistence_models import PersistedReview
from app.services.analytics_service import AnalyticsService, calculate_health_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_persisted_review(score: int = 85, days_ago: int = 2) -> PersistedReview:
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    return PersistedReview(
        review_key=f"owner/repo#{score}@{days_ago}",
        repository="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=score,
        overall_score=score,
        total_issues=2,
        severity_counts={"critical": 0, "high": 1, "medium": 1, "low": 0},
        category_counts={"security": 1, "bug": 1},
        review_duration_ms=120.0,
        review_status="COMPLETED",
        created_at=dt,
        updated_at=dt,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_calculate_health_score_logic():
    """calculate_health_score calculates score penalty accurately."""
    # 90.0 avg - ((2 crit * 10) + (1 high * 5)) / 1 PR = 90 - 25 = 65.0
    assert calculate_health_score(90.0, critical_count=2, high_count=1, pr_count=1) == 65.0
    assert calculate_health_score(100.0, critical_count=0, high_count=0, pr_count=0) == 100.0


@pytest.mark.asyncio
async def test_analytics_service_overview_empty():
    """get_overview_metrics on empty database returns zeroed default dictionary."""
    mock_repo = MagicMock()
    mock_repo.list_reviews = AsyncMock(return_value=([], 0))

    svc = AnalyticsService(repository=mock_repo)
    metrics = await svc.get_overview_metrics()

    assert metrics["total_prs_reviewed"] == 0
    assert metrics["total_issues"] == 0
    assert metrics["average_score"] == 100.0
    assert metrics["security_issues"] == 0
    assert metrics["recent_reviews"] == []
    assert metrics["score_trend"] == []


@pytest.mark.asyncio
async def test_analytics_service_overview_populated():
    """get_overview_metrics computes real metrics across populated review dataset."""
    r1 = _sample_persisted_review(score=90, days_ago=1)
    r2 = _sample_persisted_review(score=70, days_ago=3)
    mock_repo = MagicMock()
    mock_repo.list_reviews = AsyncMock(return_value=([r1, r2], 2))

    svc = AnalyticsService(repository=mock_repo)
    metrics = await svc.get_overview_metrics()

    assert metrics["total_prs_reviewed"] == 2
    assert metrics["total_issues"] == 4
    assert metrics["average_score"] == 80.0
    assert metrics["security_issues"] == 2
    assert metrics["reviews_last_7_days"] == 2
    assert len(metrics["recent_reviews"]) == 2
    assert len(metrics["score_trend"]) == 2


@pytest.mark.asyncio
async def test_analytics_service_repository_metrics():
    """get_repository_metrics computes per-repo analytics."""
    r1 = _sample_persisted_review(score=80, days_ago=1)
    mock_repo = MagicMock()
    mock_repo.list_reviews = AsyncMock(return_value=([r1], 1))

    svc = AnalyticsService(repository=mock_repo)
    analytics = await svc.get_repository_metrics("owner/repo")

    assert analytics["repository_id"] == "owner/repo"
    assert analytics["pr_count"] == 1
    assert analytics["security_issues"] == 1
    assert analytics["bug_issues"] == 1
    assert analytics["average_score"] == 80.0
    assert analytics["health_score"] == 75.0  # 80 - 5 (1 high issue)
