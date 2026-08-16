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
        return await self._run_specialized_review(
            user_prompt=user_prompt,
            system_prompt=DOCUMENTATION_SYSTEM_PROMPT,
            target_category=IssueCategory.BEST_PRACTICE,
        )
