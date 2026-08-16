"""
test_advanced_search_filters.py
================================
Unit tests for Stage 7.10 Search & Advanced Filter API query sanitization and execution.

Tests cover:
- Regex escaping in search term (prevents ReDoS/Mongo injection).
- Search query matching pull_request_title, summary, or review_key.
- Range query construction (min_score, max_score, start_date, end_date).
- Sorting parameter validation (created_at, overall_score, total_issues).
- Multi-field filter combination.
"""

from __future__ import annotations

import datetime

from app.db.review_repository import ReviewFilter, ReviewRepository


def test_build_query_search_sanitization():
    """search parameter is re.escaped to prevent regex injection."""
    filters = ReviewFilter(search="[test]* (PR) + $100?")
    query = ReviewRepository._build_query(filters)

    assert "$or" in query
    or_clauses = query["$or"]
    assert len(or_clauses) == 3

    # Ensure special regex chars are escaped in the pattern
    regex_pattern = or_clauses[0]["pull_request_title"]["$regex"]
    assert r"\[test\]\*" in regex_pattern
    assert r"\$100\?" in regex_pattern


def test_build_query_all_filters_combined():
    """All advanced filter fields are mapped correctly into Mongo query dictionary."""
    start_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 12, 31, tzinfo=datetime.timezone.utc)

    filters = ReviewFilter(
        repository="owner/repo",
        author="alice",
        severity="High",
        category="Security",
        agent="security_agent",
        status="COMPLETED",
        min_score=50,
        max_score=95,
        start_date=start_dt,
        end_date=end_dt,
        search="auth_fix",
        sort_by="overall_score",
        sort_order="asc",
    )

    query = ReviewRepository._build_query(filters)

    assert query["repository"] == "owner/repo"
    assert query["author"] == "alice"
    assert query["review_status"] == "COMPLETED"
    assert query["overall_score"] == {"$gte": 50, "$lte": 95}
    assert query["created_at"] == {"$gte": start_dt, "$lte": end_dt}
    assert query["severity_counts.high"] == {"$gt": 0}
    assert query["category_counts.security"] == {"$gt": 0}
    assert query["agent_results.agent_name"] == "security_agent"


def test_build_sort_valid_fields():
    """_build_sort validates allowed fields and directions."""
    f1 = ReviewFilter(sort_by="overall_score", sort_order="asc")
    field1, dir1 = ReviewRepository._build_sort(f1)
    assert field1 == "overall_score"
    assert dir1 == 1

    f2 = ReviewFilter(sort_by="total_issues", sort_order="desc")
    field2, dir2 = ReviewRepository._build_sort(f2)
    assert field2 == "total_issues"
    assert dir2 == -1

    # Disallowed field falls back to created_at
    f3 = ReviewFilter(sort_by="invalid_field", sort_order="desc")
    field3, dir3 = ReviewRepository._build_sort(f3)
    assert field3 == "created_at"
    assert dir3 == -1
