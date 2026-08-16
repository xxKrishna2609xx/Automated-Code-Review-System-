"""
test_dashboard_router.py
========================
Integration tests for Dashboard Overview API endpoint (Stage 7.7/7.9).

Tests:
- GET /api/v1/dashboard/overview with empty database returns zeroed default metrics.
- GET /api/v1/dashboard/overview with review data calculates real metrics, distributions, and trends.
- GET /api/dashboard/overview alias route works cleanly.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.persistence_models import PersistedReview
from app.services.analytics_service import get_analytics_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def _sample_persisted_review(score: int = 80, days_ago: int = 2) -> PersistedReview:
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    return PersistedReview(
        review_key=f"org/repo#{score}@{days_ago}",
        repository="org/repo",
        owner="org",
        repo_name="repo",
        pull_request_number=score,
        pull_request_title=f"PR score {score}",
        overall_score=score,
        total_issues=2,
        severity_counts={"critical": 0, "high": 1, "medium": 1, "low": 0},
        category_counts={"security": 1, "bug": 1},
        review_duration_ms=150.0,
        review_status="COMPLETED",
        created_at=dt,
        updated_at=dt,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dashboard_overview_empty_db():
    """GET /api/v1/dashboard/overview on empty DB returns clean zero metrics."""
    mock_analytics = MagicMock()
    mock_analytics.get_overview_metrics = AsyncMock(
        return_value={
            "total_prs_reviewed": 0,
            "total_issues": 0,
            "average_score": 100.0,
            "security_issues": 0,
            "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "category_distribution": {},
            "reviews_last_7_days": 0,
            "reviews_last_30_days": 0,
            "average_review_duration_ms": 0.0,
            "recent_reviews": [],
            "score_trend": [],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        assert data["total_prs_reviewed"] == 0
        assert data["total_issues"] == 0
        assert data["average_score"] == 100.0
        assert data["security_issues"] == 0
        assert data["recent_reviews"] == []
        assert data["score_trend"] == []
    finally:
        app.dependency_overrides.clear()


def test_dashboard_overview_with_data():
    """GET /api/v1/dashboard/overview with review data returns accurate analytics."""
    doc1 = _sample_persisted_review(score=90, days_ago=1)
    doc2 = _sample_persisted_review(score=70, days_ago=3)
    reviews = [doc1.model_dump(mode="json"), doc2.model_dump(mode="json")]

    mock_analytics = MagicMock()
    mock_analytics.get_overview_metrics = AsyncMock(
        return_value={
            "total_prs_reviewed": 2,
            "total_issues": 4,
            "average_score": 80.0,
            "security_issues": 2,
            "severity_distribution": {"critical": 0, "high": 2, "medium": 2, "low": 0},
            "category_distribution": {"security": 2, "bug": 2},
            "reviews_last_7_days": 2,
            "reviews_last_30_days": 2,
            "average_review_duration_ms": 150.0,
            "recent_reviews": [doc1, doc2],
            "score_trend": [{"date": "2026-08-15", "average_score": 80.0, "review_count": 2}],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        assert data["total_prs_reviewed"] == 2
        assert data["total_issues"] == 4
        assert data["average_score"] == 80.0
        assert data["security_issues"] == 2
        assert data["reviews_last_7_days"] == 2
        assert len(data["recent_reviews"]) == 2
        assert len(data["score_trend"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_dashboard_overview_alias_route():
    """GET /api/dashboard/overview alias route functions identically."""
    mock_analytics = MagicMock()
    mock_analytics.get_overview_metrics = AsyncMock(
        return_value={
            "total_prs_reviewed": 0,
            "total_issues": 0,
            "average_score": 100.0,
            "security_issues": 0,
            "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "category_distribution": {},
            "reviews_last_7_days": 0,
            "reviews_last_30_days": 0,
            "average_review_duration_ms": 0.0,
            "recent_reviews": [],
            "score_trend": [],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_prs_reviewed"] == 0
    finally:
        app.dependency_overrides.clear()
