"""
exceptions.py  (app.fixes)
==========================
Domain-specific exceptions for Phase 8 Fix & Auto-Remediation pipeline.

These are raised by fix services and caught by the API router layer,
which maps them to appropriate HTTP responses.

Author : AI Code Review Bot — Phase 8 (Stage 8.2)
"""

from __future__ import annotations


class FixNotFoundError(Exception):
    """Raised when a FixRequest or referenced review/issue cannot be found."""


class FixValidationError(Exception):
    """Raised when a FixRequest fails server-side validation.

    Examples: review does not exist, issue not in review, file path mismatch.
    """


class FixIneligibleError(Exception):
    """Raised when an issue is found but is not eligible for auto-remediation.

    Set in Stage 8.3 (FixEligibilityService). Placeholder raised here if
    the service is called before Stage 8.3 is implemented.
    """


class FixStateError(Exception):
    """Raised when a state-transition is attempted on a fix in the wrong state.

    Example: approving a fix that is not yet READY_FOR_APPROVAL.
    """
