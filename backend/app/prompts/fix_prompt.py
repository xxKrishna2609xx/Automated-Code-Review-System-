"""
fix_prompt.py  (app.prompts)
============================
Stage 8.5 — AI Fix Generator Prompt Templates.

Defines the system prompt and prompt builder for generating minimal, targeted,
and safe code patches to remediate specific code review findings.

Design rules:
    - Output must be strict JSON matching FixPatch schema.
    - Minimal patch: modify only lines necessary to fix the finding.
    - No unrelated refactoring, whitespace changes, or style modifications.
    - Preserve existing behavior and API contracts.
    - Low temperature for deterministic output.

Author : AI Code Review Bot — Phase 8 (Stage 8.5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.fixes.fix_context_builder import FixContext


FIX_SYSTEM_PROMPT = """You are an expert, precision AI Code Remediation Engine.

Your sole task is to generate a minimal, targeted, and syntactically correct unified diff patch to fix a specific code review finding.

CRITICAL CONSTRAINTS:
1. MINIMAL PATCH: Modify ONLY the lines required to fix the issue. Do NOT refactor surrounding code, reformat file layout, or adjust unrelated whitespace.
2. PRESERVE CONTRACTS: Do NOT break existing function signatures, public APIs, or external behavior unless directly required to fix a security flaw or bug.
3. NO INVENTED APIS: Use standard library features or existing project utilities shown in the context. Never call non-existent methods or third-party packages.
4. VALID UNIFIED DIFF: The "patch" field must contain a standard GNU unified diff format string (starting with @@ hunk headers).
5. STRUCTURED JSON OUTPUT: Return ONLY a raw JSON object matching the required schema. No Markdown fences, no explanations outside the JSON object.

REQUIRED JSON SCHEMA:
{
  "file_path": "<target_file_path>",
  "patch": "<unified_diff_patch_string>",
  "changed_lines": [<list_of_1_based_modified_line_numbers>],
  "explanation": "<concise_plain_english_description_of_what_was_fixed_and_why>"
}
"""


def build_fix_prompt(context: FixContext) -> str:
    """Build the user prompt for the AI Fix Generator from a FixContext.

    Args:
        context : Populated FixContext from Stage 8.4.

    Returns:
        Formatted user prompt string ready for LLM generation.
    """
    sections: list[str] = [
        "### TARGET FIX REQUEST",
        f"- Repository: {context.repository}",
        f"- PR Number: #{context.pull_request_number}",
        f"- Target File: {context.file_path}",
        f"- Target Line: {context.line or 'N/A'}",
        f"- Primary Language: {context.language_hint}",
        "",
        "### FINDING TO REMEDIATE",
        f"- Title: {context.issue_title}",
        f"- Description: {context.issue_description}",
    ]

    if context.suggestion:
        sections.append(f"- Recommended Suggestion: {context.suggestion}")

    if context.file_diff_patch:
        sections.extend([
            "",
            "### FILE UNIFIED DIFF (FOR CONTEXT)",
            "```diff",
            context.file_diff_patch.strip(),
            "```",
        ])

    if context.context_window:
        sections.extend([
            "",
            "### CODE CONTEXT WINDOW (TARGET LINE MARKED WITH ->)",
            "```",
            context.context_window.strip(),
            "```",
        ])
    elif context.file_content:
        sections.extend([
            "",
            "### TARGET FILE CONTENT",
            "```",
            context.file_content.strip(),
            "```",
        ])

    sections.extend([
        "",
        "### INSTRUCTIONS",
        "Generate a minimal unified diff patch to fix the issue described above.",
        "Return strictly a JSON object with keys: file_path, patch, changed_lines, explanation.",
    ])

    return "\n".join(sections)
