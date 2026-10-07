"""
MedBrief AI — Safe AI Logging & Sanitization
Step 8: Gemini AI Integration Foundation

Implements HIPAA/GDPR-compliant logging practices for AI operations:
- Strictly prohibits logging patient PHI, raw medical documents, or prompts
- Sanitizes and suppresses API keys, JWTs, and bearer tokens
- Emits structured metadata (request ID, model, duration, status, retries)
"""

import logging
import re
from typing import Optional, Dict, Any
from src.backend.ai.metadata import AIGenerationMetadata

logger = logging.getLogger("medbrief.ai")
logger.setLevel(logging.INFO)

# Patterns for sensitive tokens and API keys
API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z-_]{20,50}")
KEY_PARAM_PATTERN = re.compile(r"(?:api_key|api-key|key)=([^\s&'\"]+)", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*")


def sanitize_message(text: str) -> str:
    """Mask any potential API keys or authorization tokens from log text."""
    if not text:
        return text
    text = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)
    text = KEY_PARAM_PATTERN.sub("key=[REDACTED_API_KEY]", text)
    text = BEARER_PATTERN.sub("[REDACTED_BEARER_TOKEN]", text)
    return text


class SafeAILogger:
    """Safe, auditable logging interface for Gemini AI Gateway operations."""

    @staticmethod
    def log_operation_start(
        request_id: str,
        operation: str,
        model: str,
        input_char_count: int,
        user_id: Optional[str] = None,
    ) -> None:
        """Log execution dispatch without logging prompt or patient content."""
        logger.info(
            "AI_OPERATION_DISPATCHED [request_id=%s] op=%s model=%s input_chars=%d user_id=%s",
            request_id,
            operation,
            model,
            input_char_count,
            user_id or "system",
        )

    @staticmethod
    def log_operation_retry(
        request_id: str,
        attempt: int,
        max_retries: int,
        error_category: str,
        backoff_seconds: float,
    ) -> None:
        """Log transient retry event."""
        logger.warning(
            "AI_OPERATION_RETRY [request_id=%s] attempt=%d/%d category=%s backoff_sec=%.2f",
            request_id,
            attempt,
            max_retries,
            error_category,
            backoff_seconds,
        )

    @staticmethod
    def log_operation_success(metadata: AIGenerationMetadata) -> None:
        """Log successful execution with telemetry metadata."""
        logger.info(
            "AI_OPERATION_COMPLETED [request_id=%s] op=%s model=%s latency_ms=%.1f retries=%d structured=%s",
            metadata.request_id,
            metadata.operation,
            metadata.model,
            metadata.latency_ms,
            metadata.retry_count,
            metadata.structured_output_status,
        )

    @staticmethod
    def log_operation_failure(
        request_id: str,
        operation: str,
        model: str,
        error_category: str,
        error_message: str,
        latency_ms: float,
    ) -> None:
        """Log operation failure with sanitized error summary."""
        safe_msg = sanitize_message(error_message)
        logger.error(
            "AI_OPERATION_FAILED [request_id=%s] op=%s model=%s category=%s latency_ms=%.1f error=%s",
            request_id,
            operation,
            model,
            error_category,
            latency_ms,
            safe_msg,
        )
