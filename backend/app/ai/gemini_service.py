"""
gemini_service.py
=================
Low-level, reusable async wrapper around the Google Gemini API.

Responsibilities
----------------
• Initialise and hold a single ``genai.Client`` per service instance.
• Send a structured chat turn (system prompt + user prompt) to Gemini.
• Apply retry logic with exponential back-off on transient failures.
• Parse and validate the raw Gemini text response as a ReviewResponse.
• Chunk oversized diffs and merge per-chunk responses transparently.

This service is intentionally **prompt-agnostic** — callers inject the
system prompt and user prompt so the service can be reused for any
structured-output Gemini task.

Usage
-----
    from app.ai.gemini_service import GeminiService
    from app.config import settings

    svc = GeminiService(settings)
    response = await svc.review_code(diff=my_diff_string)

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Optional

import google.generativeai as genai
from google.api_core.exceptions import (
    DeadlineExceeded,
    GoogleAPICallError,
    InvalidArgument,
    ResourceExhausted,
    Unauthenticated,
)

from app.config import Settings
from app.models.review_models import ReviewResponse
from app.prompts.review_prompt import (
    SYSTEM_PROMPT,
    build_chunk_prompt,
    build_review_prompt,
)
from app.utils import extract_json_from_text, split_diff_into_chunks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class GeminiServiceError(Exception):
    """Base class for all errors raised by GeminiService."""


class GeminiAuthError(GeminiServiceError):
    """Raised when the API key is invalid or missing."""


class GeminiRateLimitError(GeminiServiceError):
    """Raised when the API quota is exhausted (HTTP 429)."""


class GeminiTimeoutError(GeminiServiceError):
    """Raised when an API call exceeds the configured timeout."""


class GeminiParseError(GeminiServiceError):
    """Raised when the model response cannot be parsed as ReviewResponse JSON."""


class EmptyDiffError(GeminiServiceError):
    """Raised when the supplied diff is empty after normalisation."""





# ---------------------------------------------------------------------------
# GeminiService
# ---------------------------------------------------------------------------


class GeminiService:
    """Async, reusable wrapper around the Google Gemini generative AI API.

    This class encapsulates all Gemini-specific concerns: client lifecycle,
    prompt assembly, generation config, retry logic, and response parsing.

    Consumers should inject an instance via FastAPI's ``Depends`` mechanism
    rather than constructing one manually — see ``get_gemini_service()``.

    Args:
        config: Application-wide ``Settings`` instance.
    """

    def __init__(self, config: Settings) -> None:
        self._config = config
        self._client: genai.GenerativeModel = self._build_client()
        logger.info(
            "GeminiService initialised — model=%s temperature=%.2f max_output_tokens=%d",
            config.gemini_model,
            config.gemini_temperature,
            config.gemini_max_output_tokens,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def review_code(
        self,
        diff: str,
        pr_title: Optional[str] = None,
        pr_description: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> ReviewResponse:
        """Review a Git diff and return a structured ``ReviewResponse``.

        Automatically splits the diff into chunks when it exceeds the
        configured ``max_diff_chars`` limit and merges the per-chunk
        responses into a single result.

        Args:
            diff            : Raw Git unified diff string.
            pr_title        : Optional PR title for context injection.
            pr_description  : Optional PR description body.
            language_hint   : Optional primary language hint (e.g. "Python").

        Returns:
            Validated ``ReviewResponse`` containing a summary and issue list.

        Raises:
            EmptyDiffError      : Diff is empty or whitespace-only.
            GeminiAuthError     : API key is invalid.
            GeminiRateLimitError: Quota exhausted after retries.
            GeminiTimeoutError  : Request timed out after retries.
            GeminiParseError    : Response could not be parsed as JSON.
            GeminiServiceError  : Any other unrecoverable error.
        """
        if not diff or not diff.strip():
            raise EmptyDiffError(
                "Cannot review an empty diff.  Supply a non-empty Git patch."
            )

        chunks = split_diff_into_chunks(
            diff=diff,
            max_chars=self._config.max_diff_chars,
            overlap_lines=self._config.chunk_overlap_lines,
        )

        if len(chunks) == 1:
            # Fast path — single chunk review
            user_prompt = build_review_prompt(
                diff=chunks[0],
                pr_title=pr_title,
                pr_description=pr_description,
                language_hint=language_hint,
            )
            return await self._generate_review(user_prompt)

        # Chunked path — review each piece and merge
        logger.info("Reviewing %d diff chunks independently.", len(chunks))
        merged: Optional[ReviewResponse] = None

        for idx, chunk in enumerate(chunks, start=1):
            chunk_prompt = build_chunk_prompt(
                chunk=chunk,
                chunk_index=idx,
                total_chunks=len(chunks),
                pr_title=pr_title,
                language_hint=language_hint,
            )
            chunk_response = await self._generate_review(chunk_prompt)

            if merged is None:
                merged = chunk_response
            else:
                merged = merged.merge(chunk_response)

            logger.debug("Chunk %d/%d reviewed — issues found: %d",
                         idx, len(chunks), chunk_response.total_issues)

        # ``merged`` is guaranteed non-None here because chunks is non-empty
        assert merged is not None
        return merged

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_client(self) -> genai.GenerativeModel:
        """Initialise the Gemini client with the configured API key and model.

        Returns:
            Configured ``GenerativeModel`` instance.

        Raises:
            GeminiAuthError: When the API key is rejected during configuration.
        """
        try:
            genai.configure(api_key=self._config.gemini_api_key)
            generation_config = genai.GenerationConfig(
                temperature=self._config.gemini_temperature,
                max_output_tokens=self._config.gemini_max_output_tokens,
                response_mime_type="application/json",
            )
            model = genai.GenerativeModel(
                model_name=self._config.gemini_model,
                system_instruction=SYSTEM_PROMPT,
                generation_config=generation_config,
            )
            return model
        except Exception as exc:
            logger.exception("Failed to initialise Gemini client.")
            raise GeminiAuthError(
                f"Could not initialise Gemini client: {exc}"
            ) from exc

    async def _generate_review(self, user_prompt: str) -> ReviewResponse:
        """Send a single prompt to Gemini and parse the response.

        Applies exponential back-off retry logic for transient failures
        (rate-limit, timeout, server errors).

        Args:
            user_prompt: Fully assembled user-turn prompt string.

        Returns:
            Validated ``ReviewResponse``.

        Raises:
            GeminiAuthError      : Unauthenticated API call.
            GeminiRateLimitError : Quota exhausted.
            GeminiTimeoutError   : Deadline exceeded.
            GeminiParseError     : Unparseable JSON response.
            GeminiServiceError   : Any other irrecoverable error.
        """
        max_retries = self._config.review_max_retries
        base_delay = self._config.review_retry_delay
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 2):  # +2 → 1 initial + N retries
            try:
                logger.debug(
                    "Gemini API call — attempt %d/%d.", attempt, max_retries + 1
                )
                raw_text = await self._call_gemini(user_prompt)
                return self._parse_response(raw_text)

            except GeminiAuthError:
                # Non-retryable — bad key; raise immediately.
                raise

            except GeminiRateLimitError as exc:
                last_error = exc
                if attempt > max_retries:
                    break
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Rate limited by Gemini API (attempt %d/%d). "
                    "Retrying in %.1fs.",
                    attempt, max_retries + 1, delay,
                )
                await asyncio.sleep(delay)

            except GeminiTimeoutError as exc:
                last_error = exc
                if attempt > max_retries:
                    break
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Gemini API timeout (attempt %d/%d). Retrying in %.1fs.",
                    attempt, max_retries + 1, delay,
                )
                await asyncio.sleep(delay)

            except GeminiParseError:
                # Non-retryable — malformed response; surface immediately.
                raise

            except GeminiServiceError as exc:
                last_error = exc
                if attempt > max_retries:
                    break
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Gemini API error (attempt %d/%d): %s. Retrying in %.1fs.",
                    attempt, max_retries + 1, exc, delay,
                )
                await asyncio.sleep(delay)

        raise last_error or GeminiServiceError(
            "Gemini review failed after all retries for an unknown reason."
        )

    async def _call_gemini(self, user_prompt: str) -> str:
        """Execute the actual Gemini API call in a thread pool.

        The ``google-generativeai`` SDK is synchronous; we wrap it with
        ``asyncio.to_thread`` so FastAPI's event loop is not blocked.

        Args:
            user_prompt: User-turn prompt string.

        Returns:
            Raw text content from the first Gemini response candidate.

        Raises:
            GeminiAuthError      : HTTP 401 from the API.
            GeminiRateLimitError : HTTP 429 / quota exhausted.
            GeminiTimeoutError   : HTTP 504 / deadline exceeded.
            GeminiServiceError   : All other API errors.
        """
        def _sync_call() -> str:
            start = time.monotonic()
            try:
                response = self._client.generate_content(
                    contents=user_prompt,
                    request_options={"timeout": self._config.gemini_timeout_seconds},
                )
                elapsed = time.monotonic() - start
                logger.debug(
                    "Gemini responded in %.2fs — candidates=%d.",
                    elapsed,
                    len(response.candidates) if response.candidates else 0,
                )

                # Guard: no candidates in the response
                if not response.candidates:
                    raise GeminiServiceError(
                        "Gemini returned a response with no candidates. "
                        "The diff may have been blocked by the safety filter."
                    )

                candidate = response.candidates[0]

                # Guard: candidate was blocked by safety filters
                if candidate.finish_reason and str(candidate.finish_reason) not in (
                    "1", "STOP"
                ):
                    raise GeminiServiceError(
                        f"Gemini candidate was blocked — finish_reason="
                        f"{candidate.finish_reason}."
                    )

                raw = response.text
                if not raw or not raw.strip():
                    raise GeminiParseError(
                        "Gemini returned an empty response.  "
                        "Cannot parse review from empty text."
                    )
                return raw

            except Unauthenticated as exc:
                raise GeminiAuthError(
                    f"Gemini API rejected the API key: {exc}"
                ) from exc
            except ResourceExhausted as exc:
                raise GeminiRateLimitError(
                    f"Gemini API quota exhausted: {exc}"
                ) from exc
            except DeadlineExceeded as exc:
                raise GeminiTimeoutError(
                    f"Gemini API call exceeded timeout of "
                    f"{self._config.gemini_timeout_seconds}s: {exc}"
                ) from exc
            except InvalidArgument as exc:
                raise GeminiServiceError(
                    f"Invalid argument sent to Gemini API: {exc}"
                ) from exc
            except GoogleAPICallError as exc:
                raise GeminiServiceError(
                    f"Gemini API call failed: {exc}"
                ) from exc

        return await asyncio.to_thread(_sync_call)

    def _parse_response(self, raw_text: str) -> ReviewResponse:
        """Parse and validate raw Gemini text into a ``ReviewResponse``.

        Handles Markdown code-fence stripping, JSON extraction, and
        Pydantic validation.

        Args:
            raw_text: Raw string from the Gemini API.

        Returns:
            Validated ``ReviewResponse`` instance.

        Raises:
            GeminiParseError: When the text cannot be parsed as valid JSON
                              or validated as a ``ReviewResponse``.
        """
        logger.debug("Parsing Gemini response (%d chars).", len(raw_text))

        json_str = extract_json_from_text(raw_text)

        try:
            data: dict[str, Any] = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error(
                "JSON decode failed.  Gemini raw response:\n%s", raw_text[:2000]
            )
            raise GeminiParseError(
                f"Gemini response is not valid JSON: {exc}.  "
                f"Raw snippet: {raw_text[:500]!r}"
            ) from exc

        try:
            review = ReviewResponse(**data)
        except Exception as exc:
            logger.error(
                "Pydantic validation failed for parsed JSON: %s", data
            )
            raise GeminiParseError(
                f"Gemini JSON does not match ReviewResponse schema: {exc}"
            ) from exc

        logger.info(
            "Review parsed successfully — issues=%d summary_len=%d",
            review.total_issues,
            len(review.summary),
        )
        return review


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------


def get_gemini_service() -> GeminiService:
    """FastAPI dependency that yields a ``GeminiService`` singleton.

    Usage in a route::

        @router.post("/review")
        async def review(
            request: ReviewRequest,
            svc: GeminiService = Depends(get_gemini_service),
        ) -> ReviewResponse:
            return await svc.review_code(diff=request.diff)

    Returns:
        Application-scoped ``GeminiService`` instance.
    """
    from app.config import settings  # deferred to avoid circular import

    # In a production app this would be a singleton managed by the DI container.
    # For simplicity we construct on first call — the underlying genai.Client
    # holds a connection pool so this is safe to call repeatedly.
    return GeminiService(config=settings)
