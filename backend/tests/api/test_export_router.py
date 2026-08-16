"""
test_export_router.py
======================
Integration tests for backend export API router (Stage 7.22).
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db.review_repository import get_review_repository
from app.models.persistence_models import PersistedReview, ReviewStatus

class DummyExportRepository:
    async def list_reviews(self, filter_dto):
        return [
            PersistedReview(
                review_key="acme/backend#101",
                repository="acme/backend",
                owner="acme",
                repo_name="backend",
                pull_request_number=101,
                pull_request_title="Export Test PR",
                author="exporter",
                overall_score=88,
                total_issues=2,
                severity_counts={"critical": 0, "high": 1, "medium": 1, "low": 0},
                category_counts={"security": 1, "bug": 1},
                review_duration_ms=1200,
                review_status=ReviewStatus.COMPLETED,
                created_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
            )
        ], 1

@pytest.fixture
def client():
    app.dependency_overrides[get_review_repository] = lambda: DummyExportRepository()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def test_export_reviews_json(client):
    response = client.get("/api/v1/export/reviews?format=json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    data = response.json()
    assert len(data) == 1
    assert data[0]["review_key"] == "acme/backend#101"

def test_export_reviews_csv(client):
    response = client.get("/api/v1/export/reviews?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "acme/backend#101" in response.text
    assert "Export Test PR" in response.text

def test_export_reviews_markdown(client):
    response = client.get("/api/v1/export/reviews?format=markdown")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "# AI Code Review System — Exported Report" in response.text
    assert "`acme/backend#101`" in response.text

def test_export_reviews_invalid_format(client):
    response = client.get("/api/v1/export/reviews?format=invalid_fmt")
    assert response.status_code == 400
    assert "Unsupported export format" in response.json()["detail"]
