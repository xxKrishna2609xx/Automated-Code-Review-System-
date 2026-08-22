"""
fix_eligibility_service.py  (app.fixes)
=========================================
Stage 8.3 — Fix Eligibility Policy.

Determines whether a specific finding (Issue + context) is eligible for
AI-generated auto-remediation.

Design principles (Phase 8 spec §6):
    - "Do not assume every finding is safely auto-fixable."
    - Initially ALLOW: obvious bugs, simple security fixes, simple performance
      fixes, documentation fixes, simple testing improvements.
    - Initially REQUIRE STRONGER REVIEW for: destructive DB ops, auth/authz
      architecture, crypto, infrastructure, dependency upgrades, large
      multi-file refactors, migrations, secret/credential handling, ambiguous
      findings.
    - Return: eligible (bool), reason (str), risk_level (str).

No Gemini calls.  No GitHub mutations.  No MongoDB writes.
Pure, independently testable logic.

Author : AI Code Review Bot — Phase 8 (Stage 8.3)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.models.review_models import Issue, IssueCategory, Severity


# ---------------------------------------------------------------------------
# Risk Level Enum
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Risk level associated with an auto-remediation attempt.

    LOW         — Mechanical fix; minimal blast radius.
    MEDIUM      — Moderate complexity; developer review recommended.
    HIGH        — Non-trivial change; careful human review required.
    CRITICAL    — Dangerous category; requires explicit senior sign-off.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# EligibilityResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EligibilityResult:
    """Outcome of a fix eligibility check.

    Attributes:
        eligible   : True if the issue may proceed to fix generation.
        reason     : Human-readable explanation of the decision.
        risk_level : Assessed risk level of the proposed auto-remediation.
        requires_stronger_review : True when eligible but flagged for extra
                                   scrutiny (e.g. developer must acknowledge
                                   the risk before approving).
    """

    eligible: bool
    reason: str
    risk_level: RiskLevel
    requires_stronger_review: bool = False


# ---------------------------------------------------------------------------
# High-risk keyword groups
# ---------------------------------------------------------------------------

# These patterns in title or description signal elevated risk regardless
# of the IssueCategory.  Patterns are applied case-insensitively.

_AUTH_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bauth(?:entication|orization|oriz)\b",
        r"\bpassword\b",
        r"\btoken\b",
        r"\bjwt\b",
        r"\boauth\b",
        r"\bsso\b",
        r"\brbac\b",
        r"\brole.based\b",
        r"\bpermission\b",
        r"\baccess.control\b",
        r"\bsession\b",
    ]
]

_CRYPTO_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bcrypt(?:o|ograph)\w*\b",
        r"\bencrypt\b",
        r"\bdecrypt\b",
        r"\bhashing?\b",
        r"\bhmac\b",
        r"\bsha-?\d+\b",
        r"\brsa\b",
        r"\baes\b",
        r"\bssl\b",
        r"\btls\b",
        r"\bcertificate\b",
    ]
]

_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bsecret\b",
        r"\bapi.?key\b",
        r"\bcredential\b",
        r"\benv(?:ironment)?.?var(?:iable)?\b",
        r"\b\.env\b",
        r"\bprivate.?key\b",
    ]
]

_INFRA_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bdocker(?:file)?\b",
        r"\bkubernetes\b",
        r"\bk8s\b",
        r"\bterraform\b",
        r"\bcloud(?:formation|watch)?\b",
        r"\bdeployment\b",
        r"\bci.?cd\b",
        r"\bpipeline\b",
        r"\binfrastructure\b",
    ]
]

_MIGRATION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bmigration\b",
        r"\bschema.?change\b",
        r"\balter.?table\b",
        r"\bdrop.?table\b",
        r"\bdrop.?column\b",
        r"\btruncate\b",
        r"\bdestructive\b",
        r"\bdata.?loss\b",
    ]
]

_DEPENDENCY_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bdependency\b",
        r"\bdependencies\b",
        r"\bupgrade\b",
        r"\bpip.?install\b",
        r"\bnpm.?install\b",
        r"\brequirements\.txt\b",
        r"\bpackage\.json\b",
        r"\bpoetry\.toml\b",
        r"\bpyproject\.toml\b",
    ]
]

_REFACTOR_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\brefactor\b",
        r"\bmulti.?file\b",
        r"\bmultiple.?files\b",
        r"\barchitecture\b",
        r"\bbreaking.?change\b",
    ]
]


def _matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    """Return True if ``text`` matches any of the compiled patterns."""
    return any(p.search(text) for p in patterns)


def _combined_text(issue: Issue) -> str:
    """Combine issue fields into a single searchable string."""
    return f"{issue.title} {issue.description} {issue.suggestion}"


# ---------------------------------------------------------------------------
# Category-level base eligibility table
# ---------------------------------------------------------------------------

# Base decisions per IssueCategory before keyword overrides are applied.
# Format: (eligible, risk_level, reason)
_BASE_POLICY: dict[str, tuple[bool, RiskLevel, str]] = {
    IssueCategory.BUG.value: (
        True, RiskLevel.MEDIUM,
        "Bug fixes are eligible for auto-remediation with developer review.",
    ),
    IssueCategory.SECURITY.value: (
        True, RiskLevel.HIGH,
        "Security fixes are eligible but require careful review before approval.",
    ),
    IssueCategory.PERFORMANCE.value: (
        True, RiskLevel.LOW,
        "Performance improvements are eligible for auto-remediation.",
    ),
    IssueCategory.CODE_SMELL.value: (
        True, RiskLevel.LOW,
        "Code smell fixes are eligible for auto-remediation.",
    ),
    IssueCategory.READABILITY.value: (
        True, RiskLevel.LOW,
        "Readability improvements are eligible for auto-remediation.",
    ),
    IssueCategory.NAMING.value: (
        True, RiskLevel.LOW,
        "Naming fixes are eligible for auto-remediation.",
    ),
    IssueCategory.MAINTAINABILITY.value: (
        True, RiskLevel.MEDIUM,
        "Maintainability improvements are eligible with developer review.",
    ),
    IssueCategory.ERROR_HANDLING.value: (
        True, RiskLevel.MEDIUM,
        "Error handling improvements are eligible for auto-remediation.",
    ),
    IssueCategory.EDGE_CASE.value: (
        True, RiskLevel.MEDIUM,
        "Edge case fixes are eligible with developer review.",
    ),
    IssueCategory.BEST_PRACTICE.value: (
        True, RiskLevel.LOW,
        "Best practice improvements are eligible for auto-remediation.",
    ),
    IssueCategory.OTHER.value: (
        False, RiskLevel.MEDIUM,
        "Issues categorized as 'Other' are ambiguous; manual remediation required.",
    ),
}


# ---------------------------------------------------------------------------
# FixEligibilityService
# ---------------------------------------------------------------------------


class FixEligibilityService:
    """Determines whether a finding is eligible for AI auto-remediation.

    Applies a two-tier policy:
        1. Category-level base decision (from _BASE_POLICY table).
        2. High-risk keyword override — promotes risk level and may flip
           an ELIGIBLE finding to REQUIRES_REVIEW when the title or
           description contains patterns matching auth, crypto, secrets,
           infrastructure, migrations, or broad refactors.

    Usage::

        service = FixEligibilityService()
        result = service.check(issue)
        if not result.eligible:
            raise FixIneligibleError(result.reason)

    Args:
        None — the service is stateless and has no external dependencies.
    """

    def check(self, issue: Issue) -> EligibilityResult:
        """Evaluate a single Issue for auto-remediation eligibility.

        Args:
            issue : Phase 6 ``Issue`` model to evaluate.

        Returns:
            ``EligibilityResult`` with eligible flag, reason, and risk_level.
        """
        category_key = str(issue.category)
        base_eligible, base_risk, base_reason = _BASE_POLICY.get(
            category_key,
            (False, RiskLevel.MEDIUM, f"Unknown category '{category_key}'; manual review required."),
        )

        # Immediately ineligible categories — no keyword override can help
        if not base_eligible:
            return EligibilityResult(
                eligible=False,
                reason=base_reason,
                risk_level=base_risk,
                requires_stronger_review=False,
            )

        # Keyword-based override checks
        combined = _combined_text(issue)
        override_flags: list[tuple[str, RiskLevel]] = []

        if _matches_any(combined, _AUTH_PATTERNS):
            override_flags.append((
                "authentication/authorization",
                RiskLevel.CRITICAL,
            ))
        if _matches_any(combined, _CRYPTO_PATTERNS):
            override_flags.append(("cryptographic operations", RiskLevel.CRITICAL))
        if _matches_any(combined, _SECRET_PATTERNS):
            override_flags.append(("secret/credential handling", RiskLevel.CRITICAL))
        if _matches_any(combined, _MIGRATION_PATTERNS):
            override_flags.append(("destructive database operations/migrations", RiskLevel.CRITICAL))
        if _matches_any(combined, _INFRA_PATTERNS):
            override_flags.append(("infrastructure changes", RiskLevel.HIGH))
        if _matches_any(combined, _DEPENDENCY_PATTERNS):
            override_flags.append(("dependency upgrades", RiskLevel.HIGH))
        if _matches_any(combined, _REFACTOR_PATTERNS):
            override_flags.append(("large refactors/architecture changes", RiskLevel.HIGH))

        # Severity override: Critical issues always require stronger review
        if issue.severity in (Severity.CRITICAL.value, "Critical"):
            override_flags.append((
                "Critical severity requires additional human scrutiny",
                RiskLevel.HIGH,
            ))

        if not override_flags:
            # Clean path — no high-risk patterns detected
            return EligibilityResult(
                eligible=True,
                reason=base_reason,
                risk_level=base_risk,
                requires_stronger_review=False,
            )

        # Determine the highest risk level among all triggered overrides
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_risk = max(
            (risk for _, risk in override_flags),
            key=lambda r: risk_order.index(r),
            default=base_risk,
        )
        max_risk = max(
            [max_risk, base_risk],
            key=lambda r: risk_order.index(r),
        )

        flag_labels = ", ".join(label for label, _ in override_flags)

        # CRITICAL-tier overrides make the finding INELIGIBLE for auto-fix
        if max_risk == RiskLevel.CRITICAL:
            return EligibilityResult(
                eligible=False,
                reason=(
                    f"This finding involves {flag_labels}. "
                    "Auto-remediation is not safe for this category; "
                    "manual remediation with senior review is required."
                ),
                risk_level=RiskLevel.CRITICAL,
                requires_stronger_review=True,
            )

        # HIGH-tier overrides: eligible but requires_stronger_review = True
        return EligibilityResult(
            eligible=True,
            reason=(
                f"{base_reason} "
                f"However, this finding involves {flag_labels} — "
                "additional human scrutiny is required before approval."
            ),
            risk_level=max_risk,
            requires_stronger_review=True,
        )
