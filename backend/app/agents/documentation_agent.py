"""
documentation_agent.py
======================
Specialized DocumentationAgent for Phase 6 Multi-Agent AI Code Review.

Focuses exclusively on missing docstrings for public APIs, incomplete Args/Returns/Raises
sections, outdated or contradictory inline comments, missing type annotations, and
undocumented FastAPI route handlers or exported classes.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.ai.gemini_service import GeminiService
from app.models.agent_models import AgentCategory
from app.models.review_models import Issue, IssueCategory
from app.prompts.documentation_prompt import (
    DOCUMENTATION_SYSTEM_PROMPT,
    build_documentation_prompt,
)

logger = logging.getLogger(__name__)


class DocumentationAgent(BaseAgent):
    """Specialized reviewer focused exclusively on documentation quality and completeness."""

    def __init__(self, gemini_service: Optional[GeminiService] = None) -> None:
        super().__init__(
            name="documentation_agent",
            category=AgentCategory.DOCUMENTATION,
            gemini_service=gemini_service,
        )

    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        """Execute DocumentationAgent audit using dedicated documentation prompt."""
        user_prompt = build_documentation_prompt(
            diff=diff,
            pr_title=pr_title,
            pr_description=pr_description,
            language_hint=language_hint,
        )

        summary, issues = await self._gemini.generate_custom_review(
            user_prompt=user_prompt,
            system_instruction=DOCUMENTATION_SYSTEM_PROMPT,
        )

        # Force issue category to BEST_PRACTICE (documentation issues fall under best practices)
        doc_issues: list[Issue] = []
        for issue in issues:
            issue.category = IssueCategory.BEST_PRACTICE
            doc_issues.append(issue)

        return summary, doc_issues
