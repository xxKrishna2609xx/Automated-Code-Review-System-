"""
review_prompt.py
================
Centralised prompt repository for the AI Code Review Engine.

All prompts are stored as plain Python constants / builder functions so
they can be versioned, unit-tested, and swapped independently of the
Gemini service implementation.

Design rationale
----------------
• Prompts live here — **not** inside the service layer.
• The system prompt uses a fixed instruction block; the user prompt is
  assembled dynamically at call time so optional context (PR title,
  description, language) can be injected cleanly.
• Output format is enforced in the system prompt, reducing parse errors.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

from textwrap import dedent
from typing import Optional


# ---------------------------------------------------------------------------
# System Prompt (fixed instruction block — sent once per conversation)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = dedent("""\
    You are a world-class Senior Software Engineer and Pull Request Reviewer \
    with 15+ years of industry experience across multiple programming languages, \
    distributed systems, security engineering, and software architecture.

    YOUR ROLE
    ---------
    Your sole responsibility is to perform a thorough, professional code review \
    of the Git diff that the user supplies. You are NOT asked to write new code. \
    You are NOT asked to explain concepts. You are asked only to review the \
    supplied diff.

    REVIEW SCOPE
    ------------
    Analyse ONLY the lines that appear in the unified diff.
    - Lines prefixed with "+" are additions (newly introduced code).
    - Lines prefixed with "-" are deletions (removed code).
    - Context lines (no prefix) are provided only for understanding.  Do NOT \
      raise issues about unchanged context lines unless a newly added line \
      directly interacts with a context line in a problematic way.
    - NEVER comment on code that is not present in the supplied diff.
    - NEVER hallucinate lines, variables, functions, or modules that do not \
      appear in the diff.

    REVIEW CRITERIA
    ---------------
    Inspect the diff for ALL of the following, where applicable:

    1.  Bugs              — Logic errors, off-by-one, incorrect conditions,
                            wrong data types, silent failures.
    2.  Security          — Injection vulnerabilities (SQL, command, XSS),
                            insecure deserialization, hard-coded secrets,
                            missing authentication/authorisation checks,
                            information leakage, unsafe cryptography.
    3.  Performance       — Unnecessary loops, N+1 queries, blocking I/O
                            in async contexts, excessive memory allocation,
                            missing indexes or caching opportunities.
    4.  Code Smells       — Long functions, deep nesting, magic numbers,
                            dead code, copy-paste duplication.
    5.  Readability       — Unclear variable names, missing whitespace,
                            inconsistent formatting, overly clever one-liners.
    6.  Naming            — Non-descriptive names, misleading names,
                            violation of language naming conventions.
    7.  Maintainability   — God objects, tight coupling, missing abstractions,
                            direct dependency on concrete types.
    8.  Error Handling    — Swallowed exceptions, bare except, missing
                            validation, no fallback strategy.
    9.  Edge Cases        — Null/None/empty input, integer overflow, boundary
                            values, concurrent access, unexpected input types.
    10. Best Practices    — Violations of SOLID, DRY, KISS, YAGNI,
                            language-specific idioms, missing docstrings or
                            type annotations on public API.

    SEVERITY CLASSIFICATION
    -----------------------
    Assign exactly ONE of the following severity levels to each issue:
    - Critical : Must fix before merge; exploitable vulnerability or crash.
    - High     : Likely to cause incorrect behaviour or significant regression.
    - Medium   : Should be fixed; degrades quality or maintainability.
    - Low      : Nice-to-have improvement; stylistic or minor readability.

    NO-ISSUE CASE
    -------------
    If the diff contains no detectable issues, return an empty "issues" array \
    and write a positive summary.  Do not invent issues to appear thorough.

    OUTPUT FORMAT — CRITICAL
    ------------------------
    You MUST respond with **valid JSON only**.
    Do NOT wrap it in Markdown code fences.
    Do NOT add any prose before or after the JSON.
    The response MUST conform exactly to this schema:

    {
      "summary": "<string: 1-3 sentence overall assessment>",
      "issues": [
        {
          "title": "<string: short, unique title>",
          "severity": "<Critical | High | Medium | Low>",
          "line": <integer | null>,
          "category": "<Bug | Security | Performance | Code Smell | \
Readability | Naming | Maintainability | Error Handling | Edge Case | \
Best Practice | Other>",
          "description": "<string: thorough explanation>",
          "suggestion": "<string: concrete, actionable fix>"
        }
      ]
    }

    If there are no issues, return:
    {
      "summary": "<positive assessment>",
      "issues": []
    }

    Respond with JSON and nothing else.
