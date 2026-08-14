"""
test_security_agent.py
======================
Unit tests for Stage 6.3 SecurityAgent with mocked Gemini API responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.security_agent import SecurityAgent
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
async def test_security_agent_detects_sql_injection(mock_gemini_service: MagicMock):
    """Test SecurityAgent detects SQL Injection vulnerability."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Critical SQL Injection vulnerability detected.",
        [
            Issue(
                title="SQL Injection in Raw Query",
                severity=Severity.CRITICAL,
                line=15,
                category=IssueCategory.SECURITY,
                description="Unsanitized user input string formatted directly into SQL query.",
                suggestion="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
            )
        ],
    )

    agent = SecurityAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/db.py\n+++ b/db.py\n@@ -10,3 +10,3 @@\n-query = 'SELECT * FROM users WHERE id = %s'\n+query = f'SELECT * FROM users WHERE id = {user_id}'\n",
        pr_title="Update query",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "security_agent"
    assert review.category == AgentCategory.SECURITY
    assert review.success is True
    assert len(review.issues) == 1
    assert review.issues[0].title == "SQL Injection in Raw Query"
    assert review.issues[0].severity == Severity.CRITICAL
    assert review.issues[0].category == IssueCategory.SECURITY


@pytest.mark.asyncio
async def test_security_agent_detects_hardcoded_secret(mock_gemini_service: MagicMock):
    """Test SecurityAgent flags hardcoded API keys and secrets."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Hardcoded API secret found in source code.",
        [
            Issue(
                title="Hardcoded API Secret Key",
                severity=Severity.CRITICAL,
                line=5,
                category=IssueCategory.SECURITY,
                description="AWS secret key hardcoded directly in file.",
                suggestion="Store secret in environment variable: os.environ.get('AWS_SECRET_KEY')",
            )
        ],
    )

    agent = SecurityAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/config.py\n+++ b/config.py\n@@ -1,2 +1,2 @@\n+AWS_SECRET_KEY = 'AKIAIOSFODNN7EXAMPLE'\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "Hardcoded" in review.issues[0].title
    assert review.issues[0].severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_security_agent_detects_unsafe_eval(mock_gemini_service: MagicMock):
    """Test SecurityAgent flags unsafe eval/exec usage."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Unsafe eval execution vulnerability.",
        [
            Issue(
                title="Unsafe Dynamic Code Execution with eval()",
                severity=Severity.HIGH,
                line=8,
                category=IssueCategory.SECURITY,
                description="eval() executed on untrusted user input string.",
                suggestion="Use ast.literal_eval() or safe JSON parser instead.",
            )
        ],
    )

    agent = SecurityAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/parser.py\n+++ b/parser.py\n@@ -5,2 +5,2 @@\n+result = eval(user_input)\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.success is True
    assert len(review.issues) == 1
    assert "eval()" in review.issues[0].title


@pytest.mark.asyncio
async def test_security_agent_safe_code(mock_gemini_service: MagicMock):
    """Test SecurityAgent returns clean review for safe code."""
    mock_gemini_service.generate_custom_review.return_value = (
        "Security audit clean. No vulnerabilities detected.",
        [],
    )

    agent = SecurityAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/auth.py\n+++ b/auth.py\n@@ -1,2 +1,2 @@\n+token = os.environ.get('AUTH_TOKEN')\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "security_agent"
    assert review.category == AgentCategory.SECURITY
    assert review.success is True
    assert review.issues == []


@pytest.mark.asyncio
async def test_security_agent_error_isolation(mock_gemini_service: MagicMock):
    """Test SecurityAgent handles Gemini API error gracefully without crashing."""
    mock_gemini_service.generate_custom_review.side_effect = GeminiParseError(
        "Failed to parse security audit JSON."
    )

    agent = SecurityAgent(gemini_service=mock_gemini_service)
    request = ReviewRequest(
        diff="--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n+x = 1\n",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "security_agent"
    assert review.category == AgentCategory.SECURITY
    assert review.success is False
    assert "Failed to parse security audit JSON" in review.error
    assert review.issues == []
