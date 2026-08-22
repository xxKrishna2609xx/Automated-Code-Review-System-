"""
fix_service.py  (app.fixes)
============================
Stage 8.8 — Fix Service & Preview Pipeline Orchestrator.

Coordinates the full preview & patch generation pipeline:
    1. Retrieve FixRequest record.
    2. Check eligibility via FixEligibilityService (Stage 8.3).
    3. Build context via FixContextBuilder (Stage 8.4).
    4. Generate patch via FixGenerator (Stage 8.5).
    5. Validate patch via PatchValidator (Stage 8.6).
    6. Validate syntax via SyntaxValidator (Stage 8.7).
    7. Update FixRequest status (READY_FOR_APPROVAL if valid, FAILED/STALE if invalid).
    8. Return FixPreviewResponse.

Author : AI Code Review Bot — Phase 8 (Stage 8.8)
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.db.review_repository import ReviewRepository, get_review_repository
from app.fixes.exceptions import FixIneligibleError, FixNotFoundError, FixValidationError
from app.fixes.fix_context_builder import FixContextBuilder
from app.fixes.fix_eligibility_service import EligibilityResult, FixEligibilityService, RiskLevel
from app.fixes.fix_generator import FixGenerator
from app.fixes.fix_request_service import FixRequestService
from app.fixes.models import FixPatch, FixRequest, FixStatus
from app.fixes.patch_validator import PatchValidationResult, PatchValidator
from app.models.github_models import GitHubFile
from app.models.review_models import Issue, IssueCategory, Severity
from app.validation.syntax_validator import SyntaxValidator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FixPreviewResponse DTO
# ---------------------------------------------------------------------------


class FixPreviewResponse(BaseModel):
    """Response DTO for GET /api/fixes/{fix_request_id} and POST /api/fixes/{fix_request_id}/generate.

    Provides complete visibility into proposed changes, validation results,
    risk level, and eligibility before developer approval.
    """

    fix_request_id: str = Field(..., description="Unique fix request identifier.")
    review_id: str = Field(..., description="Phase 7 PersistedReview document ID.")
    issue_id: str = Field(..., description="Deterministic issue identifier.")
    repository: str = Field(..., description="Target repository slug ('owner/repo').")
    pull_request_number: int = Field(..., ge=1, description="Pull Request number.")
    base_commit_sha: str = Field(..., description="HEAD commit SHA evaluated.")
    file_path: str = Field(..., description="Target relative file path.")
    line: Optional[int] = Field(default=None, description="Target 1-based line number.")
    issue_title: str = Field(..., description="Title of original finding.")
    issue_description: str = Field(..., description="Description of original finding.")
    suggestion: str = Field(default="", description="Original recommendation.")
    status: str = Field(..., description="Current lifecycle state (e.g. READY_FOR_APPROVAL).")

    # Eligibility details
    eligible: bool = Field(..., description="Whether finding is eligible for auto-remediation.")
    risk_level: str = Field(..., description="Risk level (LOW, MEDIUM, HIGH, CRITICAL).")
    eligibility_reason: str = Field(..., description="Explanation of eligibility policy decision.")
    requires_stronger_review: bool = Field(
        default=False,
        description="True if finding requires additional human scrutiny before approval.",
    )

    # Generated patch details (None if not yet generated)
    proposed_patch: Optional[str] = Field(default=None, description="GNU unified diff patch string.")
    explanation: Optional[str] = Field(default=None, description="Plain-English explanation of fix.")
    changed_lines: list[int] = Field(default_factory=list, description="Line numbers modified by fix.")
    original_content_hash: Optional[str] = Field(
        default=None, description="SHA-256 digest of original source content."
    )

    # Validation details
    validation_results: dict[str, str] = Field(
        default_factory=dict, description="Validator check status breakdown."
    )
    syntax_validation: Optional[dict[str, Any]] = Field(
        default=None, description="Syntax validator outcome details."
    )
    error_code: Optional[str] = Field(
        default=None, description="Machine-readable error code if status is FAILED/STALE."
    )

    created_at: datetime.datetime = Field(..., description="Record creation timestamp.")
    updated_at: datetime.datetime = Field(..., description="Record last update timestamp.")


# ---------------------------------------------------------------------------
# In-Memory Fix Request Storage (Pre-Stage 8.17 Persistence)
# ---------------------------------------------------------------------------

_FIX_REQUEST_STORE: Dict[str, FixRequest] = {}
_FIX_PATCH_STORE: Dict[str, FixPatch] = {}
_FIX_VAL_STORE: Dict[str, PatchValidationResult] = {}
_FIX_RESULT_STORE: Dict[str, Any] = {}


def reset_fix_stores() -> None:
    """Helper for unit tests to clear in-memory stores."""
    _FIX_REQUEST_STORE.clear()
    _FIX_PATCH_STORE.clear()
    _FIX_VAL_STORE.clear()
    _FIX_RESULT_STORE.clear()



# ---------------------------------------------------------------------------
# FixService
# ---------------------------------------------------------------------------


class FixService:
    """Orchestrates fix request lifecycle, preview generation, and validation."""

    def __init__(
        self,
        request_service: FixRequestService,
        eligibility_service: Optional[FixEligibilityService] = None,
        context_builder: Optional[FixContextBuilder] = None,
        generator: Optional[FixGenerator] = None,
        patch_validator: Optional[PatchValidator] = None,
        syntax_validator: Optional[SyntaxValidator] = None,
    ) -> None:
        self._req_service = request_service
        self._eligibility_svc = eligibility_service or FixEligibilityService()
        self._context_builder = context_builder or FixContextBuilder()
        self._generator = generator or FixGenerator()
        self._patch_validator = patch_validator or PatchValidator()
        self._syntax_validator = syntax_validator or SyntaxValidator()

    async def create_fix_request(
        self,
        review_id: str,
        issue_id: str,
        created_by: str = "system",
    ) -> FixRequest:
        """Create a FixRequest and store it in memory."""
        fix_req = await self._req_service.create_fix_request(
            review_id=review_id,
            issue_id=issue_id,
            created_by=created_by,
        )
        _FIX_REQUEST_STORE[fix_req.id] = fix_req
        return fix_req

    def get_fix_request(self, fix_request_id: str) -> FixRequest:
        """Retrieve stored FixRequest by ID."""
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req:
            raise FixNotFoundError(f"Fix request '{fix_request_id}' was not found.")
        return fix_req

    def get_fix_preview(self, fix_request_id: str) -> FixPreviewResponse:
        """Fetch current preview status of a FixRequest."""
        fix_req = self.get_fix_request(fix_request_id)
        issue = self._reconstruct_issue(fix_req)
        eligibility = self._eligibility_svc.check(issue)

        patch = _FIX_PATCH_STORE.get(fix_request_id)
        val_res = _FIX_VAL_STORE.get(fix_request_id)

        val_results_dict = val_res.to_dict() if val_res else {}

        status_str = fix_req.status.value if hasattr(fix_req.status, "value") else str(fix_req.status)

        return FixPreviewResponse(
            fix_request_id=fix_req.id,
            review_id=fix_req.review_id,
            issue_id=fix_req.issue_id,
            repository=fix_req.repository,
            pull_request_number=fix_req.pull_request_number,
            base_commit_sha=fix_req.base_commit_sha,
            file_path=fix_req.file_path,
            line=fix_req.line,
            issue_title=fix_req.issue_title,
            issue_description=fix_req.issue_description,
            suggestion=fix_req.suggestion,
            status=status_str,
            eligible=eligibility.eligible,
            risk_level=eligibility.risk_level.value,
            eligibility_reason=eligibility.reason,
            requires_stronger_review=eligibility.requires_stronger_review,
            proposed_patch=patch.patch if patch else None,
            explanation=patch.explanation if patch else None,
            changed_lines=patch.changed_lines if patch else [],
            original_content_hash=patch.original_content_hash if patch else None,
            validation_results=val_results_dict,
            syntax_validation=None,
            error_code=val_res.error_code if val_res else None,
            created_at=fix_req.created_at,
            updated_at=fix_req.updated_at,
        )

    async def generate_fix_preview(
        self,
        fix_request_id: str,
        current_file_content: Optional[str] = None,
        files: Optional[list[GitHubFile]] = None,
    ) -> FixPreviewResponse:
        """Run the complete fix generation & validation pipeline.

        Pipeline steps:
            1. Check eligibility via FixEligibilityService.
            2. Build code context via FixContextBuilder.
            3. Generate minimal patch via FixGenerator.
            4. Validate patch via PatchValidator.
            5. Validate syntax via SyntaxValidator.
            6. Advance status to READY_FOR_APPROVAL (if valid) or FAILED/STALE.

        Args:
            fix_request_id       : Unique FixRequest ID.
            current_file_content : Optional raw target file content.
            files                : Optional pre-fetched list of GitHubFile objects.

        Returns:
            Updated FixPreviewResponse.
        """
        fix_req = self.get_fix_request(fix_request_id)
        fix_req.status = FixStatus.GENERATING
        fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)

        # ── 1. Eligibility Check ─────────────────────────────────────
        issue = self._reconstruct_issue(fix_req)
        eligibility = self._eligibility_svc.check(issue)

        if not eligibility.eligible:
            fix_req.status = FixStatus.REJECTED
            fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
            _FIX_REQUEST_STORE[fix_req.id] = fix_req
            logger.warning("Fix request %s rejected by eligibility policy: %s", fix_req.id, eligibility.reason)
            return self.get_fix_preview(fix_req.id)

        try:
            # ── 2. Build Context ─────────────────────────────────────
            fix_req.status = FixStatus.GENERATING
            context = await self._context_builder.build_context(
                fix_request=fix_req,
                files=files,
                file_content=current_file_content,
            )

            # Update resolved file_path if it was UNRESOLVED
            if fix_req.file_path == "UNRESOLVED":
                fix_req.file_path = context.file_path

            # ── 3. Generate Patch ────────────────────────────────────
            patch = await self._generator.generate_fix(context)
            _FIX_PATCH_STORE[fix_req.id] = patch

            # ── 4. Patch Validation ──────────────────────────────────
            fix_req.status = FixStatus.VALIDATING
            val_result = self._patch_validator.validate(
                fix_patch=patch,
                current_file_content=context.file_content or current_file_content,
                expected_file_path=fix_req.file_path,
            )
            _FIX_VAL_STORE[fix_req.id] = val_result

            if not val_result.valid:
                fix_req.status = FixStatus.STALE if val_result.stale else FixStatus.FAILED
                fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
                _FIX_REQUEST_STORE[fix_req.id] = fix_req
                logger.warning("Patch validation failed for fix request %s: code=%s", fix_req.id, val_result.error_code)
                return self.get_fix_preview(fix_req.id)

            # ── 5. Syntax Validation ──────────────────────────────────
            target_content = val_result.applied_content or context.file_content
            syntax_res = None
            if target_content:
                syntax_val = self._syntax_validator.validate_syntax(
                    content=target_content,
                    language_or_path=fix_req.file_path,
                )
                syntax_res = {
                    "valid": syntax_val.valid,
                    "language": syntax_val.language,
                    "error_message": syntax_val.error_message,
                }
                if not syntax_val.valid:
                    fix_req.status = FixStatus.FAILED
                    fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    _FIX_REQUEST_STORE[fix_req.id] = fix_req
                    logger.warning("Syntax validation failed for fix request %s: %s", fix_req.id, syntax_val.error_message)
                    preview = self.get_fix_preview(fix_req.id)
                    preview.syntax_validation = syntax_res
                    preview.error_code = "SYNTAX_VALIDATION_FAILED"
                    return preview

            # ── 6. Success -> READY_FOR_APPROVAL ─────────────────────
            fix_req.status = FixStatus.READY_FOR_APPROVAL
            fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
            _FIX_REQUEST_STORE[fix_req.id] = fix_req

            preview = self.get_fix_preview(fix_req.id)
            preview.syntax_validation = syntax_res
            return preview

        except Exception as exc:
            logger.exception("Fix generation pipeline error for %s: %s", fix_req.id, exc)
            fix_req.status = FixStatus.FAILED
            fix_req.updated_at = datetime.datetime.now(datetime.timezone.utc)
            _FIX_REQUEST_STORE[fix_req.id] = fix_req
            raise

    @staticmethod
    def _reconstruct_issue(fix_req: FixRequest) -> Issue:
        """Reconstruct Issue model for FixEligibilityService."""
        category_str = fix_req.issue_id.split("-")[0].capitalize()
        cat = IssueCategory.BUG
        try:
            cat = IssueCategory(category_str)
        except ValueError:
            pass

        return Issue(
            title=fix_req.issue_title,
            severity=Severity.MEDIUM,
            category=cat,
            description=fix_req.issue_description,
            suggestion=fix_req.suggestion,
            line=fix_req.line,
        )
