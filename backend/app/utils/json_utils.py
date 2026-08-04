"""
json_utils.py
=============
Utilities for parsing and sanitising JSON outputs returned by LLMs.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import re


def extract_json_from_text(text: str) -> str:
    """Extract a JSON payload from raw Gemini text response.

    Gemini occasionally wraps its JSON in Markdown fences (e.g. ```json ... ```).
    This utility extracts the JSON body safely.

    Strategy:
        1. Try to find content between ```json … ``` Markdown fences.
        2. Fall back to locating the first ``{`` … last ``}`` brace pair.
        3. Return raw stripped text if neither pattern matches.

    Args:
        text: Raw text response string.

    Returns:
        Extracted JSON substring ready for json.loads().
    """
    # Strategy 1 — Markdown code fence
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()

    # Strategy 2 — Locate first { … last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()

    # Strategy 3 — Return as-is
    return text.strip()