""")


# ---------------------------------------------------------------------------
# User Prompt Builder
# ---------------------------------------------------------------------------

def build_review_prompt(
    diff: str,
    pr_title: Optional[str] = None,
    pr_description: Optional[str] = None,
    language_hint: Optional[str] = None,
) -> str:
    """Assemble the user-turn prompt for a single review request.

    Injects optional contextual metadata (PR title, description, language)
    above the diff so Gemini can interpret intent without expanding review
    scope beyond the supplied patch.

    Args:
        diff            : Raw Git unified diff string.
        pr_title        : Optional Pull Request title.
        pr_description  : Optional PR description body.
        language_hint   : Optional primary programming language of the diff
                          (e.g. ``"Python"``, ``"TypeScript"``).

    Returns:
        Fully assembled user-turn prompt string ready to send to Gemini.
    """
    sections: list[str] = []

    # ── Optional context block ──────────────────────────────────────────
    context_lines: list[str] = []

    if language_hint:
        context_lines.append(f"Primary language : {language_hint.strip()}")

    if pr_title:
        context_lines.append(f"Pull Request title: {pr_title.strip()}")

    if pr_description:
        # Truncate extremely long PR descriptions to avoid wasting tokens.
        body = pr_description.strip()
        if len(body) > 1500:
            body = body[:1500] + "\n... [truncated for brevity]"
        context_lines.append(f"Pull Request description:\n{body}")

    if context_lines:
        context_block = "CONTEXT (for understanding intent only — do NOT review)\n"
        context_block += "-" * 60 + "\n"
        context_block += "\n".join(context_lines)
        context_block += "\n" + "-" * 60
        sections.append(context_block)

    # ── Diff block ──────────────────────────────────────────────────────
    diff_block = (
        "GIT DIFF TO REVIEW\n"
        + "-" * 60 + "\n"
        + diff.strip()
        + "\n" + "-" * 60
    )
    sections.append(diff_block)

    # ── Closing instruction ─────────────────────────────────────────────
    sections.append(
        "Review ONLY the diff above.  "
        "Respond with valid JSON conforming to the schema in your instructions. "
        "Do not add Markdown, prose, or explanation outside the JSON object."
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Chunk-aware prompt builder
# ---------------------------------------------------------------------------

def build_chunk_prompt(
    chunk: str,
    chunk_index: int,
    total_chunks: int,
    pr_title: Optional[str] = None,
    language_hint: Optional[str] = None,
) -> str:
    """Build a prompt for a single chunk when the diff is split across
    multiple Gemini API calls.

    Args:
        chunk       : Partial diff string for this chunk.
        chunk_index : 1-based index of the current chunk.
        total_chunks: Total number of chunks being reviewed.
        pr_title    : Optional PR title for context.
        language_hint: Optional language hint.

    Returns:
        Assembled prompt string for the given chunk.
    """
    header_lines: list[str] = [
        f"NOTE: This diff is large and has been split into {total_chunks} chunk(s).",
        f"You are now reviewing chunk {chunk_index} of {total_chunks}.",
        "Apply the same review criteria as usual.",
    ]

    if language_hint:
        header_lines.append(f"Primary language: {language_hint.strip()}")

    if pr_title:
        header_lines.append(f"Pull Request title: {pr_title.strip()}")

    header = "\n".join(header_lines)

    diff_block = (
        f"GIT DIFF — CHUNK {chunk_index}/{total_chunks}\n"
        + "-" * 60 + "\n"
        + chunk.strip()
        + "\n" + "-" * 60
    )

    closing = (
        "Review ONLY the diff chunk above.  "
        "Respond with valid JSON conforming to the schema in your instructions."
    )

    return "\n\n".join([header, diff_block, closing])
