"""
review_exceptions.py
====================
High-level service exceptions for the review processing domain.

Author : AI Code Review Bot
"""

from __future__ import annotations


class ReviewServiceError(Exception):
    """Raised when the review execution pipeline fails at the service level."""
