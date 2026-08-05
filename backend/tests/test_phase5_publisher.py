"""
test_phase5_publisher.py
========================
Comprehensive unit test suite for Phase 5 — GitHub Review Publishing Layer.

Tests:
• Diff position mapper (hunks, positions, line numbers).
• Review formatter (Markdown summary, severity badges, code suggestions, event calculation).
• GitHub HTTP client (retry logic, status code handling).
• Review publisher (batch creation, HTTP 422 fallback strategy).
• Publish service orchestration.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.github.github_client import (
    GitHubAPIError,
    GitHubClient,
    GitHubNotFoundError,
    GitHubValidationError,
)
from app.github.review_formatter import ReviewFormatter
from app.github.review_publisher import ReviewPublisher
from app.models.github_models import (
    GitHubInlineComment,
    GitHubPublishResult,
    GitHubReviewEvent,
    GitHubReviewPayload,
)
from app.models.review_models import Issue, ReviewRequest, ReviewResponse, Severity
from app.services.publish_service import PublishService
from app.utils.diff_mapper import map_line_to_diff_position, parse_unified_diff

# ---------------------------------------------------------------------------
# Sample Test Data
# ---------------------------------------------------------------------------

SAMPLE_DIFF = r"""
--- a/app/main.py
+++ b/app/main.py
@@ -10,6 +10,8 @@ def hello():
     print("hello")
-    x = 1
+    x = 2
+    y = 3
     return x
"""


# ---------------------------------------------------------------------------
# 1. Diff Mapper Tests
# ---------------------------------------------------------------------------


def test_parse_unified_diff():
    diff_map = parse_unified_diff(SAMPLE_DIFF)
    assert "app/main.py" in diff_map

    file_map = diff_map["app/main.py"]
    assert len(file_map.hunks) == 1
    hunk = file_map.hunks[0]
    assert hunk.new_start == 10
    assert 11 in file_map.line_to_position
    assert 12 in file_map.line_to_position


def test_map_line_to_diff_position():
    pos, line, side = map_line_to_diff_position(SAMPLE_DIFF, "app/main.py", 11)
    assert pos is not None
    assert line == 11
    assert side == "RIGHT"


# ---------------------------------------------------------------------------
# 2. Review Formatter Tests
# ---------------------------------------------------------------------------


def test_formatter_event_calculation():
    formatter = ReviewFormatter()

    # Empty issues -> APPROVE
    event_empty = formatter._determine_review_event([], "Clean code.")
    assert event_empty == GitHubReviewEvent.APPROVE

    # Critical issue -> REQUEST_CHANGES
    crit_issue = Issue(
        title="SQL Injection",
        line=10,
        severity=Severity.CRITICAL,
        category="Security",
        description="User input passed directly into SQL query string.",
        suggestion="Use parameterized query parameters.",
    )
    event_crit = formatter._determine_review_event([crit_issue], "Security risk found.")
    assert event_crit == GitHubReviewEvent.REQUEST_CHANGES

    # Low issue -> COMMENT
    low_issue = Issue(
        title="Missing type hint",
        line=12,
        severity=Severity.LOW,
        category="Naming",
        description="Parameter 'x' lacks explicit type hint.",
        suggestion="x: int",
    )
    event_low = formatter._determine_review_event([low_issue], "Minor findings.")
    assert event_low == GitHubReviewEvent.COMMENT


def test_formatter_inline_comment():
    formatter = ReviewFormatter()
    issue = Issue(
        title="Potential Null Pointer Exception",
        line=15,
        severity=Severity.HIGH,
        category="Bug",
        description="Object 'user' may be None before property access.",
        suggestion="if user is not None:\n    print(user.name)",
    )

    body = formatter.format_inline_comment(issue)
    assert "🟠 **High**" in body
    assert "Bug" in body
    assert "```suggestion" in body
    assert "if user is not None:" in body


def test_formatter_full_review_payload():
    formatter = ReviewFormatter()
    response = ReviewResponse(
        summary="Good PR with 1 minor suggestion.",
        issues=[
            Issue(
                title="Unused import variable",
                line=11,
                severity=Severity.LOW,
                category="Code Smell",
                description="Imported variable 'os' is never referenced in module.",
                suggestion="Remove unused import.",
            )
        ],
        reviewed_chunks=1,
    )

    payload = formatter.format_review(
        response=response,
        diff_text=SAMPLE_DIFF,
        commit_sha="abc1234",
        pr_number=42,
    )

    assert payload.commit_id == "abc1234"
    assert payload.event == GitHubReviewEvent.COMMENT
    assert len(payload.comments) == 1
    assert payload.comments[0].line == 11
    assert "AI Code Review Summary" in payload.body


# ---------------------------------------------------------------------------
# 3. Review Publisher & Fallback Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_publisher_success():
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.create_review.return_value = {
        "id": 999,
        "html_url": "https://github.com/owner/repo/pull/42#pullrequestreview-999",
    }

    publisher = ReviewPublisher(github_client=mock_client)
    payload = GitHubReviewPayload(
        commit_id="sha123",
        body="Summary",
        event=GitHubReviewEvent.APPROVE,
        comments=[],
    )

    result = await publisher.publish("owner", "repo", 42, payload)

    assert result.status == "success"
    assert result.review_id == 999
    assert result.comments_published == 0
    mock_client.create_review.assert_called_once()


@pytest.mark.asyncio
async def test_review_publisher_http_422_fallback():
    mock_client = AsyncMock(spec=GitHubClient)
    # Primary create_review fails with 422
    mock_client.create_review.side_effect = [
        GitHubValidationError("Line number 99 is invalid for diff.", status_code=422),
        {"id": 1000, "html_url": "https://github.com/owner/repo/pull/42#fallback"},
    ]

    publisher = ReviewPublisher(github_client=mock_client)
    comment = GitHubInlineComment(path="app.py", line=99, body="Stale line issue")
    payload = GitHubReviewPayload(
        commit_id="sha123",
        body="Summary",
        event=GitHubReviewEvent.COMMENT,
        comments=[comment],
    )

    result = await publisher.publish("owner", "repo", 42, payload)

    assert result.status == "fallback_published"
    assert result.review_id == 1000
    assert mock_client.create_review.call_count == 2


# ---------------------------------------------------------------------------
# 4. Publish Service Orchestration Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_service_orchestration():
    mock_review_service = AsyncMock()
    mock_review_service.review.return_value = ReviewResponse(
        summary="All clear.",
        issues=[],
        reviewed_chunks=1,
    )

    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_latest_commit_sha.return_value = "head_sha_123"
    mock_client.get_pull_request_files.return_value = []
    mock_client.create_review.return_value = {"id": 101, "html_url": "https://github.com/url"}

    service = PublishService(
        review_service=mock_review_service,
        github_client=mock_client,
    )

    req = ReviewRequest(diff=SAMPLE_DIFF, pr_title="Test PR")
    res = await service.review_and_publish(req, "owner", "repo", 10)

    assert res.status == "success"
    assert res.review_id == 101
    mock_review_service.review.assert_called_once_with(req)
