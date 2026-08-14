"""
test_documentation_agent.py
============================
Unit tests for Stage 6.5 DocumentationAgent with mocked Gemini API responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.documentation_agent import DocumentationAgent
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
async def test_documentation_agent_detects_missing_docstring(mock_gemini_service: MagicMock):
    """Test DocumentationAgent detects a public function missing its docstring."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Public function added without any docstring.",
        [
            Issue(
                title="Missing Docstring on Public Function",
                severity=Severity.MEDIUM,
                line=5,
                category=IssueCategory.BEST_PRACTICE,
                description="Function `calculate_total` is public but has no docstring explaining its purpose.",
                suggestion='Add docstring: """Calculate the total price including tax.\n\nArgs:\n    items: list of Item.\n\nReturns:\n    Total float value.\n"""',
            )
        ],
    )

    agent = DocumentationAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/pricing.py\n+++ b/pricing.py\n@@ -3,4 +3,4 @@\n+def calculate_total(items):\n+    return sum(i.price for i in items)\n",
        pr_title="Add pricing function",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "documentation_agent"
    assert review.category == AgentCategory.DOCUMENTATION
    assert review.success is True
    assert len(review.issues) == 1
    assert "Missing Docstring" in review.issues[0].title
    assert review.issues[0].severity == Severity.MEDIUM
    assert review.issues[0].category == IssueCategory.BEST_PRACTICE


@pytest.mark.asyncio
async def test_documentation_agent_detects_missing_type_hints(mock_gemini_service: MagicMock):
    """Test DocumentationAgent flags missing type annotations on public API."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Public function missing type annotations.",
        [
            Issue(
                title="Missing Type Annotations on Public Function",
                severity=Severity.LOW,
                line=3,
                category=IssueCategory.BEST_PRACTICE,
                description="Function `process_items` has no parameter or return type hints.",
                suggestion="Add annotations: def process_items(items: list[str]) -> dict[str, int]:",
            )
        ],
    )

    agent = DocumentationAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/utils.py\n+++ b/utils.py\n@@ -1,3 +1,3 @@\n+def process_items(items):\n+    return {i: len(i) for i in items}\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "Type Annotations" in review.issues[0].title
    assert review.issues[0].category == IssueCategory.BEST_PRACTICE


@pytest.mark.asyncio
async def test_documentation_agent_detects_outdated_comment(mock_gemini_service: MagicMock):
    """Test DocumentationAgent flags a comment that contradicts the code."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Outdated inline comment found — contradicts the actual implementation.",
        [
            Issue(
                title="Outdated Comment Contradicts Implementation",
                severity=Severity.LOW,
                line=7,
                category=IssueCategory.BEST_PRACTICE,
                description="Comment says 'returns None' but function now returns a dict.",
                suggestion="Update comment to reflect the actual return type: # Returns: dict of {id: value}",
            )
        ],
    )

    agent = DocumentationAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/helpers.py\n+++ b/helpers.py\n@@ -5,3 +5,3 @@\n+# Returns: None\n+def get_mapping(items):\n+    return {i.id: i.value for i in items}\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "Outdated" in review.issues[0].title
    assert review.issues[0].category == IssueCategory.BEST_PRACTICE


@pytest.mark.asyncio
async def test_documentation_agent_well_documented_code(mock_gemini_service: MagicMock):
    """Test DocumentationAgent returns clean result for well-documented code."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Documentation is thorough. All public APIs have docstrings and type hints.",
        [],
    )

    agent = DocumentationAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff=(
            "--- a/service.py\n+++ b/service.py\n@@ -1,5 +1,5 @@\n"
            '+def fetch_user(user_id: int) -> dict:\n'
            '+    """Fetch user by ID.\n'
            '+\n'
            '+    Args:\n'
            '+        user_id: The unique user identifier.\n'
            '+\n'
            '+    Returns:\n'
            '+        User data dictionary.\n'
            '+    """\n'
            "+    return db.get(user_id)\n"
        ),
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "documentation_agent"
    assert review.category == AgentCategory.DOCUMENTATION
    assert review.success is True
    assert review.issues == []
    assert "thorough" in review.summary


@pytest.mark.asyncio
async def test_documentation_agent_error_isolation(mock_gemini_service: MagicMock):
    """Test DocumentationAgent handles Gemini error gracefully without crashing."""
    mock_gemini_service.generate_custom_review.side_effect = GeminiParseError(
        "Failed to parse documentation audit JSON."
    )

    agent = DocumentationAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n+x = 1\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "documentation_agent"
    assert review.category == AgentCategory.DOCUMENTATION
    assert review.success is False
    assert "Failed to parse documentation audit JSON" in review.error
    assert review.issues == []
