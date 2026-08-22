"""
test_analytics_service.py  (tests.fixes)
=========================================
Unit tests for Stage 8.18 — Fix Analytics Service & Endpoint.

Tests cover:
    - Empty metrics fallback calculations
    - Correct status counts, category breakdown, acceptance rate, and verification success rate
    - Repository slug filtering
    - FastAPI GET /api/fixes/analytics endpoint response format

Author : AI Code Review Bot — Phase 8 (Stage 8.18)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.fixes.analytics_service import FixAnalyticsMetrics, FixAnalyticsService
from app.fixes.fix_service import _FIX_REQUEST_STORE, reset_fix_stores
from app.fixes.models import FixRequest, FixStatus
from app.main import app

client = TestClient(app)

BASE_SHA = "a" * 40


def _make_fix_request(req_id: str, status: FixStatus, category: str = "security", repo: str = "owner/repo") -> FixRequest:
    return FixRequest(
        id=req_id,
        review_id="rev-123",
        issue_id=f"{category}-0",
        repository=repo,
        pull_request_number=42,
        base_commit_sha=BASE_SHA,
        file_path="app/auth.py",
        line=10,
        issue_title="Test Issue Title",
        issue_description="Test Issue Description",
        suggestion="Test Fix Suggestion",
        status=status,
    )


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# FixAnalyticsService Tests
# ---------------------------------------------------------------------------

class TestFixAnalyticsService:
    @pytest.mark.asyncio
    async def test_empty_stores_return_zero_metrics(self):
        svc = FixAnalyticsService()
        metrics = await svc.compute_metrics()

        assert metrics.total_fix_requests == 0
        assert metrics.acceptance_rate == 0.0
        assert metrics.verification_success_rate == 0.0
        assert metrics.status_counts == {}
        assert metrics.category_breakdown == {}

    @pytest.mark.asyncio
    async def test_compute_metrics_with_data(self):
        _FIX_REQUEST_STORE["f1"] = _make_fix_request("f1", FixStatus.COMPLETED, "security")
        _FIX_REQUEST_STORE["f2"] = _make_fix_request("f2", FixStatus.COMPLETED, "bug")
        _FIX_REQUEST_STORE["f3"] = _make_fix_request("f3", FixStatus.FAILED, "security")
        _FIX_REQUEST_STORE["f4"] = _make_fix_request("f4", FixStatus.REJECTED, "performance")

        svc = FixAnalyticsService()
        metrics = await svc.compute_metrics()

        assert metrics.total_fix_requests == 4
        assert metrics.total_completed == 2
        assert metrics.total_failed == 2
        assert metrics.status_counts["COMPLETED"] == 2
        assert metrics.status_counts["FAILED"] == 1
        assert metrics.status_counts["REJECTED"] == 1

        assert metrics.category_breakdown["Security"] == 2
        assert metrics.category_breakdown["Bug"] == 1
        assert metrics.category_breakdown["Performance"] == 1

        # 2 approved/completed out of 4 = 50.0%
        assert metrics.acceptance_rate == 50.0

        # 2 completed out of 4 decided (2 completed + 2 failed/rejected) = 50.0%
        assert metrics.verification_success_rate == 50.0

    @pytest.mark.asyncio
    async def test_compute_metrics_repository_filter(self):
        _FIX_REQUEST_STORE["f1"] = _make_fix_request("f1", FixStatus.COMPLETED, "bug", repo="owner/repo-a")
        _FIX_REQUEST_STORE["f2"] = _make_fix_request("f2", FixStatus.COMPLETED, "bug", repo="owner/repo-b")

        svc = FixAnalyticsService()
        metrics_a = await svc.compute_metrics(repository_slug="owner/repo-a")

        assert metrics_a.total_fix_requests == 1
        assert metrics_a.total_completed == 1


# ---------------------------------------------------------------------------
# Endpoint Tests
# ---------------------------------------------------------------------------

class TestAnalyticsEndpoint:
    def test_get_analytics_endpoint_200_ok(self):
        _FIX_REQUEST_STORE["f1"] = _make_fix_request("f1", FixStatus.COMPLETED)

        response = client.get("/api/fixes/analytics")
        assert response.status_code == 200

        data = response.json()
        assert "total_fix_requests" in data
        assert "status_counts" in data
        assert "acceptance_rate" in data
        assert data["total_fix_requests"] == 1
        assert data["status_counts"]["COMPLETED"] == 1
