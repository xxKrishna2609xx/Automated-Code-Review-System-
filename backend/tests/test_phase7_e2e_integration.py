"""
test_phase7_e2e_integration.py
===============================
Full End-to-End Integration Test Suite for Phase 7:
  PR review -> persistence -> history query -> analytics aggregation -> API responses -> export.

Author : AI Code Review Bot — Phase 7 (Stage 7.25)
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.models.persistence_models import (
    PersistedReview,
    ReviewStatus,
    generate_review_key,
)
from app.models.review_models import Issue, Severity
from app.models.agent_models import (
    FinalReview,
    AgentReview,
    AgentCategory,
)
from app.services.review_persistence_service import ReviewPersistenceService
from app.services.analytics_service import AnalyticsService
from app.db.review_repository import ReviewRepository, get_review_repository


class InMemoryE2ERepository(ReviewRepository):
    """In-memory mock repository simulating MongoDB for E2E integration test."""

    def __init__(self):
        self._reviews: dict[str, PersistedReview] = {}

    async def upsert_review(self, review: PersistedReview) -> PersistedReview:
        key = review.review_key
        self._reviews[key] = review
        return review

    async def get_review_by_key(self, review_key: str) -> PersistedReview | None:
        return self._reviews.get(review_key)

    async def get_review_by_id(self, review_id: str) -> PersistedReview | None:
        for r in self._reviews.values():
            if r.id == review_id or r.review_key == review_id:
                return r
        return None

    async def list_reviews(self, filter_dto) -> tuple[list[PersistedReview], int]:
        results = list(self._reviews.values())
        if filter_dto.repository:
            results = [r for r in results if r.repository == filter_dto.repository]
        if filter_dto.severity:
            sev = filter_dto.severity.lower()
            results = [r for r in results if r.severity_counts.get(sev, 0) > 0]
        if filter_dto.search:
            s = filter_dto.search.lower()
            results = [
                r for r in results
                if s in r.pull_request_title.lower() or s in r.review_key.lower()
            ]
        return results, len(results)

    async def count_reviews(self, filter_dto) -> int:
        reviews, count = await self.list_reviews(filter_dto)
        return count


@pytest.fixture
def e2e_repo():
    return InMemoryE2ERepository()


@pytest.fixture
def client(e2e_repo):
    from app.db.review_repository import get_review_repository
    from app.services.analytics_service import get_analytics_service, AnalyticsService
    from app.api.history_router import get_review_repository as history_get_repo
    from app.api.export_router import get_review_repository as export_get_repo

    repo_getter = lambda: e2e_repo
    app.dependency_overrides[get_review_repository] = repo_getter
    app.dependency_overrides[history_get_repo] = repo_getter
    app.dependency_overrides[export_get_repo] = repo_getter
    app.dependency_overrides[get_analytics_service] = lambda: AnalyticsService(e2e_repo)

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_full_phase7_e2e_pipeline(e2e_repo, client):
    """
    E2E Test:
      1. Create a FinalReview (Phase 6 output).
      2. Persist via ReviewPersistenceService.
      3. Query via ReviewRepository.
      4. Aggregate via AnalyticsService.
      5. Fetch via FastAPI Routers (Overview, History, Repos, Security, Agents, Export).
    """

    # 1. Construct FinalReview payload (Phase 6 output)
    issues = [
        Issue(
            title="SQL Injection in Query Builder",
            severity=Severity.CRITICAL,
            category="Security",
            description="Raw string concatenation used in DB query.",
            suggestion="Use parameterized query placeholder.",
            file="app/db/query.py",
            line=42,
        ),
        Issue(
            title="Unused Variable in Loop",
            severity=Severity.LOW,
            category="Code Smell",
            description="Variable temp is declared but never referenced.",
            suggestion="Remove unused variable.",
            file="app/db/query.py",
            line=88,
        ),
    ]

    agent_results = [
        AgentReview(
            agent_name="security_agent",
            category=AgentCategory.SECURITY,
            issues=[issues[0]],
            summary="Found 1 critical security issue.",
            execution_time_ms=320.0,
            success=True,
        ),
        AgentReview(
            agent_name="bug_agent",
            category=AgentCategory.BUG,
            issues=[issues[1]],
            summary="Found 1 low issue.",
            execution_time_ms=280.0,
            success=True,
        ),
        AgentReview(
            agent_name="performance_agent",
            category=AgentCategory.PERFORMANCE,
            issues=[],
            summary="Clean.",
            execution_time_ms=300.0,
            success=True,
        ),
        AgentReview(
            agent_name="documentation_agent",
            category=AgentCategory.DOCUMENTATION,
            issues=[],
            summary="Clean.",
            execution_time_ms=210.0,
            success=True,
        ),
        AgentReview(
            agent_name="testing_agent",
            category=AgentCategory.TESTING,
            issues=[],
            summary="Clean.",
            execution_time_ms=250.0,
            success=True,
        ),
    ]

    final_review = FinalReview(
        overall_score=82,
        summary="Critical security issue found in SQL query construction.",
        issues=issues,
        total_issues=2,
        issues_by_category={"security": 1, "code_smell": 1},
        issues_by_severity={"critical": 1, "low": 1},
        agent_results=agent_results,
        successful_agents=[
            "security_agent",
            "bug_agent",
            "performance_agent",
            "documentation_agent",
            "testing_agent",
        ],
        failed_agents=[],
        execution_time_ms=1360.0,
    )

    # 2. Persist via ReviewPersistenceService
    persistence_service = ReviewPersistenceService(e2e_repo)
    persisted_doc = await persistence_service.save_final_review(
        final_review=final_review,
        owner="acme",
        repo_name="e2e-service",
        pull_request_number=99,
        pull_request_title="feat: Add database search API",
        author="e2e_developer",
        commit_sha="a1b2c3d4e5f6",
    )

    assert persisted_doc.review_key == "acme/e2e-service#99@a1b2c3d4e5f6"
    assert persisted_doc.overall_score == 82
    assert persisted_doc.total_issues == 2

    # 3. Query document directly from repository
    retrieved = await e2e_repo.get_review_by_key("acme/e2e-service#99@a1b2c3d4e5f6")
    assert retrieved is not None
    assert retrieved.author == "e2e_developer"
    assert retrieved.severity_counts["critical"] == 1
    assert retrieved.severity_counts["low"] == 1

    # 4. Analytics Service Aggregations
    analytics_service = AnalyticsService(e2e_repo)

    overview = await analytics_service.get_overview_metrics()
    assert overview["total_prs_reviewed"] == 1
    assert overview["total_issues"] == 2
    assert overview["average_score"] == 82.0
    assert overview["security_issues"] == 1

    repo_analytics = await analytics_service.get_repository_metrics("acme/e2e-service")
    assert repo_analytics["repository_id"] == "acme/e2e-service"
    assert repo_analytics["pr_count"] == 1
    assert repo_analytics["health_score"] < 100.0  # Penalty applied for critical security issue

    sec_analytics = await analytics_service.get_security_metrics()
    assert sec_analytics["total_security_issues"] == 1
    assert sec_analytics["critical_security_issues"] == 1

    agent_analytics = await analytics_service.get_agent_metrics()
    assert agent_analytics["total_agent_executions"] == 5
    assert agent_analytics["agent_success_rates"]["security_agent"] == 100.0

    # 5. FastAPI Endpoints Integration Verification via TestClient
    res_overview = client.get("/api/v1/dashboard/overview")
    assert res_overview.status_code == 200
    assert res_overview.json()["total_prs_reviewed"] == 1

    res_history = client.get("/api/v1/reviews")
    assert res_history.status_code == 200
    assert res_history.json()["total"] == 1
    assert res_history.json()["items"][0]["review_key"] == "acme/e2e-service#99@a1b2c3d4e5f6"

    res_repo = client.get("/api/v1/repositories/acme%2Fe2e-service/analytics")
    assert res_repo.status_code == 200
    assert res_repo.json()["pr_count"] == 1

    res_sec = client.get("/api/v1/analytics/security")
    assert res_sec.status_code == 200
    assert res_sec.json()["critical_security_issues"] == 1

    res_agents = client.get("/api/v1/analytics/agents")
    assert res_agents.status_code == 200
    assert res_agents.json()["total_agent_executions"] == 5

    res_export = client.get("/api/v1/export/reviews?format=csv")
    assert res_export.status_code == 200
    assert "acme/e2e-service#99@a1b2c3d4e5f6" in res_export.text
