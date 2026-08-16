"""
test_analytics_router.py
=========================
Integration tests for Security Analytics API endpoints (Stage 7.11).

Tests:
- GET /api/v1/analytics/security on empty database returns zeroed response.
- GET /api/v1/analytics/security with data returns security breakdown and vulnerability metrics.
- GET /api/analytics/security alias route works cleanly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analytics_service import get_analytics_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_security_analytics_empty_db():
    """GET /api/v1/analytics/security on empty DB returns zero metrics."""
    mock_analytics = MagicMock()
    mock_analytics.get_security_metrics = AsyncMock(
        return_value={
            "total_security_issues": 0,
            "critical_security_issues": 0,
            "high_security_issues": 0,
            "security_trend": [],
            "top_vulnerable_repositories": [],
            "common_security_types": [],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/analytics/security")
        assert response.status_code == 200
        data = response.json()

        assert data["total_security_issues"] == 0
        assert data["critical_security_issues"] == 0
        assert data["security_trend"] == []
    finally:
        app.dependency_overrides.clear()


def test_get_security_analytics_populated():
    """GET /api/v1/analytics/security returns security findings breakdown."""
    mock_analytics = MagicMock()
    mock_analytics.get_security_metrics = AsyncMock(
        return_value={
            "total_security_issues": 5,
            "critical_security_issues": 2,
            "high_security_issues": 3,
            "security_trend": [{"date": "2026-08-15", "security_issue_count": 5}],
            "top_vulnerable_repositories": [{"repository_id": "org/repo", "security_issue_count": 5}],
            "common_security_types": [{"title": "Hardcoded API Secret", "count": 3}],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/analytics/security")
        assert response.status_code == 200
        data = response.json()

        assert data["total_security_issues"] == 5
        assert data["critical_security_issues"] == 2
        assert data["high_security_issues"] == 3
        assert len(data["security_trend"]) == 1
        assert data["top_vulnerable_repositories"][0]["repository_id"] == "org/repo"
        assert data["common_security_types"][0]["title"] == "Hardcoded API Secret"
    finally:
        app.dependency_overrides.clear()


def test_get_security_analytics_alias_route():
    """GET /api/analytics/security alias route functions identically."""
    mock_analytics = MagicMock()
    mock_analytics.get_security_metrics = AsyncMock(
        return_value={
            "total_security_issues": 0,
            "critical_security_issues": 0,
            "high_security_issues": 0,
            "security_trend": [],
            "top_vulnerable_repositories": [],
            "common_security_types": [],
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/analytics/security")
        assert response.status_code == 200
        data = response.json()

        assert data["total_security_issues"] == 0
    finally:
        app.dependency_overrides.clear()
