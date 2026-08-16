"""
config.py
=========
Application-wide configuration loaded from environment variables.

All secrets and runtime settings are read from the environment (or a .env
file) using Pydantic's ``BaseSettings``.  This module is the **single source
of truth** for configuration across the entire backend.

Usage
-----
    from app.config import settings

    key = settings.gemini_api_key

The ``settings`` singleton is created at module import time.  In tests,
override individual fields via environment variables or by constructing a
new ``Settings`` instance directly.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Runtime configuration — populated from environment / .env file.

    All attributes map 1-to-1 to environment variables (case-insensitive).

    Attributes
    ----------
    gemini_api_key          : Google Gemini API key.  **Required.**
    gemini_model            : Gemini model identifier.
    gemini_max_output_tokens: Maximum tokens in the model response.
    gemini_temperature      : Sampling temperature (0.0–1.0).
    gemini_timeout_seconds  : HTTP timeout for Gemini API calls (seconds).

    max_diff_chars          : Maximum characters in a single diff before
                              automatic chunking kicks in.
    chunk_overlap_lines     : Lines of overlap kept between adjacent chunks
                              so context is not completely lost.

    review_max_retries      : Maximum number of retry attempts on transient
                              failures (rate-limit, timeout, server error).
    review_retry_delay      : Base delay in seconds between retries
                              (exponential back-off applied on top).

    log_level               : Root logging level (DEBUG | INFO | WARNING …).
    environment             : Deployment environment label (dev | staging | prod).
    """

    # ── Gemini ──────────────────────────────────────────────────────────
    gemini_api_key: str = Field(
        ...,
        description="Google Gemini API key.  Required.",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model identifier.",
    )
    gemini_max_output_tokens: int = Field(
        default=8192,
        ge=256,
        le=65536,
        description="Maximum tokens the model may generate per response.",
    )
    gemini_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Sampling temperature — lower → more deterministic output.",
    )
    gemini_timeout_seconds: int = Field(
        default=120,
        ge=10,
        le=600,
        description="HTTP read timeout for Gemini API calls (seconds).",
    )

    # ── Chunking ────────────────────────────────────────────────────────
    max_diff_chars: int = Field(
        default=80_000,
        ge=1_000,
        description=(
            "Maximum characters in a diff before splitting into chunks. "
            "Gemini flash context window is ~1M tokens; 80 k chars ≈ 20 k tokens "
            "which leaves ample room for the system prompt and response."
        ),
    )
    chunk_overlap_lines: int = Field(
        default=10,
        ge=0,
        description="Lines of overlap between consecutive diff chunks.",
    )

    # ── Retry policy ────────────────────────────────────────────────────
    review_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts on transient API failures.",
    )
    review_retry_delay: float = Field(
        default=2.0,
        ge=0.5,
        description="Base delay (seconds) between retries; exponential back-off applied.",
    )

    # ── Application ─────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Root logging level.",
    )
    environment: str = Field(
        default="development",
        description="Deployment environment: development | staging | production.",
    )

    # ── GitHub Integration ──────────────────────────────────────────────
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token or App Installation token.",
    )
    github_api_url: str = Field(
        default="https://api.github.com",
        description="Base URL for the GitHub REST API.",
    )
    github_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=180,
        description="HTTP request timeout for GitHub API calls (seconds).",
    )

    # ── MongoDB Integration (Phase 7) ───────────────────────────────────
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string (URI).",
    )
    mongodb_database: str = Field(
        default="code_review_db",
        description="MongoDB database name for storing reviews and analytics.",
    )

    # ── Pydantic settings config ─────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Validators ──────────────────────────────────────────────────────

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Ensure log_level is a recognised Python logging level."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}; got {value!r}.")
        return upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Normalise the environment label to lowercase."""
        return value.lower().strip()

    @field_validator("gemini_api_key")
    @classmethod
    def validate_api_key_not_placeholder(cls, value: str) -> str:
        """Reject obvious placeholder values to fail fast in misconfigured deploys."""
        placeholders = {"your_api_key_here", "changeme", "xxx", "placeholder", ""}
        if value.strip().lower() in placeholders:
            raise ValueError(
                "GEMINI_API_KEY appears to be a placeholder.  "
                "Set a real Gemini API key in your .env file."
            )
        return value.strip()


# ---------------------------------------------------------------------------
# Singleton accessor — cached for the lifetime of the process
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Uses ``lru_cache`` to ensure the .env file is read exactly once.
    In tests, call ``get_settings.cache_clear()`` before overriding env vars.

    Returns:
        Fully validated ``Settings`` instance.
    """
    _settings = Settings()  # type: ignore[call-arg]
    logger.info(
        "Configuration loaded — environment=%s model=%s",
        _settings.environment,
        _settings.gemini_model,
    )
    return _settings


# Module-level convenience alias
settings: Settings = get_settings()
