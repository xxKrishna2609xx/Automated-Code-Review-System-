"""
agent_models.py
===============
Pydantic data models for the Multi-Agent Code Review architecture (Phase 6).

Defines structured inputs/outputs for all specialized agents, ensuring strict
type-safety and interoperability with existing Phase 5 models.

Author : AI Code Review Bot — Phase 6
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.review_models import Issue, Severity


class AgentCategory(str, Enum):
    """Categories of specialized code review agents."""

    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


class AgentReview(BaseModel):
    """Structured output returned by an individual specialized agent.

    Attributes:
        agent_name        : Unique identifier for the agent (e.g., 'bug_agent').
        category          : Agent specialization category.
        issues            : List of detected issues matching the agent's focus.
        summary           : Concise category summary produced by the agent.
        execution_time_ms : Wall-clock execution time in milliseconds.
        success           : True if execution completed cleanly; False on error.
        error             : Error message string if success=False (or None).
    """

    agent_name: str = Field(
        ...,
        description="Unique identifier of the executing agent.",
    )
    category: AgentCategory = Field(
        ...,
        description="Category taxonomy for this agent.",
    )
    issues: list[Issue] = Field(
        default_factory=list,
        description="List of findings raised by this agent.",
    )
    summary: str = Field(
        default="",
        description="Concise summary for this category.",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution duration in milliseconds.",
    )
    success: bool = Field(
        default=True,
        description="Whether the agent completed its review successfully.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error description if execution failed.",
    )

    model_config = {"use_enum_values": True}


class FinalReview(BaseModel):
    """Aggregated, deduplicated, and ranked output of the multi-agent pipeline.

    Produced by ``ReviewAggregator`` and consumed by ``ScoreEngine`` and the
    Phase 5 adapter. The ``overall_score`` field is populated by the ScoreEngine
    in a later stage and defaults to -1 (unscored) here.

    Attributes:
        overall_score     : 0–100 quality score (populated by ScoreEngine; -1 = unscored).
        summary           : Combined narrative assembled from all successful agent summaries.
        issues            : Deduplicated, severity-ranked list of all findings.
        total_issues      : Auto-computed count of issues.
        issues_by_category: Breakdown of issue counts per category key.
        issues_by_severity: Breakdown of issue counts per severity level.
        agent_results     : Original per-agent reviews preserved for traceability.
        successful_agents : Names of agents that completed successfully.
        failed_agents     : Names of agents that failed.
        execution_time_ms : Total pipeline wall-clock duration in milliseconds.
    """

    overall_score: int = Field(
        default=-1,
        ge=-1,
        le=100,
        description="0–100 quality score. -1 means not yet scored.",
    )
    summary: str = Field(
        default="",
        description="Combined narrative from all successful agent summaries.",
    )
    issues: list[Issue] = Field(
        default_factory=list,
        description="Deduplicated, severity-ranked findings from all agents.",
    )
    total_issues: int = Field(
        default=0,
        ge=0,
        description="Total deduplicated issue count (auto-computed).",
    )
    issues_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Count of issues per category key (e.g. {'bug': 2, 'security': 1}).",
    )
    issues_by_severity: dict[str, int] = Field(
        default_factory=dict,
        description="Count of issues per severity level (e.g. {'critical': 0, 'high': 1}).",
    )
    agent_results: list[AgentReview] = Field(
        default_factory=list,
        description="Original per-agent AgentReview objects for full traceability.",
    )
    successful_agents: list[str] = Field(
        default_factory=list,
        description="Names of agents that completed successfully.",
    )
    failed_agents: list[str] = Field(
        default_factory=list,
        description="Names of agents that encountered errors.",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total orchestration + aggregation wall-clock time in ms.",
    )

    model_config = {"use_enum_values": True}
