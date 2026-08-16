"""
performance_agent.py
====================
Specialized PerformanceAgent for Phase 6 Multi-Agent AI Code Review.

Focuses exclusively on algorithmic complexity (O(n²)+), database N+1 queries,
blocking I/O in async contexts, memory inefficiencies, redundant computation,
missing pagination, and unnecessary network calls.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.ai.gemini_service import GeminiService
from app.models.agent_models import AgentCategory
from app.models.review_models import Issue, IssueCategory
from app.prompts.performance_prompt import (
    PERFORMANCE_SYSTEM_PROMPT,
    build_performance_prompt,
)

logger = logging.getLogger(__name__)


class PerformanceAgent(BaseAgent):
    """Specialized reviewer focused exclusively on performance bottlenecks and scalability."""

    def __init__(self, gemini_service: Optional[GeminiService] = None) -> None:
        super().__init__(
            name="performance_agent",
            category=AgentCategory.PERFORMANCE,
            gemini_service=gemini_service,
        )

    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        """Execute PerformanceAgent audit using dedicated performance prompt."""
        user_prompt = build_performance_prompt(
            diff=diff,
            pr_title=pr_title,
            pr_description=pr_description,
            language_hint=language_hint,
        )
        return await self._run_specialized_review(
            user_prompt=user_prompt,
            system_prompt=PERFORMANCE_SYSTEM_PROMPT,
            target_category=IssueCategory.PERFORMANCE,
        )
