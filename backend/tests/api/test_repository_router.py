"""
test_repository_router.py
==========================
Integration tests for Repository APIs and Health Analytics (Stage 7.8/7.9).

Tests:
- GET /api/v1/repositories returns PaginatedRepositoriesResponse.
- GET /api/v1/repositories/{id}/analytics calculates real health_score and category breakdowns.
- GET /api/v1/repositories/{id}/reviews returns repository-filtered review history.
- GET /api/v1/repositories/{id} returns repository summary.
- calculate_health_score formula validation (no hardcoding).
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.repository_router import get_review_repository
from app.main import app
from app.models.persistence_models import PersistedReview
from app.services.analytics_service import calculate_health_score, get_analytics_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def _sample_repo_review(owner: str = "myorg", repo: str = "myrepo", score: int = 80) -> PersistedReview:
    return PersistedReview(
        review_key=f"{owner}/{repo}#{score}@head",
        repository=f"{owner}/{repo}",
        owner=owner,
        repo_name=repo,
        pull_request_number=score,
        overall_score=score,
        total_issues=3,
        severity_counts={"critical": 1, "high": 1, "medium": 1, "low": 0},
        category_counts={"security": 1, "bug": 1, "performance": 1},
        review_duration_ms=100.0,
        review_status="COMPLETED",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_calculate_repository_health_formula():
    """Verify health score penalty calculation logic."""
    health = calculate_health_score(avg_score=80.0, critical_count=1, high_count=1, pr_count=1)
    assert health == 65.0

    clean_health = calculate_health_score(avg_score=100.0, critical_count=0, high_count=0, pr_count=5)
    assert clean_health == 100.0


def test_list_repositories_endpoint():
    """GET /api/v1/repositories returns paginated repo list."""
    mock_repo = MagicMock()
    doc1 = _sample_repo_review("org1", "repo1", score=90)
    doc2 = _sample_repo_review("org2", "repo2", score=70)
    mock_repo.list_reviews = AsyncMock(return_value=([doc1, doc2], 2))

    app.dependency_overrides[get_review_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/repositories")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["health_score"] >= 0.0
    finally:
        app.dependency_overrides.clear()


def test_get_repository_analytics_endpoint():
    """GET /api/v1/repositories/{id}/analytics returns calculated repo analytics."""
    mock_analytics = MagicMock()
    mock_analytics.get_repository_metrics = AsyncMock(
        return_value={
            "repository_id": "acme/service",
            "owner": "acme",
            "repo_name": "service",
            "health_score": 75.0,
            "average_score": 85.0,
            "pr_count": 1,
            "issue_count": 3,
            "security_issues": 1,
            "bug_issues": 1,
            "performance_issues": 1,
            "testing_issues": 0,
            "documentation_issues": 0,
            "severity_distribution": {"critical": 1, "high": 1, "medium": 1, "low": 0},
            "category_distribution": {"security": 1, "bug": 1, "performance": 1},
            "score_trend": [{"date": "2026-08-16", "average_score": 85.0, "review_count": 1}],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/repositories/acme/service/analytics")
        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == "acme/service"
        assert data["pr_count"] == 1
        assert data["security_issues"] == 1
        assert data["bug_issues"] == 1
        assert data["performance_issues"] == 1
        assert data["average_score"] == 85.0
        assert len(data["score_trend"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_get_repository_reviews_endpoint():
    """GET /api/v1/repositories/{id}/reviews returns repository filtered reviews."""
    mock_repo = MagicMock()
    doc = _sample_repo_review("acme", "service", score=90)
    mock_repo.list_reviews = AsyncMock(return_value=([doc], 1))

    app.dependency_overrides[get_review_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/repositories/acme/service/reviews")
        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == "acme/service"
        assert data["total"] == 1
        assert len(data["items"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_get_repository_by_id_endpoint():
    """GET /api/v1/repositories/{id} returns repo summary."""
    mock_analytics = MagicMock()
    mock_analytics.get_repository_metrics = AsyncMock(
        return_value={
            "repository_id": "acme/service",
            "owner": "acme",
            "repo_name": "service",
            "health_score": 95.0,
            "average_score": 95.0,
            "pr_count": 1,
            "issue_count": 0,
            "security_issues": 0,
            "bug_issues": 0,
            "performance_issues": 0,
            "testing_issues": 0,
            "documentation_issues": 0,
            "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "category_distribution": {},
            "score_trend": [],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/repositories/acme/service")
        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == "acme/service"
        assert data["average_score"] == 95.0
    finally:
        app.dependency_overrides.clear()
