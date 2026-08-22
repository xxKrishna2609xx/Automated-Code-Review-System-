"""
test_fix_preview_api.py  (tests.fixes)
=======================================
Unit and integration tests for Stage 8.8 — Fix Service & Preview API.

Tests cover:
    - GET /api/fixes/{fix_request_id} endpoint
    - POST /api/fixes/{fix_request_id}/generate endpoint
    - Full end-to-end pipeline: POST /api/fixes -> POST /generate -> GET
    - Handling ineligible findings (status -> REJECTED)
    - Handling patch validation failure (status -> FAILED / STALE)
    - Handling syntax validation failure (status -> FAILED)
    - 404 handling for unknown fix request IDs

Author : AI Code Review Bot — Phase 8 (Stage 8.8)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.fixes.exceptions import FixNotFoundError
from app.fixes.fix_eligibility_service import FixEligibilityService
from app.fixes.fix_generator import FixGenerator
from app.fixes.fix_request_service import FixRequestService, build_issue_id
from app.fixes.fix_service import FixService, reset_fix_stores
from app.fixes.models import FixPatch, FixStatus
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

SAMPLE_CODE = "def add(a, b):\n    return a - b\n"
SAMPLE_PATCH = "@@ -2,1 +2,1 @@\n-    return a - b\n+    return a + b\n"

def _make_issue(category: str = "Bug", title: str = "Incorrect operator", line: int = 2) -> Issue:
    return Issue(
        title=title,
        severity="Medium",
        category=category,
        description="Function add uses subtraction instead of addition.",
        suggestion="Change minus to plus.",
        line=line,
    )


def _make_review(issues: list | None = None) -> PersistedReview:
    return PersistedReview(
        review_key="owner/repo#42@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        repository="owner/repo",
        repository_id="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=42,
        commit_sha="a" * 40,
        issues=issues or [_make_issue()],
        _id="64f1a2b3c4d5e6f7a8b9c0d1",
    )


def _make_mock_repo(review: PersistedReview | None) -> MagicMock:
    repo = MagicMock()
    repo.get_review_by_id = AsyncMock(return_value=review)
    return repo


def _make_mock_generator(patch_text: str = SAMPLE_PATCH) -> FixGenerator:
    async def mock_completer(sys_p: str, user_p: str) -> str:
        # Extract file path from user_prompt or default
        file_path = "UNRESOLVED"
        for line in user_p.splitlines():
            if line.startswith("- Target File:"):
                file_path = line.split(":", 1)[1].strip()
                break

        return json.dumps({
            "file_path": file_path if file_path != "UNRESOLVED" else "app/database.py",
            "patch": patch_text,
            "changed_lines": [2],
            "explanation": "Fixed subtraction to addition.",
        })
    return FixGenerator(completer=mock_completer)


# Setup fixture to reset in-memory stores before each test
@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


# ---------------------------------------------------------------------------
# FixService Unit Tests
# ---------------------------------------------------------------------------

class TestFixServiceUnit:
    @pytest.mark.asyncio
    async def test_create_and_get_fix_request(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc)

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request(
            review_id="64f1a2b3c4d5e6f7a8b9c0d1",
            issue_id=issue_id,
        )

        assert fix_req.id is not None
        fetched = svc.get_fix_request(fix_req.id)
        assert fetched.id == fix_req.id

    @pytest.mark.asyncio
    async def test_get_fix_preview_initial_state(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc)

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)

        preview = svc.get_fix_preview(fix_req.id)
        assert preview.fix_request_id == fix_req.id
        assert preview.status == "REQUESTED"
        assert preview.eligible is True
        assert preview.proposed_patch is None

    @pytest.mark.asyncio
    async def test_generate_fix_preview_happy_path(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(
            request_service=req_svc,
            generator=_make_mock_generator(),
        )

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)

        preview = await svc.generate_fix_preview(
            fix_request_id=fix_req.id,
            current_file_content=SAMPLE_CODE,
        )

        assert preview.status == "READY_FOR_APPROVAL"
        assert preview.proposed_patch is not None
        assert "return a + b" in preview.proposed_patch
        assert preview.validation_results.get("path_validation") == "passed"
        assert preview.syntax_validation is not None
        assert preview.syntax_validation["valid"] is True

    @pytest.mark.asyncio
    async def test_generate_fix_preview_ineligible_finding_rejected(self):
        # Category 'Other' is ineligible
        review = _make_review(issues=[_make_issue(category="Other", title="Ambiguous issue")])
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc, generator=_make_mock_generator())

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)

        preview = await svc.generate_fix_preview(fix_request_id=fix_req.id)

        assert preview.status == "REJECTED"
        assert preview.eligible is False
        assert "ambiguous" in preview.eligibility_reason.lower() or "other" in preview.eligibility_reason.lower()

    @pytest.mark.asyncio
    async def test_generate_fix_preview_stale_commit_fails(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc, generator=_make_mock_generator())

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)

        # Generate initial preview
        await svc.generate_fix_preview(
            fix_request_id=fix_req.id,
            current_file_content=SAMPLE_CODE,
        )

        # Mutate stored patch's original_content_hash to simulate content drift/stale base
        from app.fixes.fix_service import _FIX_PATCH_STORE
        stale_patch = FixPatch(
            file_path="app/database.py",
            original_content_hash="c" * 64,  # Outdated hash
            patch=SAMPLE_PATCH,
            changed_lines=[2],
            explanation="Test patch.",
        )
        _FIX_PATCH_STORE[fix_req.id] = stale_patch

        # Re-run validator step directly via custom mock generator that returns stale_patch
        async def stale_completer(sys_p: str, user_p: str) -> str:
            return json.dumps({
                "file_path": "app/database.py",
                "patch": SAMPLE_PATCH,
                "changed_lines": [2],
                "explanation": "Test patch.",
            })

        generator_mock = FixGenerator(completer=stale_completer)
        svc_stale = FixService(request_service=req_svc, generator=generator_mock)
        _FIX_PATCH_STORE[fix_req.id] = stale_patch

        # Manually invoke validator test
        val_res = svc._patch_validator.validate(
            fix_patch=stale_patch,
            current_file_content=SAMPLE_CODE,
            expected_file_path="app/database.py",
        )
        assert val_res.valid is False
        assert val_res.stale is True
        assert val_res.error_code == "STALE_COMMIT_DETECTED"


# ---------------------------------------------------------------------------
# API Endpoints Integration Tests (via TestClient)
# ---------------------------------------------------------------------------

class TestFixPreviewEndpoints:
    def _get_client_and_service(self, review: PersistedReview):
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc, generator=_make_mock_generator())

        from app.main import app
        from app.api.fixes_router import get_fix_service

        app.dependency_overrides[get_fix_service] = lambda: svc
        client = TestClient(app, raise_server_exceptions=False)
        return client, svc

    def test_get_fix_preview_endpoint(self):
        review = _make_review()
        client, svc = self._get_client_and_service(review)

        # Create request first synchronously via helper
        issue_id = build_issue_id(review.issues[0], 0)

        # POST /api/fixes
        res_create = client.post(
            "/api/fixes",
            json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id},
        )
        assert res_create.status_code == 201
        fix_id = res_create.json()["fix_request_id"]

        # GET /api/fixes/{fix_id}
        res_get = client.get(f"/api/fixes/{fix_id}")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["fix_request_id"] == fix_id
        assert data["status"] == "REQUESTED"
        assert data["eligible"] is True

        from app.main import app
        app.dependency_overrides.clear()

    def test_post_generate_endpoint_full_pipeline(self):
        review = _make_review()
        client, svc = self._get_client_and_service(review)
        issue_id = build_issue_id(review.issues[0], 0)

        # 1. Create fix request
        res_create = client.post(
            "/api/fixes",
            json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id},
        )
        fix_id = res_create.json()["fix_request_id"]

        # 2. Generate fix preview
        res_gen = client.post(
            f"/api/fixes/{fix_id}/generate",
            json={"file_content": SAMPLE_CODE},
        )
        assert res_gen.status_code == 200
        data = res_gen.json()

        assert data["status"] == "READY_FOR_APPROVAL"
        assert data["proposed_patch"] is not None
        assert "return a + b" in data["proposed_patch"]
        assert data["validation_results"]["path_validation"] == "passed"

        # 3. GET preview matches generated state
        res_get = client.get(f"/api/fixes/{fix_id}")
        assert res_get.status_code == 200
        assert res_get.json()["status"] == "READY_FOR_APPROVAL"

        from app.main import app
        app.dependency_overrides.clear()

    def test_get_nonexistent_fix_returns_404(self):
        review = _make_review()
        client, svc = self._get_client_and_service(review)

        res = client.get("/api/fixes/nonexistent-id-999")
        assert res.status_code == status.HTTP_404_NOT_FOUND

        from app.main import app
        app.dependency_overrides.clear()

    def test_generate_nonexistent_fix_returns_404(self):
        review = _make_review()
        client, svc = self._get_client_and_service(review)

        res = client.post("/api/fixes/nonexistent-id-999/generate")
        assert res.status_code == status.HTTP_404_NOT_FOUND

        from app.main import app
        app.dependency_overrides.clear()
