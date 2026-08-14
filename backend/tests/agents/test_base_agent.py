"""
test_base_agent.py
===================
Unit tests for the Stage 6.1 BaseAgent abstract contract and model validation.
"""

from __future__ import annotations

from typing import Optional

import pytest
from pydantic import ValidationError

from app.agents.base_agent import BaseAgent
from app.ai.gemini_service import EmptyDiffError
from app.models.agent_models import AgentCategory, AgentReview
from app.models.review_models import Issue, IssueCategory, ReviewRequest, Severity


class ConcreteDummyAgent(BaseAgent):
    """Concrete test implementation of BaseAgent for testing contract behavior."""

    def __init__(self, fail_trigger: bool = False) -> None:
        super().__init__(
            name="test_dummy_agent",
            category=AgentCategory.BUG,
            gemini_service=None,
        )
        self.fail_trigger = fail_trigger

    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        if self.fail_trigger:
            raise RuntimeError("Simulated agent execution error")

        issues = [
            Issue(
                title="Test bug detected",
                severity=Severity.HIGH,
                line=10,
                category=IssueCategory.BUG,
                description="Simulated bug issue for testing.",
                suggestion="Fix the simulated bug.",
            )
        ]
        return "Dummy review completed successfully.", issues


@pytest.mark.asyncio
async def test_cannot_instantiate_base_agent_directly():
    """Verify that BaseAgent cannot be instantiated without implementing abstract methods."""
    with pytest.raises(TypeError):
        BaseAgent(name="abstract", category=AgentCategory.BUG)


@pytest.mark.asyncio
async def test_base_agent_successful_review():
    """Verify clean review execution for a valid diff."""
    agent = ConcreteDummyAgent(fail_trigger=False)
    request = ReviewRequest(
        diff="--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')",
        pr_title="Test PR Title",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "test_dummy_agent"
    assert review.category == AgentCategory.BUG
    assert review.success is True
    assert review.error is None
    assert review.summary == "Dummy review completed successfully."
    assert len(review.issues) == 1
    assert review.issues[0].title == "Test bug detected"
    assert review.execution_time_ms >= 0.0


@pytest.mark.asyncio
async def test_base_agent_empty_diff_validation():
    """Verify that empty diffs are rejected during pre-processing."""
    agent = ConcreteDummyAgent(fail_trigger=False)

    # 1. Pydantic validation rejects whitespace diffs
    with pytest.raises(ValidationError):
        ReviewRequest(diff="   \n   ")

    # 2. BaseAgent._pre_process raises EmptyDiffError if diff normalizes to empty
    with pytest.raises(EmptyDiffError):
        agent._pre_process(ReviewRequest.model_construct(diff=""))


@pytest.mark.asyncio
async def test_base_agent_error_isolation():
    """Verify that agent execution failures return success=False without crashing."""
    agent = ConcreteDummyAgent(fail_trigger=True)
    request = ReviewRequest(
        diff="--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-x = 1\n+x = 2",
    )

    review: AgentReview = await agent.review(request)

    assert review.agent_name == "test_dummy_agent"
    assert review.category == AgentCategory.BUG
    assert review.success is False
    assert review.error == "Simulated agent execution error"
    assert review.issues == []
    assert "failed" in review.summary.lower()
    assert review.execution_time_ms >= 0.0
