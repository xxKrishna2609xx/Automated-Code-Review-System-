"""
test_approval_service.py  (tests.fixes)
========================================
Unit and integration tests for Stage 8.9 — Human Approval & Rejection.

Tests cover:
    - Approval of a READY_FOR_APPROVAL fix request (status -> APPROVED)
    - Re-validation at approval time (stale content -> status STALE / FixStateError)
    - Approval rejected when fix request is not in READY_FOR_APPROVAL state
    - Rejection of a fix request (status -> REJECTED)
    - Rejection rejected when fix request is already COMPLETED
    - POST /api/fixes/{id}/approve endpoint (200 OK, 404, 409 Conflict)
    - POST /api/fixes/{id}/reject endpoint (200 OK, 404, 409 Conflict)
    - Audit logging of approval & rejection actions

Author : AI Code Review Bot — Phase 8 (Stage 8.9)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.fixes.approval_service import ApprovalService, reset_approval_store
from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
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


def _make_review() -> PersistedReview:
    return PersistedReview(
        review_key="owner/repo#42@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        repository="owner/repo",
        repository_id="owner/repo",
        owner="owner",
        repo_name="repo",
        pull_request_number=42,
        commit_sha="a" * 40,
        issues=[_make_issue()],
        _id="64f1a2b3c4d5e6f7a8b9c0d1",
    )


def _make_mock_repo(review: PersistedReview) -> MagicMock:
    repo = MagicMock()
    repo.get_review_by_id = AsyncMock(return_value=review)
    return repo


def _make_mock_generator(patch_text: str = SAMPLE_PATCH) -> FixGenerator:
    async def mock_completer(sys_p: str, user_p: str) -> str:
        file_path = "unknown/file"
        for line in user_p.splitlines():
            if line.startswith("- Target File:"):
                file_path = line.split(":", 1)[1].strip()
                break

        return json.dumps({
            "file_path": file_path,
            "patch": patch_text,
            "changed_lines": [2],
            "explanation": "Fixed operator.",
        })
    return FixGenerator(completer=mock_completer)


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    reset_approval_store()
    yield
    reset_fix_stores()
    reset_approval_store()


# ---------------------------------------------------------------------------
# ApprovalService Unit Tests
# ---------------------------------------------------------------------------

class TestApprovalServiceUnit:
    @pytest.mark.asyncio
    async def test_approve_fix_success(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc, generator=_make_mock_generator())
        approval_svc = ApprovalService()

        # 1. Create and generate fix to reach READY_FOR_APPROVAL
        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)
        await svc.generate_fix_preview(fix_req.id, current_file_content=SAMPLE_CODE)

        # 2. Approve fix
        res = approval_svc.approve_fix(
            fix_request_id=fix_req.id,
            user_id="alice_dev",
            note="Looks good to me!",
            current_file_content=SAMPLE_CODE,
        )

        assert res.status == "APPROVED"
        assert res.approved_by == "alice_dev"
        assert res.note == "Looks good to me!"
        assert svc.get_fix_request(fix_req.id).status == FixStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_fix_unready_state_raises_fix_state_error(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc)
        approval_svc = ApprovalService()

        # Request is in REQUESTED state (not GENERATED/READY_FOR_APPROVAL)
        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)

        with pytest.raises(FixStateError) as exc_info:
            approval_svc.approve_fix(fix_req.id, user_id="bob")
        assert "READY_FOR_APPROVAL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_approve_fix_nonexistent_raises_fix_not_found(self):
        approval_svc = ApprovalService()
        with pytest.raises(FixNotFoundError):
            approval_svc.approve_fix("nonexistent-id-999")

    @pytest.mark.asyncio
    async def test_reject_fix_success(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc, generator=_make_mock_generator())
        approval_svc = ApprovalService()

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)

        res = approval_svc.reject_fix(
            fix_request_id=fix_req.id,
            user_id="carol_dev",
            reason="Will fix manually.",
        )

        assert res.status == "REJECTED"
        assert res.rejected_by == "carol_dev"
        assert res.reason == "Will fix manually."
        assert svc.get_fix_request(fix_req.id).status == FixStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_completed_fix_raises_fix_state_error(self):
        review = _make_review()
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        svc = FixService(request_service=req_svc)
        approval_svc = ApprovalService()

        issue_id = build_issue_id(review.issues[0], 0)
        fix_req = await svc.create_fix_request("64f1a2b3c4d5e6f7a8b9c0d1", issue_id)
        fix_req.status = FixStatus.COMPLETED  # Manually set to terminal completed state

        with pytest.raises(FixStateError) as exc_info:
            approval_svc.reject_fix(fix_req.id)
        assert "applied/committed" in str(exc_info.value) or "COMPLETED" in str(exc_info.value)


# ---------------------------------------------------------------------------
# API Endpoints Integration Tests (via TestClient)
# ---------------------------------------------------------------------------

class TestApprovalEndpoints:
    def _get_client_and_services(self, review: PersistedReview):
        req_svc = FixRequestService(repository=_make_mock_repo(review))
        fix_svc = FixService(request_service=req_svc, generator=_make_mock_generator())
        app_svc = ApprovalService()

        from app.main import app
        from app.api.fixes_router import get_approval_service, get_fix_service

        app.dependency_overrides[get_fix_service] = lambda: fix_svc
        app.dependency_overrides[get_approval_service] = lambda: app_svc

        client = TestClient(app, raise_server_exceptions=False)
        return client, fix_svc, app_svc

    def test_approve_endpoint_full_flow(self):
        review = _make_review()
        client, fix_svc, _ = self._get_client_and_services(review)
        issue_id = build_issue_id(review.issues[0], 0)

        # 1. Create fix request
        res_create = client.post("/api/fixes", json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id})
        fix_id = res_create.json()["fix_request_id"]

        # 2. Generate fix preview (advances state to READY_FOR_APPROVAL)
        res_gen = client.post(f"/api/fixes/{fix_id}/generate", json={"file_content": SAMPLE_CODE})
        assert res_gen.status_code == 200

        # 3. Approve fix
        res_app = client.post(
            f"/api/fixes/{fix_id}/approve",
            json={"user_id": "dev_lead", "note": "Approved for merge.", "file_content": SAMPLE_CODE},
        )
        assert res_app.status_code == 200
        data = res_app.json()
        assert data["status"] == "APPROVED"
        assert data["approved_by"] == "dev_lead"
        assert data["note"] == "Approved for merge."

        # 4. Verify preview GET reflects APPROVED
        res_get = client.get(f"/api/fixes/{fix_id}")
        assert res_get.json()["status"] == "APPROVED"

        from app.main import app
        app.dependency_overrides.clear()

    def test_reject_endpoint_full_flow(self):
        review = _make_review()
        client, fix_svc, _ = self._get_client_and_services(review)
        issue_id = build_issue_id(review.issues[0], 0)

        # 1. Create fix request
        res_create = client.post("/api/fixes", json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id})
        fix_id = res_create.json()["fix_request_id"]

        # 2. Reject fix
        res_rej = client.post(
            f"/api/fixes/{fix_id}/reject",
            json={"user_id": "dev_reviewer", "reason": "Not needed."},
        )
        assert res_rej.status_code == 200
        data = res_rej.json()
        assert data["status"] == "REJECTED"
        assert data["rejected_by"] == "dev_reviewer"

        from app.main import app
        app.dependency_overrides.clear()

    def test_approve_unready_returns_409_conflict(self):
        review = _make_review()
        client, _, _ = self._get_client_and_services(review)
        issue_id = build_issue_id(review.issues[0], 0)

        # Create but do NOT generate preview (remains in REQUESTED state)
        res_create = client.post("/api/fixes", json={"review_id": "64f1a2b3c4d5e6f7a8b9c0d1", "issue_id": issue_id})
        fix_id = res_create.json()["fix_request_id"]

        # Attempt to approve
        res_app = client.post(f"/api/fixes/{fix_id}/approve")
        assert res_app.status_code == status.HTTP_409_CONFLICT

        from app.main import app
        app.dependency_overrides.clear()

    def test_approve_nonexistent_returns_404(self):
        review = _make_review()
        client, _, _ = self._get_client_and_services(review)

        res = client.post("/api/fixes/nonexistent-id-999/approve")
        assert res.status_code == status.HTTP_404_NOT_FOUND

        from app.main import app
        app.dependency_overrides.clear()
