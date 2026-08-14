"""
test_performance_agent.py
=========================
Unit tests for Stage 6.4 PerformanceAgent with mocked Gemini API responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.performance_agent import PerformanceAgent
from app.ai.gemini_service import GeminiParseError, GeminiService
from app.models.agent_models import AgentCategory, AgentReview
from app.models.review_models import Issue, IssueCategory, ReviewRequest, Severity


@pytest.fixture
def mock_gemini_service() -> MagicMock:
    """Fixture returning a mocked GeminiService."""
    service = MagicMock(spec=GeminiService)
    service.generate_custom_review = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_performance_agent_detects_n_squared(mock_gemini_service: MagicMock):
    """Test PerformanceAgent detects O(n²) nested loop."""
    mock_gemini_service.generate_custom_review.return_value = (
        "O(n²) nested loop detected — will degrade with large inputs.",
        [
            Issue(
                title="O(n²) Nested Loop",
                severity=Severity.HIGH,
                line=12,
                category=IssueCategory.PERFORMANCE,
                description="Nested for-loop iterates over items for every element, resulting in O(n²) complexity.",
                suggestion="Use a set or dict for O(1) lookups: seen = set(items); if x in seen:...",
            )
        ],
    )

    agent = PerformanceAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/search.py\n+++ b/search.py\n@@ -10,4 +10,4 @@\n+for x in items:\n+    for y in items:\n+        if x == y:\n+            result.append(x)\n",
        pr_title="Add duplicate search",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "performance_agent"
    assert review.category == AgentCategory.PERFORMANCE
    assert review.success is True
    assert len(review.issues) == 1
    assert "O(n²)" in review.issues[0].title
    assert review.issues[0].severity == Severity.HIGH
    assert review.issues[0].category == IssueCategory.PERFORMANCE


@pytest.mark.asyncio
async def test_performance_agent_detects_n_plus_1_query(mock_gemini_service: MagicMock):
    """Test PerformanceAgent detects database N+1 query pattern."""
    mock_gemini_service.generate_custom_review.return_value = (
        "N+1 database query pattern detected inside loop.",
        [
            Issue(
                title="N+1 Database Query in Loop",
                severity=Severity.HIGH,
                line=8,
                category=IssueCategory.PERFORMANCE,
                description="User.objects.get() called per item in loop — fires N separate DB queries.",
                suggestion="Use User.objects.filter(id__in=ids) to batch fetch all users in one query.",
            )
        ],
    )

    agent = PerformanceAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/views.py\n+++ b/views.py\n@@ -5,3 +5,3 @@\n+for order in orders:\n+    user = User.objects.get(id=order.user_id)\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "N+1" in review.issues[0].title
    assert review.issues[0].category == IssueCategory.PERFORMANCE


@pytest.mark.asyncio
async def test_performance_agent_detects_blocking_io(mock_gemini_service: MagicMock):
    """Test PerformanceAgent detects blocking I/O in async context."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Blocking I/O call inside async function blocks the event loop.",
        [
            Issue(
                title="Blocking requests.get() Inside Async Function",
                severity=Severity.HIGH,
                line=14,
                category=IssueCategory.PERFORMANCE,
                description="Synchronous requests.get() called inside async def — blocks event loop thread.",
                suggestion="Use httpx.AsyncClient or aiohttp: async with httpx.AsyncClient() as client: await client.get(url)",
            )
        ],
    )

    agent = PerformanceAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/api.py\n+++ b/api.py\n@@ -12,2 +12,2 @@\n+async def fetch_data(url):\n+    response = requests.get(url)\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "Blocking" in review.issues[0].title


@pytest.mark.asyncio
async def test_performance_agent_clean_code(mock_gemini_service: MagicMock):
    """Test PerformanceAgent returns clean review for optimized code."""
    mock_gemini_service.generate_custom_review.return_value = (
        "No performance issues detected. Code uses efficient patterns.",
        [],
    )

    agent = PerformanceAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/utils.py\n+++ b/utils.py\n@@ -1,2 +1,2 @@\n+result = {item.id: item for item in items}\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "performance_agent"
    assert review.category == AgentCategory.PERFORMANCE
    assert review.success is True
    assert review.issues == []
    assert "No performance issues" in review.summary


@pytest.mark.asyncio
async def test_performance_agent_error_isolation(mock_gemini_service: MagicMock):
    """Test PerformanceAgent handles Gemini error gracefully without crashing."""
    mock_gemini_service.generate_custom_review.side_effect = GeminiParseError(
        "Failed to parse performance audit JSON."
    )

    agent = PerformanceAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n+x = 1\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "performance_agent"
    assert review.category == AgentCategory.PERFORMANCE
    assert review.success is False
    assert "Failed to parse performance audit JSON" in review.error
    assert review.issues == []
