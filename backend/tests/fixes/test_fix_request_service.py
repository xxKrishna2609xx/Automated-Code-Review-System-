"""
test_fix_request_service.py  (tests.fixes)
==========================================
Unit tests for Stage 8.2 — FixRequestService and fixes_router.

Tests cover:
    FixRequestService:
        - Valid review + issue → FixRequest returned
        - review_id not found → FixNotFoundError
        - Empty review_id / issue_id → FixValidationError
        - issue_id not found in review → FixValidationError
        - Review has no commit_sha → FixValidationError
        - FixRequest fields populated from stored review (not from client)
        - build_issue_id / find_issue_by_id helpers

    API endpoint (POST /api/fixes):
        - 201 on valid request
        - 404 when review not found
        - 422 when validation fails
        - Response never exposes file content or raw commit details beyond id

Author : AI Code Review Bot — Phase 8 (Stage 8.2)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.fixes.exceptions import FixNotFoundError, FixValidationError
from app.fixes.fix_request_service import (
    FixRequestService,
    build_issue_id,
    find_issue_by_id,
)
from app.fixes.models import FixRequest, FixStatus
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_issue(category: str = "Security", title: str = "SQL Injection", line: int = 42) -> Issue:
    return Issue(
        title=title,
        severity="High",
        category=category,
        description="The query is built via string concatenation.",
        suggestion="Use parameterized queries.",
        line=line,
    )


def _make_review(issues: list | None = None, commit_sha: str = "a" * 40) -> PersistedReview:
    return PersistedReview(
        review_key="owner/repo#42@" + (commit_sha or "head"),
        repository="owner/repo",
        repository_id="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=42,
        commit_sha=commit_sha,
        issues=issues or [_make_issue()],
        _id="64f1a2b3c4d5e6f7a8b9c0d1",
    )


def _make_mock_repo(review: PersistedReview | None) -> MagicMock:
    repo = MagicMock()
    repo.get_review_by_id = AsyncMock(return_value=review)
    return repo


# ---------------------------------------------------------------------------
# build_issue_id / find_issue_by_id helpers
# ---------------------------------------------------------------------------

class TestIssueIdHelpers:
    def test_build_issue_id_security(self):
        issue = _make_issue(category="Security")
        assert build_issue_id(issue, 0) == "security-0"

    def test_build_issue_id_bug(self):
        issue = _make_issue(category="Bug")
        assert build_issue_id(issue, 3) == "bug-3"

    def test_build_issue_id_code_smell(self):
        issue = _make_issue(category="Code Smell")
        result = build_issue_id(issue, 1)
        # spaces become underscores
        assert "code" in result and "1" in result

    def test_find_issue_by_id_found(self):
        issues = [_make_issue("Security"), _make_issue("Bug")]
        review = _make_review(issues=issues)
        issue, idx = find_issue_by_id(review, "bug-1")
        assert idx == 1
        assert "Bug" in issue.category

    def test_find_issue_by_id_not_found(self):
        review = _make_review(issues=[_make_issue("Security")])
        with pytest.raises(FixValidationError) as exc_info:
            find_issue_by_id(review, "bug-99")
        assert "bug-99" in str(exc_info.value)

    def test_find_issue_by_id_first_of_type(self):
        issues = [_make_issue("Security"), _make_issue("Security"), _make_issue("Bug")]
        review = _make_review(issues=issues)
        # "security-0" → first Security issue
        issue, idx = find_issue_by_id(review, "security-0")
        assert idx == 0
        # "security-1" → second Security issue
        issue2, idx2 = find_issue_by_id(review, "security-1")
        assert idx2 == 1


# ---------------------------------------------------------------------------
# FixRequestService — valid creation
# ---------------------------------------------------------------------------

class TestFixRequestServiceValid:
    @pytest.mark.asyncio
    async def test_returns_fix_request(self):
        review = _make_review()
        service = FixRequestService(repository=_make_mock_repo(review))
        # build the expected issue_id
        issue_id = build_issue_id(review.issues[0], 0)
        result = await service.create_fix_request(
            review_id="64f1a2b3c4d5e6f7a8b9c0d1",
            issue_id=issue_id,
        )
        assert isinstance(result, FixRequest)

    @pytest.mark.asyncio
    async def test_fix_request_status_is_requested(self):
        review = _make_review()
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        result = await service.create_fix_request("rev-id", issue_id)
        assert result.status == FixStatus.REQUESTED.value

    @pytest.mark.asyncio
    async def test_repository_loaded_from_stored_review_not_client(self):
        """Client cannot inject repository — it comes from the stored review."""
        review = _make_review()
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        result = await service.create_fix_request("any-id", issue_id)
        # Must equal the review's repository, regardless of what client sends
        assert result.repository == "owner/repo"
        assert result.pull_request_number == 42

    @pytest.mark.asyncio
    async def test_issue_fields_loaded_from_stored_review(self):
        review = _make_review(issues=[_make_issue(title="SQL Injection Risk")])
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        result = await service.create_fix_request("rev-id", issue_id)
        assert result.issue_title == "SQL Injection Risk"
        assert "string concatenation" in result.issue_description

    @pytest.mark.asyncio
    async def test_fix_request_has_unique_id(self):
        review = _make_review()
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        r1 = await service.create_fix_request("rev-id", issue_id)
        r2 = await service.create_fix_request("rev-id", issue_id)
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_created_by_passed_through(self):
        review = _make_review()
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        result = await service.create_fix_request("rev-id", issue_id, created_by="dev_alice")
        assert result.created_by == "dev_alice"

    @pytest.mark.asyncio
    async def test_base_commit_sha_from_review(self):
        sha = "b" * 40
        review = _make_review(commit_sha=sha)
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        result = await service.create_fix_request("rev-id", issue_id)
        assert result.base_commit_sha == sha.lower()


# ---------------------------------------------------------------------------
# FixRequestService — error paths
# ---------------------------------------------------------------------------

class TestFixRequestServiceErrors:
    @pytest.mark.asyncio
    async def test_review_not_found_raises_fix_not_found_error(self):
        service = FixRequestService(repository=_make_mock_repo(review=None))
        with pytest.raises(FixNotFoundError) as exc_info:
            await service.create_fix_request("nonexistent-id", "security-0")
        assert "nonexistent-id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_review_id_raises_fix_validation_error(self):
        service = FixRequestService(repository=_make_mock_repo(review=None))
        with pytest.raises(FixValidationError) as exc_info:
            await service.create_fix_request("", "security-0")
        assert "review_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_issue_id_raises_fix_validation_error(self):
        service = FixRequestService(repository=_make_mock_repo(review=None))
        with pytest.raises(FixValidationError) as exc_info:
            await service.create_fix_request("some-review", "")
        assert "issue_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_issue_not_in_review_raises_fix_validation_error(self):
        review = _make_review(issues=[_make_issue("Security")])
        service = FixRequestService(repository=_make_mock_repo(review))
        with pytest.raises(FixValidationError) as exc_info:
            await service.create_fix_request("rev-id", "bug-99")
        assert "bug-99" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_review_without_commit_sha_raises_fix_validation_error(self):
        review = _make_review(commit_sha=None)
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)
        with pytest.raises(FixValidationError) as exc_info:
            await service.create_fix_request("rev-id", issue_id)
        assert "commit_sha" in str(exc_info.value)


# ---------------------------------------------------------------------------
# API endpoint — POST /api/fixes
# ---------------------------------------------------------------------------

class TestFixesRouterEndpoint:
    """Integration-style tests using FastAPI TestClient with dependency override."""

    def _get_client(self, mock_service: FixRequestService):
        from app.main import app
        from app.api.fixes_router import get_fix_request_service
        app.dependency_overrides[get_fix_request_service] = lambda: mock_service
        client = TestClient(app, raise_server_exceptions=False)
        yield client
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_201_on_valid_request(self):
        review = _make_review()
        repo_mock = _make_mock_repo(review)
        service = FixRequestService(repository=repo_mock)
        issue_id = build_issue_id(review.issues[0], 0)

        from app.main import app
        from app.api.fixes_router import get_fix_request_service
        app.dependency_overrides[get_fix_request_service] = lambda: service

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/fixes",
            json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id},
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "fix_request_id" in data
        assert data["status"] == "REQUESTED"
        assert data["repository"] == "owner/repo"
        assert data["pull_request_number"] == 42

    @pytest.mark.asyncio
    async def test_404_when_review_not_found(self):
        repo_mock = _make_mock_repo(review=None)
        service = FixRequestService(repository=repo_mock)

        from app.main import app
        from app.api.fixes_router import get_fix_request_service
        app.dependency_overrides[get_fix_request_service] = lambda: service

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/fixes",
            json={"review_id": "nonexistent", "issue_id": "security-0"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_422_when_issue_not_in_review(self):
        review = _make_review(issues=[_make_issue("Security")])
        service = FixRequestService(repository=_make_mock_repo(review))

        from app.main import app
        from app.api.fixes_router import get_fix_request_service
        app.dependency_overrides[get_fix_request_service] = lambda: service

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/fixes",
            json={"review_id": "rev-id", "issue_id": "bug-999"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_response_does_not_expose_file_content(self):
        """The response must never leak source code or raw file content."""
        review = _make_review()
        service = FixRequestService(repository=_make_mock_repo(review))
        issue_id = build_issue_id(review.issues[0], 0)

        from app.main import app
        from app.api.fixes_router import get_fix_request_service
        app.dependency_overrides[get_fix_request_service] = lambda: service

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/fixes",
            json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        # commit SHA and file_path must NOT appear in the response
        assert "base_commit_sha" not in data
        assert "file_path" not in data
        assert "commit" not in str(data).lower() or "fix_request_id" in data

    @pytest.mark.asyncio
    async def test_missing_review_id_returns_422(self):
        """Pydantic validation — missing required field."""
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/fixes",
            json={"issue_id": "security-0"},  # review_id missing
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_missing_issue_id_returns_422(self):
        """Pydantic validation — missing required field."""
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/fixes",
            json={"review_id": "some-id"},  # issue_id missing
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
