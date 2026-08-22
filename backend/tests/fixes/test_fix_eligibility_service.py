"""
test_fix_eligibility_service.py  (tests.fixes)
================================================
Unit tests for Stage 8.3 — FixEligibilityService.

Tests cover:
    - All IssueCategory values → correct base decision
    - "Other" category → always ineligible
    - High-risk keyword overrides (auth, crypto, secrets, migration, infra,
      dependency, refactor)
    - Critical severity → requires_stronger_review
    - Risk level escalation when multiple override flags fire
    - CRITICAL-tier overrides flip eligible=False
    - HIGH-tier overrides keep eligible=True but set requires_stronger_review=True
    - Clean findings return requires_stronger_review=False
    - EligibilityResult is immutable (frozen dataclass)

Author : AI Code Review Bot — Phase 8 (Stage 8.3)
"""

from __future__ import annotations

import pytest

from app.fixes.fix_eligibility_service import (
    EligibilityResult,
    FixEligibilityService,
    RiskLevel,
)
from app.models.review_models import Issue, IssueCategory, Severity


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------

def _issue(
    category: str = "Bug",
    severity: str = "Medium",
    title: str = "Null pointer dereference",
    description: str = "The variable may be null before dereferencing.",
    suggestion: str = "Add a null check before use.",
) -> Issue:
    return Issue(
        title=title,
        severity=severity,
        category=category,
        description=description,
        suggestion=suggestion,
    )


service = FixEligibilityService()


# ---------------------------------------------------------------------------
# Base category decisions
# ---------------------------------------------------------------------------

class TestBaseCategoryEligibility:
    def test_bug_is_eligible(self):
        result = service.check(_issue(category="Bug"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.MEDIUM

    def test_security_is_eligible(self):
        result = service.check(_issue(category="Security", title="XSS vulnerability"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.HIGH

    def test_performance_is_eligible_low_risk(self):
        result = service.check(_issue(category="Performance", title="Inefficient loop"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.LOW

    def test_code_smell_is_eligible_low_risk(self):
        result = service.check(_issue(category="Code Smell"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.LOW

    def test_readability_is_eligible_low_risk(self):
        result = service.check(_issue(category="Readability"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.LOW

    def test_naming_is_eligible_low_risk(self):
        result = service.check(_issue(category="Naming", title="Misleading variable name"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.LOW

    def test_maintainability_is_eligible(self):
        result = service.check(_issue(category="Maintainability", title="Long function body"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.MEDIUM

    def test_error_handling_is_eligible(self):
        result = service.check(_issue(category="Error Handling"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.MEDIUM

    def test_edge_case_is_eligible(self):
        result = service.check(_issue(category="Edge Case"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.MEDIUM

    def test_best_practice_is_eligible_low_risk(self):
        result = service.check(_issue(category="Best Practice"))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.LOW

    def test_other_is_ineligible(self):
        result = service.check(_issue(category="Other"))
        assert result.eligible is False
        assert "ambiguous" in result.reason.lower() or "other" in result.reason.lower()

    def test_other_does_not_require_stronger_review_flag(self):
        """'Other' is simply ineligible — not a 'requires stronger review' case."""
        result = service.check(_issue(category="Other"))
        assert result.requires_stronger_review is False


# ---------------------------------------------------------------------------
# Clean findings: no override keywords → clean path
# ---------------------------------------------------------------------------

class TestCleanFindings:
    def test_clean_bug_no_stronger_review_needed(self):
        result = service.check(_issue(
            category="Bug",
            title="Off-by-one error in loop",
            description="Loop runs one extra iteration.",
            suggestion="Change <= to <.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is False

    def test_clean_sql_injection_without_auth_keywords(self):
        result = service.check(_issue(
            category="Security",
            title="SQL Injection Risk",
            description="The query is built via string concatenation from user input.",
            suggestion="Use parameterized queries instead.",
        ))
        assert result.eligible is True
        # SQL injection is eligible — no auth/crypto/secret keywords triggered
        assert result.requires_stronger_review is False


# ---------------------------------------------------------------------------
# Auth / authorization keyword overrides → CRITICAL → ineligible
# ---------------------------------------------------------------------------

class TestAuthKeywordOverrides:
    def test_authentication_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="Broken authentication flow",
            description="The authentication check can be bypassed.",
            suggestion="Fix the authentication logic.",
        ))
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.requires_stronger_review is True

    def test_authorization_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Bug",
            title="Missing authorization check",
            description="The authorization guard is absent on this endpoint.",
            suggestion="Add authorization middleware.",
        ))
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_password_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="Weak password hashing",
            description="Passwords are stored with MD5.",
            suggestion="Use bcrypt for password hashing.",
        ))
        # "password" is an auth pattern → CRITICAL
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_jwt_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="JWT not validated",
            description="The JWT signature is not verified.",
            suggestion="Add signature verification.",
        ))
        assert result.eligible is False

    def test_session_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Bug",
            title="Session not invalidated",
            description="User session persists after logout.",
            suggestion="Call session.invalidate() on logout.",
        ))
        assert result.eligible is False


# ---------------------------------------------------------------------------
# Crypto keyword overrides → CRITICAL → ineligible
# ---------------------------------------------------------------------------

class TestCryptoKeywordOverrides:
    def test_encryption_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="Weak encryption algorithm",
            description="Using DES encrypt which is deprecated.",
            suggestion="Switch to AES-256.",
        ))
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_tls_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="TLS 1.0 still enabled",
            description="The server accepts TLS 1.0 connections.",
            suggestion="Disable TLS versions below 1.2.",
        ))
        assert result.eligible is False

    def test_hashing_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Performance",
            title="Slow hashing algorithm",
            description="SHA-256 hashing is used in a tight loop.",
            suggestion="Cache the hashed result.",
        ))
        # "hashing" matches crypto patterns
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# Secret / credential keyword overrides → CRITICAL → ineligible
# ---------------------------------------------------------------------------

class TestSecretKeywordOverrides:
    def test_secret_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="Hardcoded secret in source",
            description="A secret key is stored directly in the source file.",
            suggestion="Move to environment variables.",
        ))
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_api_key_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Security",
            title="Exposed API key",
            description="The API key is committed to source control.",
            suggestion="Remove and rotate the API key.",
        ))
        assert result.eligible is False

    def test_credential_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Bug",
            title="Credential leak in logs",
            description="User credentials appear in log output.",
            suggestion="Mask credentials before logging.",
        ))
        assert result.eligible is False


