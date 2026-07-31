"""
review_models.py
================
Pydantic data models for the AI Code Review Engine.

Defines the structured output schema that Gemini must return,
validated at parse time using strict Pydantic V2 validators.

Schema:
    Issue          → Individual code issue found during review.
    ReviewResponse → Aggregated result returned by the review engine.
    ReviewRequest  → Input payload for triggering a review.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Valid severity levels for a detected issue.

    Ordering (ascending risk): Low → Medium → High → Critical
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class IssueCategory(str, Enum):
    """Taxonomy of issue categories the AI reviewer can raise."""

    BUG = "Bug"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    CODE_SMELL = "Code Smell"
    READABILITY = "Readability"
    NAMING = "Naming"
    MAINTAINABILITY = "Maintainability"
    ERROR_HANDLING = "Error Handling"
    EDGE_CASE = "Edge Case"
    BEST_PRACTICE = "Best Practice"
    OTHER = "Other"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------


class Issue(BaseModel):
    """A single code-quality issue detected by the AI reviewer.

    Attributes:
        title       : Short, human-readable title (max 120 chars).
        severity    : Risk level — Low | Medium | High | Critical.
        line        : Optional 1-based line number in the diff where the
                      issue occurs.  None when not determinable.
        category    : Taxonomy bucket for the issue type.
        description : Detailed explanation of why this is an issue.
        suggestion  : Concrete, actionable fix recommendation.
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Concise title for the issue.",
    )
    severity: Severity = Field(
        ...,
        description="Risk level: Low | Medium | High | Critical.",
    )
    line: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-based line number in the diff (nullable).",
    )
    category: IssueCategory = Field(
        ...,
        description="Issue category from the IssueCategory taxonomy.",
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Thorough explanation of the problem.",
    )
    suggestion: str = Field(
        ...,
        min_length=5,
        description="Actionable recommendation to resolve the issue.",
    )

    @field_validator("severity", mode="before")
    @classmethod
    def normalise_severity(cls, value: str) -> str:
        """Accept case-insensitive severity values from Gemini output."""
        if isinstance(value, str):
            return value.strip().capitalize()
        return value

    @field_validator("category", mode="before")
    @classmethod
    def normalise_category(cls, value: str) -> str:
        """Accept minor case/spacing variations from Gemini output."""
        if isinstance(value, str):
            return value.strip().title()
        return value

    model_config = {"use_enum_values": True}


class ReviewResponse(BaseModel):
    """Aggregated AI code-review result for a Pull Request diff.

    Attributes:
        summary      : High-level narrative of the diff quality.
        issues       : Ordered list of detected issues (empty → no issues).
        reviewed_chunks : How many diff chunks were independently reviewed
                          (populated by the chunked-review path; defaults 1).
        total_issues : Computed count — automatically derived from issues list.
    """

    summary: str = Field(
        ...,
        min_length=5,
        description="Overall narrative summary of the diff review.",
    )
    issues: list[Issue] = Field(
        default_factory=list,
        description="All issues detected across the supplied diff.",
    )
    reviewed_chunks: int = Field(
        default=1,
        ge=1,
        description="Number of diff chunks that were independently reviewed.",
    )
    total_issues: int = Field(
        default=0,
        description="Auto-computed total issue count.",
    )

    @model_validator(mode="after")
    def compute_total_issues(self) -> "ReviewResponse":
        """Automatically derive total_issues from the issues list length."""
        self.total_issues = len(self.issues)
        return self

    def merge(self, other: "ReviewResponse") -> "ReviewResponse":
        """Merge another ReviewResponse into this one (chunked-review path).

        The summaries are concatenated, issues are combined, and the
        reviewed_chunks counter is incremented accordingly.

        Args:
            other: A second ReviewResponse produced from another diff chunk.

        Returns:
            A new ReviewResponse representing the combined review.
        """
        merged_summary = f"{self.summary}\n\n{other.summary}".strip()
        merged_issues = self.issues + other.issues
        return ReviewResponse(
            summary=merged_summary,
            issues=merged_issues,
            reviewed_chunks=self.reviewed_chunks + other.reviewed_chunks,
        )

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Request Model (entry-point DTO)
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    """Input payload for triggering an AI code review.

    Attributes:
        diff          : Raw Git unified diff string to review.
        pr_title      : Optional Pull Request title for context injection.
        pr_description: Optional PR description for additional context.
        language_hint : Optional primary language hint (e.g. "Python", "TypeScript").
    """

    diff: str = Field(
        ...,
        min_length=1,
        description="Raw Git unified diff (patch) to be reviewed.",
    )
    pr_title: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Pull Request title — injected as context into the prompt.",
    )
    pr_description: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Pull Request description body for additional context.",
    )
    language_hint: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Primary language of the changed code (e.g. 'Python').",
    )

    @field_validator("diff")
    @classmethod
    def diff_must_not_be_whitespace_only(cls, value: str) -> str:
        """Reject diffs that contain only whitespace."""
        if not value.strip():
            raise ValueError(
                "The supplied diff is empty or contains only whitespace. "
                "There is nothing to review."
            )
        return value

    model_config = {"str_strip_whitespace": True}
