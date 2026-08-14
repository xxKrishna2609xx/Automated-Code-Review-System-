"""
test_bug_agent.py
==================
Unit tests for Stage 6.2 BugAgent with mocked Gemini API responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.bug_agent import BugAgent
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
async def test_bug_agent_detects_obvious_bug(mock_gemini_service: MagicMock):
    """Test BugAgent correctly processes and returns detected logic bugs."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Logical bug detected in array indexing.",
        [
            Issue(
                title="Off-by-one Index Out of Bounds",
                severity=Severity.HIGH,
                line=14,
                category=IssueCategory.BUG,
                description="Array index loop condition goes beyond length.",
                suggestion="Use range(len(arr)) instead of range(len(arr) + 1).",
            )
        ],
    )

    agent = BugAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/utils.py\n+++ b/utils.py\n@@ -10,3 +10,3 @@\n-for i in range(len(items)):\n+for i in range(len(items) + 1):\n",
        pr_title="Fix loop range",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "bug_agent"
    assert review.category == AgentCategory.BUG
    assert review.success is True
    assert len(review.issues) == 1
    assert review.issues[0].title == "Off-by-one Index Out of Bounds"
    assert review.issues[0].category == IssueCategory.BUG
    assert review.execution_time_ms >= 0.0


@pytest.mark.asyncio
async def test_bug_agent_no_bugs_found(mock_gemini_service: MagicMock):
    """Test BugAgent returns empty issues when no bugs exist."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Clean logic. No bugs detected.",
        [],
    )

    agent = BugAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-x = 1\n+x = 2\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "bug_agent"
    assert review.category == AgentCategory.BUG
    assert review.success is True
    assert review.issues == []
    assert "Clean logic" in review.summary


@pytest.mark.asyncio
async def test_bug_agent_edge_case_bug(mock_gemini_service: MagicMock):
    """Test BugAgent handles edge-case logic findings."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Zero-division vulnerability on empty input list.",
        [
            Issue(
                title="Zero Division Risk on Empty Input",
                severity=Severity.CRITICAL,
                line=22,
                category=IssueCategory.EDGE_CASE,
                description="Dividing total by len(items) without checking if items is empty.",
                suggestion="Add check: if not items: return 0.0",
            )
        ],
    )

    agent = BugAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/math.py\n+++ b/math.py\n@@ -20,2 +20,2 @@\n+avg = sum(vals) / len(vals)\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert review.issues[0].title == "Zero Division Risk on Empty Input"
    assert review.issues[0].category == IssueCategory.BUG  # Forced category check


@pytest.mark.asyncio
async def test_bug_agent_malformed_ai_response(mock_gemini_service: MagicMock):
    """Test BugAgent error isolation when Gemini raises a parse error."""
    mock_gemini_service.generate_custom_review.side_effect = GeminiParseError(
        "Failed to parse JSON response from Gemini."
    )

    agent = BugAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n-a = 1\n+a = 0\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "bug_agent"
    assert review.category == AgentCategory.BUG
    assert review.success is False
    assert "Failed to parse JSON" in review.error
    assert review.issues == []
