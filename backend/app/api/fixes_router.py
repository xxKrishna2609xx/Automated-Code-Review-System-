"""
fixes_router.py  (app.api)
==========================
FastAPI router for Phase 8 Fix & Auto-Remediation endpoints.

Exposes:
    POST /api/fixes                             (Stage 8.2 — Request creation)
    GET  /api/fixes/{fix_request_id}           (Stage 8.8 — Fix preview status)
    POST /api/fixes/{fix_request_id}/generate  (Stage 8.8 — Patch generation & validation)
    POST /api/fixes/{fix_request_id}/approve   (Stage 8.9 — Developer human approval)
    POST /api/fixes/{fix_request_id}/reject    (Stage 8.9 — Developer rejection)

Author : AI Code Review Bot — Phase 8 (Stage 8.9)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.review_repository import ReviewRepository, get_review_repository
from app.fixes.approval_service import (
    ApprovalRequest,
    ApprovalResult,
    ApprovalService,
    RejectionRequest,
    RejectionResult,
)
from app.fixes.exceptions import FixIneligibleError, FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_request_service import FixRequestService
from app.fixes.fix_service import FixPreviewResponse, FixService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response DTOs
# ---------------------------------------------------------------------------


class CreateFixRequest(BaseModel):
    """Request body for POST /api/fixes."""

    review_id: str = Field(
        ...,
        min_length=1,
        description="MongoDB ObjectId hex string of the target PersistedReview.",
    )
    issue_id: str = Field(
        ...,
        min_length=1,
        description='Deterministic issue identifier, e.g. "security-0".',
    )
    created_by: str = Field(
        default="system",
        description="GitHub handle or user identifier of the requester.",
    )


class FixRequestCreatedResponse(BaseModel):
    """Response payload for a successfully created FixRequest."""

    fix_request_id: str = Field(..., description="Unique fix request identifier.")
    status: str = Field(..., description="Current lifecycle state.")
    review_id: str = Field(..., description="Source review identifier.")
    issue_id: str = Field(..., description="Source issue identifier.")
    repository: str = Field(..., description="Resolved 'owner/repo' slug.")
    pull_request_number: int = Field(..., description="Resolved PR number.")
    issue_title: str = Field(..., description="Resolved issue title.")


class GenerateFixRequest(BaseModel):
    """Optional payload for POST /api/fixes/{fix_request_id}/generate."""

    file_content: Optional[str] = Field(
        default=None,
        description="Optional raw file content string at base_commit_sha.",
    )


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_fix_request_service(
    repo: ReviewRepository = Depends(get_review_repository),
) -> FixRequestService:
    """FastAPI dependency that provides a FixRequestService instance."""
    return FixRequestService(repository=repo)


def get_fix_service(
    req_service: FixRequestService = Depends(get_fix_request_service),
) -> FixService:
    """FastAPI dependency that provides a FixService instance."""
    return FixService(request_service=req_service)


def get_approval_service() -> ApprovalService:
    """FastAPI dependency that provides an ApprovalService instance."""
    return ApprovalService()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/fixes",
    response_model=FixRequestCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a fix request for a specific review finding",
    tags=["Fixes"],
)
async def create_fix_request(
    body: CreateFixRequest,
    service: FixService = Depends(get_fix_service),
) -> FixRequestCreatedResponse:
    """Create a FixRequest from a stored Phase 6/7 review finding."""
    try:
        fix_request = await service.create_fix_request(
            review_id=body.review_id,
            issue_id=body.issue_id,
            created_by=body.created_by,
        )
    except FixNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FixValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return FixRequestCreatedResponse(
        fix_request_id=fix_request.id,
        status=fix_request.status,
        review_id=fix_request.review_id,
        issue_id=fix_request.issue_id,
        repository=fix_request.repository,
        pull_request_number=fix_request.pull_request_number,
        issue_title=fix_request.issue_title,
    )


@router.get(
    "/fixes/{fix_request_id}",
    response_model=FixPreviewResponse,
    summary="Get detailed preview status of a FixRequest",
    tags=["Fixes"],
)
async def get_fix_preview(
    fix_request_id: str,
    service: FixService = Depends(get_fix_service),
) -> FixPreviewResponse:
    """Fetch current preview details, eligibility, and proposed patch for a FixRequest."""
    try:
        return service.get_fix_preview(fix_request_id)
    except FixNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/fixes/{fix_request_id}/generate",
    response_model=FixPreviewResponse,
    summary="Generate AI fix patch and run validation pipeline",
    tags=["Fixes"],
)
async def generate_fix_preview(
    fix_request_id: str,
    body: Optional[GenerateFixRequest] = None,
    service: FixService = Depends(get_fix_service),
) -> FixPreviewResponse:
    """Trigger the patch generation & multi-check validation pipeline for a FixRequest."""
    file_content = body.file_content if body else None
    try:
        return await service.generate_fix_preview(
            fix_request_id=fix_request_id,
            current_file_content=file_content,
        )
    except FixNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FixValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "/fixes/{fix_request_id}/approve",
    response_model=ApprovalResult,
    summary="Approve an AI-generated code fix proposal",
    tags=["Fixes"],
)
async def approve_fix(
    fix_request_id: str,
    body: Optional[ApprovalRequest] = None,
    approval_svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalResult:
    """Explicitly approve an AI-generated fix proposal after re-validating patch integrity."""
    user_id = body.user_id if body else "developer"
    note = body.note if body else None
    content = body.file_content if body else None

    try:
        return approval_svc.approve_fix(
            fix_request_id=fix_request_id,
            user_id=user_id,
            note=note,
            current_file_content=content,
        )
    except FixNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FixStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except FixValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "/fixes/{fix_request_id}/reject",
    response_model=RejectionResult,
    summary="Reject an AI-generated code fix proposal",
    tags=["Fixes"],
)
async def reject_fix(
    fix_request_id: str,
    body: Optional[RejectionRequest] = None,
    approval_svc: ApprovalService = Depends(get_approval_service),
) -> RejectionResult:
    """Explicitly reject an AI-generated fix proposal."""
    user_id = body.user_id if body else "developer"
    reason = body.reason if body else None

    try:
        return approval_svc.reject_fix(
            fix_request_id=fix_request_id,
            user_id=user_id,
            reason=reason,
        )
    except FixNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FixStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
