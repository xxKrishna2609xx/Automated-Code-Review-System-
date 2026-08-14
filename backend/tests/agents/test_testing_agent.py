"""
test_testing_agent.py
=====================
Unit tests for Stage 6.6 TestingAgent with mocked Gemini API responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.testing_agent import TestingAgent
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
async def test_testing_agent_detects_missing_unit_test(mock_gemini_service: MagicMock):
    """Test TestingAgent detects a new public function added with no test coverage."""
    mock_gemini_service.generate_custom_review.return_value = (
        "New public function added with zero test coverage.",
        [
            Issue(
                title="No Unit Test for New Public Function",
                severity=Severity.HIGH,
                line=4,
                category=IssueCategory.BEST_PRACTICE,
                description="Function `discount_price` was added but has no corresponding test.",
                suggestion=(
                    "Add a test:\n"
                    "def test_discount_price():\n"
                    "    assert discount_price(100, 10) == 90.0\n"
                    "    assert discount_price(0, 50) == 0.0"
                ),
            )
        ],
    )

    agent = TestingAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff=(
            "--- a/pricing.py\n+++ b/pricing.py\n"
            "@@ -1,3 +1,5 @@\n"
            "+def discount_price(price: float, pct: float) -> float:\n"
            "+    return price * (1 - pct / 100)\n"
        ),
        pr_title="Add discount pricing",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "testing_agent"
    assert review.category == AgentCategory.TESTING
    assert review.success is True
    assert len(review.issues) == 1
    assert "No Unit Test" in review.issues[0].title
    assert review.issues[0].severity == Severity.HIGH
    assert review.issues[0].category == IssueCategory.BEST_PRACTICE


@pytest.mark.asyncio
async def test_testing_agent_detects_missing_edge_cases(mock_gemini_service: MagicMock):
    """Test TestingAgent flags untested edge cases (None, empty list, zero)."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Tests exist but edge cases (empty list, None) are not covered.",
        [
            Issue(
                title="Missing Edge Case Tests for Empty and None Input",
                severity=Severity.MEDIUM,
                line=None,
                category=IssueCategory.BEST_PRACTICE,
                description="Only the happy path is tested; no test for empty list or None input.",
                suggestion=(
                    "Add:\n"
                    "def test_process_empty():\n"
                    "    assert process([]) == []\n\n"
                    "def test_process_none():\n"
                    "    with pytest.raises(TypeError):\n"
                    "        process(None)"
                ),
            )
        ],
    )

    agent = TestingAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff=(
            "--- a/test_utils.py\n+++ b/test_utils.py\n"
            "@@ -1,4 +1,7 @@\n"
            "+def test_process_basic():\n"
            "+    result = process([1, 2, 3])\n"
            "+    assert result == [1, 2, 3]\n"
        ),
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "Edge Case" in review.issues[0].title
    assert review.issues[0].category == IssueCategory.BEST_PRACTICE


@pytest.mark.asyncio
async def test_testing_agent_detects_missing_assertion(mock_gemini_service: MagicMock):
    """Test TestingAgent flags a test function with no assertions."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Test added but makes no assertions — always passes regardless of behavior.",
        [
            Issue(
                title="Test Function Has No Assertions",
                severity=Severity.HIGH,
                line=8,
                category=IssueCategory.BEST_PRACTICE,
                description="test_create_user calls the function but asserts nothing — the test is always green.",
                suggestion="Add assertions: assert response.status_code == 201\nassert response.json()['id'] is not None",
            )
        ],
    )

    agent = TestingAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff=(
            "--- a/test_api.py\n+++ b/test_api.py\n"
            "@@ -5,4 +5,4 @@\n"
            "+def test_create_user():\n"
            "+    response = client.post('/users', json={'name': 'Alice'})\n"
        ),
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "No Assertions" in review.issues[0].title


@pytest.mark.asyncio
async def test_testing_agent_adequate_coverage(mock_gemini_service: MagicMock):
    """Test TestingAgent returns clean result when tests are sufficient."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Test coverage is thorough. Happy path and edge cases are both covered.",
        [],
    )

    agent = TestingAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff=(
            "--- a/test_calc.py\n+++ b/test_calc.py\n"
            "@@ -1,5 +1,10 @@\n"
            "+def test_add_positive():\n"
            "+    assert add(2, 3) == 5\n"
            "+def test_add_zero():\n"
            "+    assert add(0, 0) == 0\n"
            "+def test_add_negative():\n"
            "+    assert add(-1, -1) == -2\n"
        ),
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "testing_agent"
    assert review.category == AgentCategory.TESTING
    assert review.success is True
    assert review.issues == []
    assert "thorough" in review.summary


@pytest.mark.asyncio
async def test_testing_agent_error_isolation(mock_gemini_service: MagicMock):
    """Test TestingAgent handles Gemini error gracefully without crashing."""
    mock_gemini_service.generate_custom_review.side_effect = GeminiParseError(
        "Failed to parse testing audit JSON."
    )

    agent = TestingAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n+x = 1\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "testing_agent"
    assert review.category == AgentCategory.TESTING
    assert review.success is False
    assert "Failed to parse testing audit JSON" in review.error
    assert review.issues == []
