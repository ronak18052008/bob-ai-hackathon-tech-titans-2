"""
MedBrief AI — Gemini AI Configuration
Step 8: Gemini AI Integration Foundation

Centralized backend-only configuration for Google Gemini AI.
Ensures API keys are never exposed to clients, logs, or responses.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class AIConfig(BaseModel):
    """Configuration contract for Gemini AI gateway."""
    api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key (strictly backend-only, never logged or exposed)"
    )
    model: str = Field(
        default="gemini-2.5-flash",
        description="Default Gemini model identifier"
    )
    max_input_chars: int = Field(
        default=100_000,
        description="Maximum characters allowed in an input prompt to prevent token overflow"
    )
    max_output_tokens: int = Field(
        default=4096,
        description="Maximum response output tokens"
    )
    timeout_seconds: float = Field(
        default=30.0,
        description="Request timeout in seconds before aborting"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for transient errors"
    )
    retry_delay_seconds: float = Field(
        default=1.0,
        description="Initial delay in seconds for exponential backoff"
    )

    @property
    def is_configured(self) -> bool:
        """Return True if an API key is provided and non-empty."""
        return bool(self.api_key and self.api_key.strip())

    @property
    def safe_dict(self) -> dict:
        """Return safe representation of configuration without sensitive API keys."""
        return {
            "configured": self.is_configured,
            "provider": "gemini",
            "model": self.model,
            "max_input_chars": self.max_input_chars,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }


def get_ai_config() -> AIConfig:
    """
    Factory function to load AI configuration from environment variables.
    Provides safe defaults and does not crash when the key is not configured.
    """
    raw_key = os.getenv("GEMINI_API_KEY", "").strip()
    api_key = raw_key if raw_key else None

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not model:
        model = "gemini-2.5-flash"

    try:
        max_input_chars = int(os.getenv("GEMINI_MAX_INPUT_CHARS", "100000"))
    except ValueError:
        max_input_chars = 100_000

    try:
        max_output_tokens = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
    except ValueError:
        max_output_tokens = 4096

    try:
        timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30.0"))
    except ValueError:
        timeout_seconds = 30.0

    try:
        max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
    except ValueError:
        max_retries = 3

    return AIConfig(
        api_key=api_key,
        model=model,
        max_input_chars=max_input_chars,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
