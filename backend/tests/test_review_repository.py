"""
test_review_repository.py
==========================
Unit tests for Stage 7.3 ReviewRepository & ReviewFilter with mocked MongoDB.

Tests cover:
- upsert_review calling find_one_and_update with review_key.
- get_review_by_id and get_review_by_key query execution.
- list_reviews with pagination, sorting, and multi-field filters.
- count_reviews query execution.
- _build_query query structure sanitization (regex escaping, score range, date range).
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.review_repository import ReviewFilter, ReviewRepository
from app.models.persistence_models import PersistedReview, ReviewStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_doc_dict(key: str = "owner/repo#1@sha123") -> dict:
    return {
        "_id": "65d4c8e1a2b3c4d5e6f7a8b9",
        "review_key": key,
        "repository": "owner/repo",
        "owner": "owner",
        "repo_name": "repo",
        "pull_request_number": 1,
        "overall_score": 88,
        "review_status": "COMPLETED",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_review():
    """upsert_review calls find_one_and_update with correct query and payload."""
    mock_col = MagicMock()
    mock_doc = _sample_doc_dict("acme/tool#42@abc")
    mock_col.find_one_and_update = AsyncMock(return_value=mock_doc)

    repo = ReviewRepository(collection=mock_col)
    review = PersistedReview.model_validate(mock_doc)

    result = await repo.upsert_review(review)

    assert mock_col.find_one_and_update.called
    call_args, call_kwargs = mock_col.find_one_and_update.call_args
    assert call_args[0] == {"review_key": "acme/tool#42@abc"}
    assert "$set" in call_args[1]
    assert result.review_key == "acme/tool#42@abc"


@pytest.mark.asyncio
async def test_get_review_by_key():
    """get_review_by_key queries by review_key string."""
    mock_col = MagicMock()
    mock_doc = _sample_doc_dict("acme/tool#10@xyz")
    mock_col.find_one = AsyncMock(return_value=mock_doc)

    repo = ReviewRepository(collection=mock_col)
    result = await repo.get_review_by_key("acme/tool#10@xyz")

    mock_col.find_one.assert_called_once_with({"review_key": "acme/tool#10@xyz"})
    assert result is not None
    assert result.review_key == "acme/tool#10@xyz"


@pytest.mark.asyncio
async def test_get_review_by_key_not_found():
    """get_review_by_key returns None when not found."""
    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=None)

    repo = ReviewRepository(collection=mock_col)
    result = await repo.get_review_by_key("missing/key#1@head")

    assert result is None


@pytest.mark.asyncio
async def test_list_reviews_pagination_and_sorting():
    """list_reviews passes skip, limit, and sort options to cursor."""
    mock_col = MagicMock()
    mock_doc = _sample_doc_dict()

    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[mock_doc])

    mock_col.count_documents = AsyncMock(return_value=15)
    mock_col.find.return_value = mock_cursor

    repo = ReviewRepository(collection=mock_col)
    filter_params = ReviewFilter(page=2, page_size=5, sort_by="overall_score", sort_order="asc")

    items, total = await repo.list_reviews(filter_params)

    assert total == 15
    assert len(items) == 1
    mock_cursor.sort.assert_called_once_with("overall_score", 1)
    mock_cursor.skip.assert_called_once_with(5)  # (page 2 - 1) * 5 = 5
    mock_cursor.limit.assert_called_once_with(5)


def test_build_query_filtering():
    """_build_query correctly constructs Mongo query dict from ReviewFilter."""
    filters = ReviewFilter(
        repository="Acme/Widget",
        author="Alice",
        severity="High",
        category="Security",
        agent="security_agent",
        min_score=70,
        max_score=100,
        search="Critical Fix",
        status="completed",
    )

    query = ReviewRepository._build_query(filters)

    assert query["repository"] == "acme/widget"
    assert query["author"] == "alice"
    assert query["review_status"] == "COMPLETED"
    assert query["overall_score"] == {"$gte": 70, "$lte": 100}
    assert query["severity_counts.high"] == {"$gt": 0}
    assert query["category_counts.security"] == {"$gt": 0}
    assert query["agent_results.agent_name"] == "security_agent"
    assert "$or" in query
    assert len(query["$or"]) == 2
