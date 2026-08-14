"""
bug_agent.py
============
Specialized BugAgent for Phase 6 Multi-Agent AI Code Review.

Focuses exclusively on logical bugs, incorrect boolean checks, null pointer issues,
unhandled runtime risks, state corruption, control flow mistakes, and edge cases.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.ai.gemini_service import GeminiService
from app.models.agent_models import AgentCategory
from app.models.review_models import Issue, IssueCategory
from app.prompts.bug_prompt import BUG_SYSTEM_PROMPT, build_bug_prompt

logger = logging.getLogger(__name__)


class BugAgent(BaseAgent):
    """Specialized reviewer focused exclusively on logical bugs and runtime risks."""

    def __init__(self, gemini_service: Optional[GeminiService] = None) -> None:
        super().__init__(
            name="bug_agent",
            category=AgentCategory.BUG,
            gemini_service=gemini_service,
        )

    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        """Execute BugAgent review using the dedicated bug prompt."""
        user_prompt = build_bug_prompt(
            diff=diff,
            pr_title=pr_title,
            pr_description=pr_description,
            language_hint=language_hint,
        )

        summary, issues = await self._gemini.generate_custom_review(
            user_prompt=user_prompt,
            system_instruction=BUG_SYSTEM_PROMPT,
        )

        # Force issue category to Bug to maintain strict agent responsibility boundary
        bug_issues: list[Issue] = []
        for issue in issues:
            issue.category = IssueCategory.BUG
            bug_issues.append(issue)

        return summary, bug_issues
