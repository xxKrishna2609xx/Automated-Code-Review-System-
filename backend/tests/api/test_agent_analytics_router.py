"""
test_agent_analytics_router.py
===============================
Integration tests for Agent Distribution Analytics API endpoints (Stage 7.12).

Tests:
- GET /api/v1/analytics/agents on empty database returns zero metrics.
- GET /api/v1/analytics/agents with dataset returns agent distribution, success rates, and durations.
- GET /api/analytics/agents alias route functions cleanly.
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

def test_get_agent_analytics_empty_db():
    """GET /api/v1/analytics/agents on empty DB returns zero metrics."""
    mock_analytics = MagicMock()
    mock_analytics.get_agent_metrics = AsyncMock(
        return_value={
            "total_agent_executions": 0,
            "agent_distribution": {},
            "agent_success_rates": {},
            "agent_average_durations_ms": {},
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/analytics/agents")
        assert response.status_code == 200
        data = response.json()

        assert data["total_agent_executions"] == 0
        assert data["agent_distribution"] == {}
        assert data["agent_success_rates"] == {}
        assert data["agent_average_durations_ms"] == {}
    finally:
        app.dependency_overrides.clear()


def test_get_agent_analytics_populated():
    """GET /api/v1/analytics/agents returns real execution counts, success rates, and durations."""
    mock_analytics = MagicMock()
    mock_analytics.get_agent_metrics = AsyncMock(
        return_value={
            "total_agent_executions": 10,
            "agent_distribution": {"bug_agent": 2, "security_agent": 2, "performance_agent": 2, "documentation_agent": 2, "testing_agent": 2},
            "agent_success_rates": {"bug_agent": 100.0, "security_agent": 50.0, "performance_agent": 100.0, "documentation_agent": 100.0, "testing_agent": 100.0},
            "agent_average_durations_ms": {"bug_agent": 45.0, "security_agent": 80.0, "performance_agent": 35.0, "documentation_agent": 20.0, "testing_agent": 30.0},
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/v1/analytics/agents")
        assert response.status_code == 200
        data = response.json()

        assert data["total_agent_executions"] == 10
        assert data["agent_distribution"]["security_agent"] == 2
        assert data["agent_success_rates"]["security_agent"] == 50.0
        assert data["agent_average_durations_ms"]["security_agent"] == 80.0
    finally:
        app.dependency_overrides.clear()


def test_get_agent_analytics_alias_route():
    """GET /api/analytics/agents alias route functions identically."""
    mock_analytics = MagicMock()
    mock_analytics.get_agent_metrics = AsyncMock(
        return_value={
            "total_agent_executions": 0,
            "agent_distribution": {},
            "agent_success_rates": {},
            "agent_average_durations_ms": {},
        }
    )

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    try:
        response = client.get("/api/analytics/agents")
        assert response.status_code == 200
        data = response.json()

        assert data["total_agent_executions"] == 0
    finally:
        app.dependency_overrides.clear()
