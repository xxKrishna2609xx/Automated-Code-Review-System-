"""
security_agent.py
==================
Specialized SecurityAgent for Phase 6 Multi-Agent AI Code Review.

Focuses exclusively on security vulnerabilities, OWASP Top 10 flaws, SQL/Command injection,
hardcoded credentials/secrets, authentication flaws, unsafe execution, and information leaks.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.ai.gemini_service import GeminiService
from app.models.agent_models import AgentCategory
from app.models.review_models import Issue, IssueCategory
from app.prompts.security_prompt import SECURITY_SYSTEM_PROMPT, build_security_prompt

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """Specialized reviewer focused exclusively on security vulnerabilities and secret leaks."""

    def __init__(self, gemini_service: Optional[GeminiService] = None) -> None:
        super().__init__(
            name="security_agent",
            category=AgentCategory.SECURITY,
            gemini_service=gemini_service,
        )

    async def _execute_review(
        self,
        diff: str,
        pr_title: Optional[str],
        pr_description: Optional[str],
        language_hint: Optional[str],
    ) -> tuple[str, list[Issue]]:
        """Execute SecurityAgent audit using dedicated security prompt."""
        user_prompt = build_security_prompt(
            diff=diff,
            pr_title=pr_title,
            pr_description=pr_description,
            language_hint=language_hint,
        )

        summary, issues = await self._gemini.generate_custom_review(
            user_prompt=user_prompt,
            system_instruction=SECURITY_SYSTEM_PROMPT,
        )

        # Force issue category to Security to maintain strict agent responsibility boundary
        sec_issues: list[Issue] = []
        for issue in issues:
            issue.category = IssueCategory.SECURITY
            sec_issues.append(issue)

        return summary, sec_issues
