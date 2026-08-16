"""
review_repository.py
====================
MongoDB Repository abstraction for PersistedReview documents (Phase 7).

Provides clean data access methods (CRUD, pagination, filtering, sorting)
without exposing raw MongoDB expressions to callers.

Author : AI Code Review Bot — Phase 7 (Stage 7.3)
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.db.mongodb import get_mongo_manager
from app.models.persistence_models import PersistedReview, ReviewStatus

logger = logging.getLogger(__name__)

REVIEWS_COLLECTION = "reviews"


class ReviewFilter(BaseModel):
    """Filter criteria and pagination options for querying review history."""

    page: int = Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page.")
    repository: Optional[str] = Field(default=None, description="Full repository slug ('owner/repo').")
    owner: Optional[str] = Field(default=None, description="Repository owner.")
    repo_name: Optional[str] = Field(default=None, description="Repository name.")
    author: Optional[str] = Field(default=None, description="PR author username.")
    severity: Optional[str] = Field(default=None, description="Filter reviews with issues of severity.")
    category: Optional[str] = Field(default=None, description="Filter reviews with issues of category.")
    agent: Optional[str] = Field(default=None, description="Filter reviews executed by agent.")
    status: Optional[str] = Field(default=None, description="Filter by ReviewStatus (COMPLETED, PARTIAL, FAILED).")
    min_score: Optional[int] = Field(default=None, ge=0, le=100, description="Minimum quality score.")
    max_score: Optional[int] = Field(default=None, ge=0, le=100, description="Maximum quality score.")
    start_date: Optional[datetime.datetime] = Field(default=None, description="Created at start bound.")
    end_date: Optional[datetime.datetime] = Field(default=None, description="Created at end bound.")
    search: Optional[str] = Field(default=None, description="Text search in PR title or summary.")
    sort_by: str = Field(default="created_at", description="Field to sort by.")
    sort_order: str = Field(default="desc", description="'asc' or 'desc'.")


class ReviewRepository:
    """Repository abstraction for MongoDB ``reviews`` collection."""

    def __init__(self, collection: Any = None) -> None:
        self._col = collection

    @property
    def collection(self) -> Any:
        """Lazy collection accessor."""
        if self._col is not None:
            return self._col
        return get_mongo_manager().get_collection(REVIEWS_COLLECTION)

    async def upsert_review(self, review: PersistedReview) -> PersistedReview:
        """Create or update a review document by its deterministic review_key.

        Args:
            review: Validated ``PersistedReview`` payload.

        Returns:
            The persisted review with ``id`` set.
        """
        doc = review.model_dump(by_alias=True, exclude={"id"})
        doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc)

        result = await self.collection.find_one_and_update(
            {"review_key": review.review_key},
            {"$set": doc, "$setOnInsert": {"created_at": doc["created_at"]}},
            upsert=True,
            return_document=True,
        )

        return self._doc_to_model(result)

    async def get_review_by_id(self, review_id: str) -> Optional[PersistedReview]:
        """Fetch a single review by MongoDB ObjectId string or review_key."""
        try:
            query = {"_id": ObjectId(review_id)}
        except Exception:
            # Fallback if review_id is not a valid ObjectId string
            query = {"_id": review_id}

        result = await self.collection.find_one(query)
        if not result:
            return None
        return self._doc_to_model(result)

    async def get_review_by_key(self, review_key: str) -> Optional[PersistedReview]:
        """Fetch a single review by its deterministic review_key."""
        result = await self.collection.find_one({"review_key": review_key})
        if not result:
            return None
        return self._doc_to_model(result)

    async def list_reviews(
        self, filter_params: Optional[ReviewFilter] = None
    ) -> tuple[list[PersistedReview], int]:
        """List reviews matching filter criteria with pagination and total count.

        Returns:
            Tuple of ``(list[PersistedReview], total_count)``.
        """
        filters = filter_params or ReviewFilter()
        query = self._build_query(filters)
        sort_field, sort_dir = self._build_sort(filters)

        total_count = await self.collection.count_documents(query)

        skip = (filters.page - 1) * filters.page_size
        cursor = (
            self.collection.find(query)
            .sort(sort_field, sort_dir)
            .skip(skip)
            .limit(filters.page_size)
        )

        docs = await cursor.to_list(length=filters.page_size)
        reviews = [self._doc_to_model(d) for d in docs]

        return reviews, total_count

    async def count_reviews(self, filter_params: Optional[ReviewFilter] = None) -> int:
        """Count total reviews matching filter criteria."""
        filters = filter_params or ReviewFilter()
        query = self._build_query(filters)
        return await self.collection.count_documents(query)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _doc_to_model(doc: dict[str, Any]) -> PersistedReview:
        """Convert MongoDB BSON document dict into PersistedReview model."""
        if not doc:
            raise ValueError("Cannot convert empty MongoDB document.")
        data = dict(doc)
        if "_id" in data:
            data["_id"] = str(data["_id"])
        return PersistedReview.model_validate(data)

    @staticmethod
    def _build_query(filters: ReviewFilter) -> dict[str, Any]:
        """Construct sanitized MongoDB filter dictionary from ReviewFilter DTO."""
        query: dict[str, Any] = {}

        if filters.repository:
            query["repository"] = filters.repository.strip().lower()
        if filters.owner:
            query["owner"] = filters.owner.strip().lower()
        if filters.repo_name:
            query["repo_name"] = filters.repo_name.strip().lower()
        if filters.author:
            query["author"] = filters.author.strip().lower()
        if filters.status:
            query["review_status"] = filters.status.strip().upper()

        # Score range
        if filters.min_score is not None or filters.max_score is not None:
            score_q: dict[str, int] = {}
            if filters.min_score is not None:
                score_q["$gte"] = filters.min_score
            if filters.max_score is not None:
                score_q["$lte"] = filters.max_score
            query["overall_score"] = score_q

        # Date range
        if filters.start_date is not None or filters.end_date is not None:
            date_q: dict[str, datetime.datetime] = {}
            if filters.start_date is not None:
                date_q["$gte"] = filters.start_date
            if filters.end_date is not None:
                date_q["$lte"] = filters.end_date
            query["created_at"] = date_q

        # Nested array checks
        if filters.severity:
            sev_key = filters.severity.strip().lower()
            query[f"severity_counts.{sev_key}"] = {"$gt": 0}

        if filters.category:
            cat_key = filters.category.strip().lower()
            query[f"category_counts.{cat_key}"] = {"$gt": 0}

        if filters.agent:
            agent_key = filters.agent.strip().lower()
            query["agent_results.agent_name"] = agent_key

        # Search term in pull_request_title or summary (regex escaped)
        if filters.search and filters.search.strip():
            safe_term = re.escape(filters.search.strip())
            query["$or"] = [
                {"pull_request_title": {"$regex": safe_term, "$options": "i"}},
                {"summary": {"$regex": safe_term, "$options": "i"}},
            ]

        return query

    @staticmethod
    def _build_sort(filters: ReviewFilter) -> tuple[str, int]:
        """Validate and construct MongoDB sort tuple."""
        allowed_fields = {
            "created_at",
            "overall_score",
            "total_issues",
            "review_duration_ms",
            "pull_request_number",
        }
        field = filters.sort_by if filters.sort_by in allowed_fields else "created_at"
        direction = -1 if filters.sort_order.lower() == "desc" else 1
        return field, direction