# ---------------------------------------------------------------------------
# Migration / destructive DB keyword overrides → CRITICAL → ineligible
# ---------------------------------------------------------------------------

class TestMigrationKeywordOverrides:
    def test_migration_keyword_makes_ineligible(self):
        result = service.check(_issue(
            category="Bug",
            title="Missing rollback in migration",
            description="The database migration has no rollback procedure.",
            suggestion="Add a rollback step.",
        ))
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_drop_table_makes_ineligible(self):
        result = service.check(_issue(
            category="Performance",
            title="Unnecessary DROP TABLE",
            description="The script calls DROP TABLE before recreation.",
            suggestion="Use DROP TABLE IF EXISTS.",
        ))
        assert result.eligible is False

    def test_data_loss_makes_ineligible(self):
        result = service.check(_issue(
            category="Bug",
            title="Data loss risk",
            description="This operation could result in data loss.",
            suggestion="Add a backup step.",
        ))
        assert result.eligible is False


# ---------------------------------------------------------------------------
# Infrastructure keyword overrides → HIGH → eligible + requires_stronger_review
# ---------------------------------------------------------------------------

class TestInfraKeywordOverrides:
    def test_dockerfile_keyword_requires_stronger_review(self):
        result = service.check(_issue(
            category="Best Practice",
            title="Dockerfile best practice missing",
            description="The Dockerfile uses root user.",
            suggestion="Add USER directive to run as non-root.",
        ))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.HIGH
        assert result.requires_stronger_review is True

    def test_kubernetes_keyword_requires_stronger_review(self):
        result = service.check(_issue(
            category="Bug",
            title="Kubernetes resource limit missing",
            description="No resource limits are set in the deployment manifest.",
            suggestion="Add resource limits.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is True

    def test_deployment_keyword_requires_stronger_review(self):
        result = service.check(_issue(
            category="Maintainability",
            title="Missing deployment health check",
            description="The deployment lacks a liveness probe.",
            suggestion="Add a liveness probe.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is True


# ---------------------------------------------------------------------------
# Dependency upgrade keyword overrides → HIGH → eligible + requires_stronger_review
# ---------------------------------------------------------------------------

class TestDependencyKeywordOverrides:
    def test_dependency_keyword_requires_stronger_review(self):
        result = service.check(_issue(
            category="Best Practice",
            title="Outdated dependency",
            description="The dependency on requests 2.24 is outdated.",
            suggestion="Upgrade to the latest stable version.",
        ))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.HIGH
        assert result.requires_stronger_review is True

    def test_requirements_txt_requires_stronger_review(self):
        result = service.check(_issue(
            category="Best Practice",
            title="Pin versions in requirements.txt",
            description="requirements.txt lacks pinned versions.",
            suggestion="Pin each dependency to a specific version.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is True


# ---------------------------------------------------------------------------
# Refactor keyword overrides → HIGH → eligible + requires_stronger_review
# ---------------------------------------------------------------------------

class TestRefactorKeywordOverrides:
    def test_refactor_keyword_requires_stronger_review(self):
        result = service.check(_issue(
            category="Maintainability",
            title="Large refactor needed",
            description="This function needs a significant refactor.",
            suggestion="Break into smaller functions.",
        ))
        assert result.eligible is True
        assert result.risk_level == RiskLevel.HIGH
        assert result.requires_stronger_review is True

    def test_architecture_keyword_requires_stronger_review(self):
        result = service.check(_issue(
            category="Maintainability",
            title="Architecture change required",
            description="The current architecture is not scalable.",
            suggestion="Adopt a layered architecture.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is True


# ---------------------------------------------------------------------------
# Severity-based overrides
# ---------------------------------------------------------------------------

class TestSeverityOverrides:
    def test_critical_severity_requires_stronger_review(self):
        result = service.check(_issue(
            category="Bug",
            severity="Critical",
            title="Unhandled null dereference",
            description="A null pointer dereference causes a crash.",
            suggestion="Add null guard.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is True
        assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_low_severity_clean_finding_no_override(self):
        result = service.check(_issue(
            category="Naming",
            severity="Low",
            title="Variable name is too short",
            description="Variable 'x' should be more descriptive.",
            suggestion="Rename to 'user_count'.",
        ))
        assert result.eligible is True
        assert result.requires_stronger_review is False
        assert result.risk_level == RiskLevel.LOW


# ---------------------------------------------------------------------------
# Multiple override flags → takes highest risk
# ---------------------------------------------------------------------------

class TestMultipleOverrideFlags:
    def test_infra_plus_dependency_takes_highest_risk(self):
        result = service.check(_issue(
            category="Best Practice",
            title="Upgrade deployment dependency",
            description="The deployment pipeline depends on an outdated library.",
            suggestion="Upgrade the dependency in the deployment script.",
        ))
        assert result.eligible is True
        # Both infra ("deployment") and dependency ("dependency") trigger HIGH
        assert result.risk_level == RiskLevel.HIGH
        assert result.requires_stronger_review is True

    def test_auth_plus_crypto_makes_ineligible_critical(self):
        result = service.check(_issue(
            category="Security",
            title="Broken JWT encryption",
            description="JWT tokens are signed with a weak encryption key.",
            suggestion="Use strong encryption for JWT signing.",
        ))
        # Both auth (JWT) and crypto (encryption) patterns → CRITICAL → ineligible
        assert result.eligible is False
        assert result.risk_level == RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# EligibilityResult immutability
# ---------------------------------------------------------------------------

class TestEligibilityResultImmutability:
    def test_result_is_frozen(self):
        result = EligibilityResult(
            eligible=True,
            reason="Eligible",
            risk_level=RiskLevel.LOW,
        )
        with pytest.raises((AttributeError, TypeError)):
            result.eligible = False  # type: ignore[misc]

    def test_result_has_expected_fields(self):
        result = EligibilityResult(
            eligible=False,
            reason="Not eligible",
            risk_level=RiskLevel.CRITICAL,
            requires_stronger_review=True,
        )
        assert result.eligible is False
        assert result.reason == "Not eligible"
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.requires_stronger_review is True


# ---------------------------------------------------------------------------
# RiskLevel enum completeness
# ---------------------------------------------------------------------------

class TestRiskLevelEnum:
    def test_all_four_risk_levels_present(self):
        assert set(r.value for r in RiskLevel) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def test_risk_level_is_string_enum(self):
        assert isinstance(RiskLevel.LOW, str)
