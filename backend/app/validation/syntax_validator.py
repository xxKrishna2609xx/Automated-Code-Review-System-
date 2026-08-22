"""
syntax_validator.py  (app.validation)
=====================================
Stage 8.7 — Language-Aware Syntax Validation.

Performs static syntax checking on updated file content resulting from patch
application BEFORE any GitHub operation.

Supported languages:
    - Python     : Static AST parsing via ``ast.parse()``.
    - JSON       : Strict JSON parsing via ``json.loads()``.
    - JS/TS/JSX/TSX: Static bracket/brace balance and quote matching.
    - Generic    : Fallback static structural balance checks.

CRITICAL SAFETY RULE:
    NEVER execute generated code (`exec()`, `eval()`, `importlib`, node runner, etc.).
    All validation is 100% static analysis.

Author : AI Code Review Bot — Phase 8 (Stage 8.7)
"""

from __future__ import annotations

import ast
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntaxValidationResult:
    """Outcome of static syntax validation.

    Attributes:
        valid         : True if syntax check passed cleanly.
        language      : Identified programming language.
        error_message : Human-readable syntax error detail, or None.
    """

    valid: bool
    language: str
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Language Resolver Helper
# ---------------------------------------------------------------------------


def resolve_language(language_or_path: str) -> str:
    """Normalize language name or derive it from file path extension."""
    clean = language_or_path.strip().lower()

    if clean in ("py", "python"):
        return "Python"
    if clean in ("json",):
        return "JSON"
    if clean in ("js", "javascript", "jsx"):
        return "JavaScript"
    if clean in ("ts", "typescript", "tsx"):
        return "TypeScript"

    if "." in clean:
        ext = clean.rsplit(".", 1)[-1]
        ext_map = {
            "py": "Python",
            "json": "JSON",
            "js": "JavaScript",
            "jsx": "JavaScript",
            "ts": "TypeScript",
            "tsx": "TypeScript",
            "go": "Go",
            "java": "Java",
            "rs": "Rust",
            "cpp": "C++",
            "c": "C",
            "md": "Markdown",
            "html": "HTML",
            "css": "CSS",
        }
        return ext_map.get(ext, "Generic")

    return "Generic"


# ---------------------------------------------------------------------------
# Syntax Checkers
# ---------------------------------------------------------------------------


def _check_python_syntax(content: str, filename: str = "<patch>") -> tuple[bool, Optional[str]]:
    """Validate Python code via static AST parsing."""
    try:
        ast.parse(content, filename=filename)
        return True, None
    except SyntaxError as err:
        msg = f"Python SyntaxError at line {err.lineno}, col {err.offset}: {err.msg}"
        return False, msg
    except Exception as err:
        return False, f"Python parsing error: {err}"


def _check_json_syntax(content: str) -> tuple[bool, Optional[str]]:
    """Validate JSON payload via json.loads()."""
    if not content.strip():
        return False, "JSON content is empty."
    try:
        json.loads(content)
        return True, None
    except json.JSONDecodeError as err:
        msg = f"JSONDecodeError at line {err.lineno}, col {err.colno}: {err.msg}"
        return False, msg


def _check_bracket_balance(content: str) -> tuple[bool, Optional[str]]:
    """Perform static bracket/brace/parentheses and string literal balance check."""
    stack: list[tuple[str, int, int]] = []  # (char, line, col)
    matching = {")": "(", "]": "[", "}": "{"}

    in_single_quote = False
    in_double_quote = False
    in_template_lit = False
    escape = False

    line_num = 1
    col_num = 0

    for char in content:
        col_num += 1
        if char == "\n":
            line_num += 1
            col_num = 0
            escape = False
            continue

        if escape:
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        # Handle strings / template literals
        if char == "'" and not in_double_quote and not in_template_lit:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote and not in_template_lit:
            in_double_quote = not in_double_quote
            continue
        if char == "`" and not in_single_quote and not in_double_quote:
            in_template_lit = not in_template_lit
            continue

        # Ignore brackets inside strings
        if in_single_quote or in_double_quote or in_template_lit:
            continue

        if char in "([{":
            stack.append((char, line_num, col_num))
        elif char in ")]}":
            expected = matching[char]
            if not stack or stack[-1][0] != expected:
                return (
                    False,
                    f"Unmatched closing bracket '{char}' at line {line_num}, col {col_num}.",
                )
            stack.pop()

    if stack:
        unclosed, u_line, u_col = stack[-1]
        return False, f"Unclosed bracket '{unclosed}' starting at line {u_line}, col {u_col}."

    if in_single_quote or in_double_quote or in_template_lit:
        return False, "Unclosed string or template literal detected."

    return True, None


# ---------------------------------------------------------------------------
# SyntaxValidator
# ---------------------------------------------------------------------------


class SyntaxValidator:
    """Language-aware static syntax validator."""

    def validate_syntax(
        self,
        content: str,
        language_or_path: str,
        filename: str = "<patch>",
    ) -> SyntaxValidationResult:
        """Validate static syntax of content for a specific language or file path.

        Args:
            content          : Updated target file content string.
            language_or_path : Language name ('Python', 'JSON') or file path ('app/main.py').
            filename         : Optional filename for error reporting.

        Returns:
            SyntaxValidationResult with pass/fail status and error message.
        """
        language = resolve_language(language_or_path)
        logger.info("Validating syntax for language '%s' (filename=%s)", language, filename)

        if not content and language != "Markdown":
            return SyntaxValidationResult(
                valid=False,
                language=language,
                error_message="File content is empty.",
            )

        if language == "Python":
            valid, err = _check_python_syntax(content, filename=filename)
        elif language == "JSON":
            valid, err = _check_json_syntax(content)
        elif language in ("JavaScript", "TypeScript"):
            valid, err = _check_bracket_balance(content)
        else:
            # Generic fallback
            valid, err = _check_bracket_balance(content)

        return SyntaxValidationResult(
            valid=valid,
            language=language,
            error_message=err,
        )
