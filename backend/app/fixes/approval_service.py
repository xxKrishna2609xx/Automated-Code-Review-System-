"""
approval_service.py  (app.fixes)
================================
Stage 8.9 — Human Approval & Rejection Service.

Handles explicit human approval and rejection gates for AI-generated fixes.

Design principles (Phase 8 spec §12):
    - NEVER automatically apply generated fixes. Explicit human approval is required.
    - Approval must verify:
        * FixRequest exists.
        * Status == READY_FOR_APPROVAL.
        * Proposed patch exists and is still valid (re-validated at approval time).
        * Content hash is unchanged (no commit drift since generation).
        * Requesting user is recorded.
    - Updates status to APPROVED upon successful re-validation.
    - Rejection records user, timestamp, optional reason, and updates status to REJECTED.

Author : AI Code Review Bot — Phase 8 (Stage 8.9)
"""

from __future__ import annotations

import datetime
import logging
from typing import Dict, Optional

from pydantic import BaseModel, Field

from app.fixes.exceptions import FixNotFoundError, FixStateError, FixValidationError
from app.fixes.fix_service import _FIX_PATCH_STORE, _FIX_REQUEST_STORE, _FIX_VAL_STORE
from app.fixes.models import FixPatch, FixRequest, FixStatus
from app.fixes.patch_validator import PatchValidator
from app.validation.syntax_validator import SyntaxValidator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Approval & Rejection DTOs
# ---------------------------------------------------------------------------


class ApprovalRequest(BaseModel):
    """Payload for approving a FixRequest."""

    user_id: str = Field(
        default="developer",
        description="GitHub handle or user ID of the approving developer.",
    )
    note: Optional[str] = Field(
        default=None,
        description="Optional approval note or review comment.",
    )
    file_content: Optional[str] = Field(
        default=None,
        description="Optional current file content at approval time for re-validation.",
    )


class RejectionRequest(BaseModel):
    """Payload for rejecting a FixRequest."""

    user_id: str = Field(
        default="developer",
        description="GitHub handle or user ID of the rejecting developer.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for rejecting the fix.",
    )


class ApprovalResult(BaseModel):
    """Result payload after successful approval."""

    fix_request_id: str = Field(..., description="Target FixRequest ID.")
    status: str = Field(..., description="Updated status (always APPROVED).")
    approved_by: str = Field(..., description="User ID of approver.")
    approved_at: datetime.datetime = Field(..., description="Approval UTC timestamp.")
    note: Optional[str] = Field(default=None, description="Optional approval note.")


class RejectionResult(BaseModel):
    """Result payload after rejection."""

    fix_request_id: str = Field(..., description="Target FixRequest ID.")
    status: str = Field(..., description="Updated status (always REJECTED).")
    rejected_by: str = Field(..., description="User ID of rejecter.")
    rejected_at: datetime.datetime = Field(..., description="Rejection UTC timestamp.")
    reason: Optional[str] = Field(default=None, description="Optional rejection reason.")


# ---------------------------------------------------------------------------
# In-Memory Approval Audit Store (Pre-Stage 8.17 Persistence)
# ---------------------------------------------------------------------------

_APPROVAL_AUDIT_STORE: Dict[str, dict] = {}


def reset_approval_store() -> None:
    """Helper for unit tests."""
    _APPROVAL_AUDIT_STORE.clear()


# ---------------------------------------------------------------------------
# ApprovalService
# ---------------------------------------------------------------------------


