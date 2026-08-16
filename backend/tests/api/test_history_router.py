"""
test_history_router.py
======================
Integration tests for Review History API endpoints (Stage 7.6).

Tests:
- GET /api/v1/reviews returns PaginatedReviewsResponse.
- GET /api/v1/reviews filter parameter passing.
- GET /api/v1/reviews/stats returns ReviewStatsResponse.
- GET /api/v1/reviews/{review_id} returns review document when found.
- GET /api/v1/reviews/{review_id} returns 404 when missing.
- GET /api/reviews alias route works.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.history_router import get_review_repository
from app.main import app
from app.models.persistence_models import PersistedReview

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def _sample_persisted_review(id_str: str = "65d4c8e1a2b3c4d5e6f7a8b9", key: str = "owner/repo#1@sha123") -> PersistedReview:
    return PersistedReview(
        id=id_str,
        review_key=key,
        repository="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=1,
        pull_request_title="Fix bugs in authentication",
        overall_score=85,
        total_issues=2,
        severity_counts={"high": 1, "medium": 1},
        review_status="COMPLETED",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )


@pytest.fixture
def mock_history_repository():
    repo = MagicMock()
    doc = _sample_persisted_review()
    repo.list_reviews = AsyncMock(return_value=([doc], 1))
    repo.get_review_by_id = AsyncMock(return_value=doc)
    repo.get_review_by_key = AsyncMock(return_value=None)
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_list_reviews_endpoint_success(mock_history_repository):
    """GET /api/v1/reviews returns 200 with PaginatedReviewsResponse."""
    app.dependency_overrides[get_review_repository] = lambda: mock_history_repository

    try:
        response = client.get("/api/v1/reviews?page=1&page_size=10&repository=owner/repo")
        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] == 1
        assert data["total_pages"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["review_key"] == "owner/repo#1@sha123"
    finally:
        app.dependency_overrides.clear()


def test_list_reviews_alias_endpoint(mock_history_repository):
    """GET /api/reviews alias route works identical to /api/v1/reviews."""
    app.dependency_overrides[get_review_repository] = lambda: mock_history_repository

    try:
        response = client.get("/api/reviews")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    finally:
        app.dependency_overrides.clear()


def test_get_review_stats_endpoint(mock_history_repository):
    """GET /api/v1/reviews/stats returns summary metrics."""
    app.dependency_overrides[get_review_repository] = lambda: mock_history_repository

    try:
        response = client.get("/api/v1/reviews/stats")
        assert response.status_code == 200
        data = response.json()

        assert data["total_reviews"] == 1
        assert data["total_issues"] == 2
        assert data["average_score"] == 85.0
        assert "COMPLETED" in data["status_counts"]
    finally:
        app.dependency_overrides.clear()


def test_get_review_by_id_success(mock_history_repository):
    """GET /api/v1/reviews/{review_id} returns single document when found."""
    app.dependency_overrides[get_review_repository] = lambda: mock_history_repository

    try:
        response = client.get("/api/v1/reviews/65d4c8e1a2b3c4d5e6f7a8b9")
        assert response.status_code == 200
        data = response.json()
        assert data["review_key"] == "owner/repo#1@sha123"
    finally:
        app.dependency_overrides.clear()


def test_get_review_by_id_not_found(mock_history_repository):
    """GET /api/v1/reviews/{review_id} returns 404 when document not found."""
    mock_history_repository.get_review_by_id = AsyncMock(return_value=None)
    mock_history_repository.get_review_by_key = AsyncMock(return_value=None)
    app.dependency_overrides[get_review_repository] = lambda: mock_history_repository

    try:
        response = client.get("/api/v1/reviews/missing_id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
