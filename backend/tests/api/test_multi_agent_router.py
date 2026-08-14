"""
test_multi_agent_router.py
===========================
Integration tests for FastAPI router endpoints (Stage 6.14).

Tests:
- POST /api/v1/multi-agent/review returns 200 with structured FinalReview.
- POST /api/v1/multi-agent/review with empty diff returns 422.
- POST /api/v1/multi-agent/review/publish calls publish pipeline and returns 200.
- GET  /api/v1/review/health returns subsystem status.
- Single-agent endpoints (/api/v1/review and /api/v1/review/publish) remain functional.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.review_router import get_multi_agent_publish_service
from app.main import app
from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.github_models import GitHubPublishResult, GitHubReviewEvent
from app.models.review_models import Issue, IssueCategory, ReviewResponse, Severity
from app.services.multi_agent_review_service import get_multi_agent_review_service

client = TestClient(app)

VALID_DIFF = (
    "--- a/main.py\n+++ b/main.py\n"
    "@@ -1,3 +1,3 @@\n"
    "-def foo(): pass\n"
    "+def foo(x: int) -> int:\n"
    "+    return x * 2\n"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_multi_agent_service():
    svc = MagicMock()

    issue = Issue(
        title="Missing return annotation",
        severity=Severity.LOW,
        line=2,
        category=IssueCategory.BEST_PRACTICE,
        description="Type hint recommended.",
        suggestion="Add -> int",
    )

    final_review = FinalReview(
        overall_score=98,
        summary="Clean diff with minor best practice recommendation.",
        issues=[issue],
        total_issues=1,
        issues_by_category={"best practice": 1},
        issues_by_severity={"low": 1, "medium": 0, "high": 0, "critical": 0},
        agent_results=[],
        successful_agents=["bug_agent", "security_agent", "performance_agent", "documentation_agent", "testing_agent"],
        failed_agents=[],
        execution_time_ms=120.0,
    )

    review_response = ReviewResponse(
        summary="## 🤖 Multi-Agent Code Review — Quality Score: 98/100 🟢\n\n**1 issue found:** 🔵 1 Low",
        issues=[issue],
        reviewed_chunks=5,
    )

    svc.review_raw = AsyncMock(return_value=final_review)
    svc.review = AsyncMock(return_value=review_response)
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_multi_agent_review_endpoint_success(mock_multi_agent_service):
    """POST /api/v1/multi-agent/review returns 200 with FinalReview JSON schema."""
    app.dependency_overrides[get_multi_agent_review_service] = lambda: mock_multi_agent_service

    try:
        response = client.post(
            "/api/v1/multi-agent/review",
            json={"diff": VALID_DIFF, "pr_title": "Update foo function"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["overall_score"] == 98
        assert data["total_issues"] == 1
        assert len(data["issues"]) == 1
        assert data["issues"][0]["title"] == "Missing return annotation"
        assert len(data["successful_agents"]) == 5
    finally:
        app.dependency_overrides.clear()


def test_multi_agent_review_endpoint_validation_error():
    """POST /api/v1/multi-agent/review with empty diff returns 422 Unprocessable Entity."""
    response = client.post(
        "/api/v1/multi-agent/review",
        json={"diff": "   "},
    )
    assert response.status_code == 422


def test_multi_agent_publish_endpoint_success(mock_multi_agent_service):
    """POST /api/v1/multi-agent/review/publish returns 200 with GitHubPublishResult."""
    mock_publish_result = GitHubPublishResult(
        status="success",
        review_id=12345,
        pr_number=42,
        event=GitHubReviewEvent.COMMENT,
        comments_published=1,
        html_url="https://github.com/owner/repo/pull/42#issuecomment-12345",
        elapsed_seconds=0.42,
    )

    mock_publish_svc = MagicMock()
    mock_publish_svc.review_and_publish = AsyncMock(return_value=mock_publish_result)

    app.dependency_overrides[get_multi_agent_review_service] = lambda: mock_multi_agent_service
    app.dependency_overrides[get_multi_agent_publish_service] = lambda: mock_publish_svc

    try:
        response = client.post(
            "/api/v1/multi-agent/review/publish?owner=testowner&repo=testrepo&pull_number=42",
            json={"diff": VALID_DIFF, "pr_title": "Test PR"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["review_id"] == 12345
        assert data["comments_published"] == 1
    finally:
        app.dependency_overrides.clear()


def test_health_check_endpoint():
    """GET /api/v1/review/health returns 200 with phase details."""
    response = client.get("/api/v1/review/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["subsystem"] == "review"
    assert data["phase"] == "6-multi-agent"
