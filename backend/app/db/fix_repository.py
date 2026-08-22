"""
fix_repository.py  (app.db)
============================
Stage 8.17 — Fix History Persistence Repository.

MongoDB Data Access Layer for Fix Requests, Fix Patches, and Fix Results.

Collections:
    - ``fix_requests`` : Stores FixRequest records and status transitions.
    - ``fix_patches``  : Stores generated unified diff FixPatch models.
    - ``fix_results``  : Stores post-verification FixResult audit records.

Author : AI Code Review Bot — Phase 8 (Stage 8.17)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.db.mongodb import get_mongo_manager
from app.fixes.models import FixPatch, FixRequest, FixResult, FixStatus

logger = logging.getLogger(__name__)

FIX_REQUESTS_COLLECTION = "fix_requests"
FIX_PATCHES_COLLECTION = "fix_patches"
FIX_RESULTS_COLLECTION = "fix_results"


class FixRepository:
    """Repository pattern abstraction for MongoDB fix collections."""

    def __init__(
        self,
        requests_collection: Any = None,
        patches_collection: Any = None,
        results_collection: Any = None,
    ) -> None:
        self._req_col = requests_collection
        self._patch_col = patches_collection
        self._res_col = results_collection

    def _get_collection(self, collection_name: str, explicit_col: Any) -> Any:
        if explicit_col is not None:
            return explicit_col
        manager = get_mongo_manager()
        if manager.is_connected:
            return manager.db[collection_name]
        return None

    @property
    def requests_collection(self) -> Any:
        return self._get_collection(FIX_REQUESTS_COLLECTION, self._req_col)

    @property
    def patches_collection(self) -> Any:
        return self._get_collection(FIX_PATCHES_COLLECTION, self._patch_col)

    @property
    def results_collection(self) -> Any:
        return self._get_collection(FIX_RESULTS_COLLECTION, self._res_col)

    # ------------------------------------------------------------------
    # FixRequest Operations
    # ------------------------------------------------------------------

    async def upsert_fix_request(self, fix_request: FixRequest) -> FixRequest:
        """Upsert a FixRequest document by ID.

        Args:
            fix_request : Validated FixRequest instance.

        Returns:
            The saved FixRequest instance.
        """
        col = self.requests_collection
        doc = fix_request.model_dump(by_alias=True)

        if col is not None:
            await col.replace_one({"id": fix_request.id}, doc, upsert=True)
            logger.info("Upserted FixRequest %s in MongoDB", fix_request.id)

        return fix_request

    async def get_fix_request(self, fix_request_id: str) -> Optional[FixRequest]:
        """Fetch a FixRequest document by ID.

        Args:
            fix_request_id : Unique FixRequest ID.

        Returns:
            FixRequest instance if found, None otherwise.
        """
        col = self.requests_collection
        if col is not None:
            doc = await col.find_one({"id": fix_request_id})
            if doc:
                doc.pop("_id", None)
                return FixRequest(**doc)
        return None

    async def update_fix_request_status(self, fix_request_id: str, status: FixStatus) -> bool:
        """Update the lifecycle status of a FixRequest document.

        Args:
            fix_request_id : Unique FixRequest ID.
            status         : New FixStatus enum value.

        Returns:
            True if document was modified or found, False otherwise.
        """
        col = self.requests_collection
        status_val = status.value if hasattr(status, "value") else str(status)

        if col is not None:
            res = await col.update_one({"id": fix_request_id}, {"$set": {"status": status_val}})
            return res.matched_count > 0

        return False

    # ------------------------------------------------------------------
    # FixPatch Operations
    # ------------------------------------------------------------------

    async def upsert_fix_patch(self, fix_request_id: str, patch: FixPatch) -> FixPatch:
        """Save or replace a FixPatch for a fix_request_id.

        Args:
            fix_request_id : Parent FixRequest ID.
            patch          : Generated FixPatch model.

        Returns:
            Saved FixPatch instance.
        """
        col = self.patches_collection
        doc = patch.model_dump()
        doc["fix_request_id"] = fix_request_id

        if col is not None:
            await col.replace_one({"fix_request_id": fix_request_id}, doc, upsert=True)
            logger.info("Upserted FixPatch for %s in MongoDB", fix_request_id)

        return patch

    async def get_fix_patch(self, fix_request_id: str) -> Optional[FixPatch]:
        """Fetch FixPatch by parent fix_request_id.

        Args:
            fix_request_id : Parent FixRequest ID.

        Returns:
            FixPatch instance if found, None otherwise.
        """
        col = self.patches_collection
        if col is not None:
            doc = await col.find_one({"fix_request_id": fix_request_id})
            if doc:
                doc.pop("_id", None)
                doc.pop("fix_request_id", None)
                return FixPatch(**doc)
        return None

    # ------------------------------------------------------------------
    # FixResult Operations
    # ------------------------------------------------------------------

    async def upsert_fix_result(self, fix_result: FixResult) -> FixResult:
        """Upsert a FixResult audit document by fix_request_id.

        Args:
            fix_result : Validated FixResult instance.

        Returns:
            Saved FixResult instance.
        """
        col = self.results_collection
        doc = fix_result.model_dump()

        if col is not None:
            await col.replace_one({"fix_request_id": fix_result.fix_request_id}, doc, upsert=True)
            logger.info("Upserted FixResult for %s in MongoDB", fix_result.fix_request_id)

        return fix_result

    async def get_fix_result(self, fix_request_id: str) -> Optional[FixResult]:
        """Fetch FixResult by fix_request_id.

        Args:
            fix_request_id : Parent FixRequest ID.

        Returns:
            FixResult instance if found, None otherwise.
        """
        col = self.results_collection
        if col is not None:
            doc = await col.find_one({"fix_request_id": fix_request_id})
            if doc:
                doc.pop("_id", None)
                return FixResult(**doc)
        return None

    # ------------------------------------------------------------------
    # Query Operations
    # ------------------------------------------------------------------

    async def list_fix_requests_by_review(self, review_id: str) -> list[FixRequest]:
        """List all FixRequests created for a specific review_id.

        Args:
            review_id : Parent PersistedReview document ID.

        Returns:
            List of FixRequest objects.
        """
        col = self.requests_collection
        results: list[FixRequest] = []

        if col is not None:
            cursor = col.find({"review_id": review_id})
            async for doc in cursor:
                doc.pop("_id", None)
                results.append(FixRequest(**doc))

        return results

    async def list_fix_requests_by_repo(self, repository: str, limit: int = 50) -> list[FixRequest]:
        """List recent FixRequests for a repository slug.

        Args:
            repository : Repository slug ('owner/repo').
            limit      : Max items to return.

        Returns:
            List of FixRequest objects.
        """
        col = self.requests_collection
        results: list[FixRequest] = []

        if col is not None:
            cursor = col.find({"repository": repository}).limit(limit)
            async for doc in cursor:
                doc.pop("_id", None)
                results.append(FixRequest(**doc))

        return results


def get_fix_repository() -> FixRepository:
    """FastAPI Dependency injector for FixRepository."""
    return FixRepository()
