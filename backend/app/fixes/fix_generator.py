"""
fix_generator.py  (app.fixes)
==============================
Stage 8.5 — AI Fix Generator.

Service that accepts a FixContext (Stage 8.4) and calls Google Gemini
(or an injected LLM completion callable) to produce a structured, minimal FixPatch.

Design principles (Phase 8 spec §8):
    - Must return structured output validating into FixPatch schema.
    - Low temperature (e.g. 0.1) for deterministic output.
    - Computes original_content_hash (SHA-256 hex) of source content.
    - Mockable for unit testing without external API calls.

Author : AI Code Review Bot — Phase 8 (Stage 8.5)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Awaitable, Callable, Optional

import google.generativeai as genai

from app.config import Settings, get_settings
from app.exceptions import GeminiParseError, GeminiServiceError
from app.fixes.exceptions import FixValidationError
from app.fixes.fix_context_builder import FixContext
from app.fixes.models import FixPatch
from app.prompts.fix_prompt import FIX_SYSTEM_PROMPT, build_fix_prompt
from app.utils import extract_json_from_text

logger = logging.getLogger(__name__)

# Type alias for custom/mockable LLM completion function
LLMCompleter = Callable[[str, str], Awaitable[str]]


def compute_sha256(content: str) -> str:
    """Compute SHA-256 hex digest of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class FixGenerator:
    """Generates structured minimal FixPatch payloads using Google Gemini.

    Args:
        config    : Application Settings instance.
        completer : Optional async callable (system_prompt, user_prompt) -> raw_response_str
                    for testing or alternative LLM backends.
    """

    def __init__(
        self,
        config: Optional[Settings] = None,
        completer: Optional[LLMCompleter] = None,
    ) -> None:
        self._config = config or get_settings()
        self._completer = completer

    async def generate_fix(self, context: FixContext) -> FixPatch:
        """Generate an AI code fix patch from a FixContext.

        Args:
            context : Populated FixContext from Stage 8.4.

        Returns:
            Validated FixPatch model.

        Raises:
            FixValidationError : If patch generation or JSON parsing fails.
        """
        logger.info(
            "Generating fix patch for request %s (file=%s, lang=%s)",
            context.fix_request_id,
            context.file_path,
            context.language_hint,
        )

        # ── 1. Compute original content hash ──────────────────────────
        source_text = context.file_content or context.file_diff_patch or context.file_path
        original_hash = compute_sha256(source_text)

        # ── 2. Build prompts ──────────────────────────────────────────
        user_prompt = build_fix_prompt(context)

        # ── 3. Call LLM (or mock completer) ───────────────────────────
        raw_response: str
        if self._completer is not None:
            raw_response = await self._completer(FIX_SYSTEM_PROMPT, user_prompt)
        else:
            raw_response = await self._call_gemini(FIX_SYSTEM_PROMPT, user_prompt)

        # ── 4. Extract and parse JSON ─────────────────────────────────
        raw_json = extract_json_from_text(raw_response)
        try:
            data = json.loads(raw_json)
        except Exception as exc:
            raise FixValidationError(
                f"Failed to parse valid JSON from AI Fix Generator response: {exc}. "
                f"Raw response preview: {raw_response[:200]!r}"
            ) from exc

        if not isinstance(data, dict):
            raise FixValidationError(
                f"Expected JSON object (dict) from AI Fix Generator response, got {type(data).__name__}."
            )

        # Inject computed original_content_hash if not provided or to enforce accuracy
        data["original_content_hash"] = original_hash

        # Ensure file_path matches context if missing/empty in LLM output
        if not data.get("file_path"):
            data["file_path"] = context.file_path

        # ── 5. Validate into FixPatch model ───────────────────────────
        try:
            fix_patch = FixPatch.model_validate(data)
        except Exception as exc:
            raise FixValidationError(
                f"AI-generated patch payload failed FixPatch validation: {exc}"
            ) from exc

        logger.info(
            "FixPatch generated successfully: file=%s, changed_lines=%s, hash=%s...",
            fix_patch.file_path,
            fix_patch.changed_lines,
            fix_patch.original_content_hash[:8],
        )

        return fix_patch

    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Google Gemini API with low temperature for fix generation."""
        try:
            genai.configure(api_key=self._config.gemini_api_key)
            model = genai.GenerativeModel(
                model_name=self._config.gemini_model,
                system_instruction=system_prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for deterministic code fixes
                    "max_output_tokens": 2048,
                    "response_mime_type": "application/json",
                },
            )
            response = await model.generate_content_async(user_prompt)
            if not response.text:
                raise GeminiServiceError("Gemini returned an empty response.")
            return response.text
        except Exception as exc:
            logger.error("Gemini API call failed during fix generation: %s", exc)
            raise FixValidationError(f"Gemini API call failed: {exc}") from exc
