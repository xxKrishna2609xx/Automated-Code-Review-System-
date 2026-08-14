"""
testing_agent.py
================
Specialized TestingAgent for Phase 6 Multi-Agent AI Code Review.

Focuses exclusively on missing test coverage for new functions/methods/endpoints,
untested edge cases (empty input, None, boundary values), missing assertions,
uncovered branches or exception handlers, and missing integration tests.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.ai.gemini_service import GeminiService
from app.models.agent_models import AgentCategory
from app.models.review_models import Issue, IssueCategory
from app.prompts.testing_prompt import TESTING_SYSTEM_PROMPT, build_testing_prompt

logger = logging.getLogger(__name__)


class TestingAgent(BaseAgent):
    """Specialized reviewer focused exclusively on test coverage gaps and missing assertions."""

    def __init__(self, gemini_service: Optional[GeminiService] = None) -> None:
        super().__init__(
            name="testing_agent",
            category=AgentCategory.TESTING,
            gemini_service=gemini_service,
        )

    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        """Execute TestingAgent audit using dedicated testing prompt."""
        user_prompt = build_testing_prompt(
            diff=diff,
            pr_title=pr_title,
            pr_description=pr_description,
            language_hint=language_hint,
        )

        summary, issues = await self._gemini.generate_custom_review(
            user_prompt=user_prompt,
            system_instruction=TESTING_SYSTEM_PROMPT,
        )

        # Force issue category to BEST_PRACTICE (testing gaps fall under best practices)
        test_issues: list[Issue] = []
        for issue in issues:
            issue.category = IssueCategory.BEST_PRACTICE
            test_issues.append(issue)

        return summary, test_issues
