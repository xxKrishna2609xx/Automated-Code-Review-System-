"""
recovery_service.py  (app.fixes)
=================================
Stage 8.25 — Failure Recovery & Safe State Transition Service.

Handles error recovery, stale commit detection, and state rollbacks for AI Fixes.

Invariants:
    - Never leave partial branch mutations on GitHub.
    - Persist clear error diagnosis and error_code on failure.
    - Support explicit developer retry from FAILED / STALE state.

Author : AI Code Review Bot — Phase 8 (Stage 8.25)
"""

from __future__ import annotations

import logging
from typing import Optional

from app.db.fix_repository import FixRepository
from app.fixes.exceptions import FixNotFoundError, FixStateError
from app.fixes.fix_service import _FIX_REQUEST_STORE, _FIX_RESULT_STORE
from app.fixes.models import FixRequest, FixResult, FixStatus

logger = logging.getLogger(__name__)


class FixRecoveryService:
    """Service handling state transitions during failures and retry workflows."""

    def __init__(self, repository: Optional[FixRepository] = None) -> None:
        self._repository = repository

    async def mark_fix_failed(
        self,
        fix_request_id: str,
        error_message: str,
        error_code: str = "FIX_GENERATION_FAILED",
    ) -> FixRequest:
        """Transition a FixRequest to FAILED status with diagnostic error information.

        Args:
            fix_request_id : Unique FixRequest ID.
            error_message  : Human-readable failure explanation.
            error_code     : Standardized error code identifier.

        Returns:
            Updated FixRequest instance.
        """
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req and self._repository:
            fix_req = await self._repository.get_fix_request(fix_request_id)

        if not fix_req:
            raise FixNotFoundError(f"FixRequest with ID '{fix_request_id}' not found.")

        updated_req = fix_req.model_copy(update={"status": FixStatus.FAILED})
        _FIX_REQUEST_STORE[fix_request_id] = updated_req

        # Also store failure audit result
        failure_result = FixResult(
            fix_request_id=fix_request_id,
            status=FixStatus.FAILED,
            original_issue_resolved=False,
            new_issues_detected=False,
            post_fix_review_id=None,
        )
        _FIX_RESULT_STORE[fix_request_id] = failure_result

        if self._repository:
            await self._repository.upsert_fix_request(updated_req)
            await self._repository.upsert_fix_result(failure_result)

        logger.error("Marked FixRequest %s as FAILED (code=%s): %s", fix_request_id, error_code, error_message)
        return updated_req

    async def mark_fix_stale(self, fix_request_id: str, reason: str) -> FixRequest:
        """Transition a FixRequest to STALE status when base SHA or target lines change.

        Args:
            fix_request_id : Unique FixRequest ID.
            reason         : Reason for staleness.

        Returns:
            Updated FixRequest instance.
        """
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req and self._repository:
            fix_req = await self._repository.get_fix_request(fix_request_id)

        if not fix_req:
            raise FixNotFoundError(f"FixRequest with ID '{fix_request_id}' not found.")

        updated_req = fix_req.model_copy(update={"status": FixStatus.STALE})
        _FIX_REQUEST_STORE[fix_request_id] = updated_req

        if self._repository:
            await self._repository.upsert_fix_request(updated_req)

        logger.warning("Marked FixRequest %s as STALE: %s", fix_request_id, reason)
        return updated_req

    async def retry_fix_request(self, fix_request_id: str) -> FixRequest:
        """Reset a FAILED or STALE FixRequest back to REQUESTED for developer retry.

        Args:
            fix_request_id : Unique FixRequest ID.

        Returns:
            Reset FixRequest instance.

        Raises:
            FixStateError : If fix is not currently FAILED or STALE.
        """
        fix_req = _FIX_REQUEST_STORE.get(fix_request_id)
        if not fix_req and self._repository:
            fix_req = await self._repository.get_fix_request(fix_request_id)

        if not fix_req:
            raise FixNotFoundError(f"FixRequest with ID '{fix_request_id}' not found.")

        if fix_req.status not in (FixStatus.FAILED, FixStatus.STALE):
            raise FixStateError(
                f"Cannot retry FixRequest '{fix_request_id}' in status '{fix_req.status}'. "
                f"Only FAILED or STALE requests can be retried."
            )

        updated_req = fix_req.model_copy(update={"status": FixStatus.REQUESTED})
        _FIX_REQUEST_STORE[fix_request_id] = updated_req
        _FIX_RESULT_STORE.pop(fix_request_id, None)

        if self._repository:
            await self._repository.upsert_fix_request(updated_req)

        logger.info("Retried FixRequest %s: reset to REQUESTED state.", fix_request_id)
        return updated_req