class ApprovalService:
    """Service handling developer approval and rejection of AI code fixes.

    Args:
        patch_validator  : Optional PatchValidator instance for re-validation.
        syntax_validator : Optional SyntaxValidator instance for re-validation.
    """

    def __init__(
        self,
        patch_validator: Optional[PatchValidator] = None,
        syntax_validator: Optional[SyntaxValidator] = None,
    ) -> None:
        self._patch_validator = patch_validator or PatchValidator()
        self._syntax_validator = syntax_validator or SyntaxValidator()

    def approve_fix(
        self,
        fix_request_id: str,
        user_id: str = "developer",
        note: Optional[str] = None,
        current_file_content: Optional[str] = None,
    ) -> ApprovalResult:
        """Approve an AI fix proposal after verifying state and patch integrity.

        Args:
            fix_request_id       : Target FixRequest ID.
            user_id              : Handle/ID of approving developer.
            note                 : Optional approval comment.
            current_file_content : Optional raw source content at approval time.

        Returns:
            ApprovalResult detailing the approval event.

        Raises:
            FixNotFoundError   : If FixRequest does not exist.
            FixStateError      : If FixRequest status is not READY_FOR_APPROVAL.
            FixValidationError : If patch is missing or re-validation fails due to drift.
        """
        logger.info("Processing fix approval for %s by user %s", fix_request_id, user_id)

        # ── 1. Fetch FixRequest ──────────────────────────────────────
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")

        # ── 2. Verify State ──────────────────────────────────────────
        current_status = fix_req.status.value if hasattr(fix_req.status, "value") else str(fix_req.status)
        if current_status != FixStatus.READY_FOR_APPROVAL.value:
            raise FixStateError(
                f"Cannot approve fix request '{fix_request_id}' in state '{current_status}'. "
                f"Fix request must be in state 'READY_FOR_APPROVAL'."
            )

        # ── 3. Fetch Stored FixPatch ──────────────────────────────────
        patch = _FIX_PATCH_STORE.get(fix_request_id)
        if not patch:
            raise FixValidationError(
                f"No generated patch found for fix request '{fix_request_id}'. "
                "Generate a fix preview before approval."
            )

        # ── 4. Re-Validate Patch & Content Hash Integrity ────────────
        val_res = self._patch_validator.validate(
            fix_patch=patch,
            current_file_content=current_file_content,
            expected_file_path=fix_req.file_path,
        )

        if not val_res.valid:
            if val_res.stale:
                fix_req.status = FixStatus.STALE
                fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
                _FIX_REQUEST_STORE[fix_req.id] = fix_req
                raise FixStateError(
                    f"Approval failed: file content has drifted since fix generation. "
                    f"Fix status set to STALE. Generate a new preview."
                )

            fix_req.status = FixStatus.FAILED
            fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
            _FIX_REQUEST_STORE[fix_req.id] = fix_req
            raise FixValidationError(f"Approval failed re-validation: {val_res.error_code}")

        # ── 5. Re-Validate Syntax ─────────────────────────────────────
        target_content = val_res.applied_content or current_file_content
        if target_content:
            syn_res = self._syntax_validator.validate_syntax(
                content=target_content,
                language_or_path=fix_req.file_path,
            )
            if not syn_res.valid:
                fix_req.status = FixStatus.FAILED
                fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
                _FIX_REQUEST_STORE[fix_req.id] = fix_req
                raise FixValidationError(f"Approval failed syntax re-validation: {syn_res.error_message}")

        # ── 6. Apply Approval ─────────────────────────────────────────
        now = datetime.datetime.now(datetime.timezone.utc)
        fix_req.status = FixStatus.APPROVED
        fix_req.updated_at = now
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        audit_entry = {
            "fix_request_id": fix_req.id,
            "action": "APPROVED",
            "user_id": user_id,
            "timestamp": now,
            "note": note,
        }
        _APPROVAL_AUDIT_STORE[fix_req.id] = audit_entry

        logger.info("Fix request %s successfully APPROVED by %s", fix_req.id, user_id)

        return ApprovalResult(
            fix_request_id=fix_req.id,
            status=FixStatus.APPROVED.value,
            approved_by=user_id,
            approved_at=now,
            note=note,
        )

    def reject_fix(
        self,
        fix_request_id: str,
        user_id: str = "developer",
        reason: Optional[str] = None,
    ) -> RejectionResult:
        """Reject an AI fix proposal.

        Args:
            fix_request_id : Target FixRequest ID.
            user_id        : Handle/ID of rejecting developer.
            reason         : Optional reason for rejection.

        Returns:
            RejectionResult detailing the rejection event.

        Raises:
            FixNotFoundError : If FixRequest does not exist.
            FixStateError    : If FixRequest is already in a terminal state.
        """
        logger.info("Processing fix rejection for %s by user %s", fix_request_id, user_id)

        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")

        current_status = fix_req.status.value if hasattr(fix_req.status, "value") else str(fix_req.status)
        if current_status in (FixStatus.COMPLETED.value, FixStatus.COMMITTED.value, FixStatus.PR_CREATED.value):
            raise FixStateError(
                f"Cannot reject fix request '{fix_request_id}' in state '{current_status}'. "
                "Fix has already been applied/committed."
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        fix_req.status = FixStatus.REJECTED
        fix_req.updated_at = now
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        audit_entry = {
            "fix_request_id": fix_req.id,
            "action": "REJECTED",
            "user_id": user_id,
            "timestamp": now,
            "reason": reason,
        }
        _APPROVAL_AUDIT_STORE[fix_req.id] = audit_entry

        logger.info("Fix request %s successfully REJECTED by %s", fix_req.id, user_id)

        return RejectionResult(
            fix_request_id=fix_req.id,
            status=FixStatus.REJECTED.value,
            rejected_by=user_id,
            rejected_at=now,
            reason=reason,
        )
