"""
MedBrief AI — Gemini AI Gateway Abstraction
Step 8: Gemini AI Integration Foundation

Provides a secure, reusable AI Gateway that isolates the Google Gemini SDK
from the rest of the application.

Features:
- Centralized Gemini client reuse
- Configurable models, input/output limits, and timeouts
- Guaranteed backend-only execution (API keys never exposed)
- Structured JSON generation with strict Pydantic validation
- Controlled retries with exponential backoff on transient errors
- HIPAA/GDPR-compliant safe logging and telemetry metadata
- Graceful health check and error mapping
"""

import json
import re
import time
import uuid
from typing import Optional, Type, TypeVar, Any, Tuple
from pydantic import BaseModel, ValidationError
import httpx

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from src.backend.ai.config import AIConfig, get_ai_config
from src.backend.ai.errors import (
    AIGatewayError,
    AINotConfiguredError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIProviderError,
    AIInvalidResponseError,
    AISchemaValidationError,
    AIInputTooLargeError,
    AINetworkError,
)
from src.backend.ai.metadata import AIGenerationMetadata
from src.backend.ai.logging import SafeAILogger

T = TypeVar("T", bound=BaseModel)


def extract_json_payload(raw_text: str) -> str:
    """
    Safely extract JSON string from raw model text, stripping markdown fences if present.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    return text


class AIGateway:
    """
    Reusable Gemini AI Gateway service.
    Designed for dependency injection and singleton usage across backend endpoints and workers.
    """

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or get_ai_config()
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        """
        Lazily initialize and cache the Gemini client.
        Raises AINotConfiguredError if GEMINI_API_KEY is missing.
        """
        if not self.config.is_configured:
            raise AINotConfiguredError()

        if self._client is None:
            self._client = genai.Client(api_key=self.config.api_key)

        return self._client

    def health_check(self) -> dict:
        """
        Safe health check returning service readiness.
        Strictly never exposes the Gemini API key.
        """
        is_ready = self.config.is_configured
        return {
            "configured": is_ready,
            "provider": "gemini",
            "model": self.config.model,
            "status": "ready" if is_ready else "unconfigured",
        }

    def get_model_info(self) -> dict:
        """Return safe model configuration metadata."""
        return self.config.safe_dict

    def _validate_input_length(self, prompt: str) -> None:
        """Validate input character limit before transmission."""
        if len(prompt) > self.config.max_input_chars:
            raise AIInputTooLargeError(
                f"Prompt character length ({len(prompt)}) exceeds maximum limit "
                f"({self.config.max_input_chars} characters)."
            )

    def _map_exception(self, exc: Exception) -> AIGatewayError:
        """Map raw provider and network exceptions to standardized AIGatewayError subclasses."""
        if isinstance(exc, AIGatewayError):
            return exc

        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return AITimeoutError()

        if isinstance(exc, (httpx.NetworkError, httpx.ConnectError, ConnectionError)):
            return AINetworkError(f"Network error communicating with Gemini API: {type(exc).__name__}")

        if isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None)
            msg = getattr(exc, "message", str(exc))

            if code == 429 or "quota" in msg.lower() or "429" in msg:
                return AIRateLimitError()
            if code in (401, 403) or "api key" in msg.lower() or "unauthenticated" in msg.lower():
                return AIAuthenticationError()
            if code in (408, 504) or "deadline" in msg.lower() or "timeout" in msg.lower():
                return AITimeoutError()
            if code and code >= 500:
                return AIProviderError(f"Gemini upstream server error (HTTP {code}).")

            return AIProviderError(f"Gemini API error (code={code}): {msg}")

        return AIProviderError(f"Unexpected error communicating with AI provider: {type(exc).__name__}")

    def _is_retryable(self, error: AIGatewayError) -> bool:
        """Determine if an error category is transient and safe to retry."""
        return error.category in (
            "AI_RATE_LIMITED",
            "AI_TIMEOUT",
            "AI_PROVIDER_ERROR",
            "AI_NETWORK_ERROR",
        )

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        operation: str = "generate_text",
    ) -> Tuple[str, AIGenerationMetadata]:
        """
        Execute text generation with safe logging, timeout, and bounded retries.
        """
        self._validate_input_length(prompt)
        target_model = model or self.config.model
        request_id = str(uuid.uuid4())
        max_tokens = max_output_tokens or self.config.max_output_tokens

        SafeAILogger.log_operation_start(
            request_id=request_id,
            operation=operation,
            model=target_model,
            input_char_count=len(prompt),
            user_id=user_id,
        )

        start_time = time.time()
        last_error: Optional[AIGatewayError] = None
        retries = 0

        config_args: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "http_options": types.HttpOptions(timeout=self.config.timeout_seconds),
        }
        if system_instruction:
            config_args["system_instruction"] = system_instruction

        gen_config = types.GenerateContentConfig(**config_args)

        for attempt in range(self.config.max_retries + 1):
            try:
                # Ensure client is available (checks GEMINI_API_KEY)
                cli = self.client

                response = cli.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=gen_config,
                )

                output_text = getattr(response, "text", None)
                if output_text is None:
                    raise AIInvalidResponseError("Gemini response did not contain text content.")

                latency_ms = (time.time() - start_time) * 1000

                # Extract token usage if available
                token_usage = None
                usage = getattr(response, "usage_metadata", None)
                if usage:
                    token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                        "candidates_tokens": getattr(usage, "candidates_token_count", 0),
                        "total_tokens": getattr(usage, "total_token_count", 0),
                    }

                metadata = AIGenerationMetadata(
                    provider="gemini",
                    model=target_model,
                    request_id=request_id,
                    operation=operation,
                    latency_ms=latency_ms,
                    success=True,
                    retry_count=retries,
                    structured_output_status="NOT_APPLICABLE",
                    token_usage=token_usage,
                )

                SafeAILogger.log_operation_success(metadata)
                return output_text, metadata

            except Exception as exc:
                mapped = self._map_exception(exc)
                last_error = mapped

                if attempt < self.config.max_retries and self._is_retryable(mapped):
                    retries += 1
                    backoff = self.config.retry_delay_seconds * (2 ** attempt)
                    SafeAILogger.log_operation_retry(
                        request_id=request_id,
                        attempt=attempt + 1,
                        max_retries=self.config.max_retries,
                        error_category=mapped.category,
                        backoff_seconds=backoff,
                    )
                    time.sleep(backoff)
                else:
                    break

        latency_ms = (time.time() - start_time) * 1000
        SafeAILogger.log_operation_failure(
            request_id=request_id,
            operation=operation,
            model=target_model,
            error_category=last_error.category if last_error else "AI_UNKNOWN_ERROR",
            error_message=str(last_error) if last_error else "Unknown error",
            latency_ms=latency_ms,
        )

        assert last_error is not None
        raise last_error

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        operation: str = "generate_structured",
    ) -> Tuple[T, AIGenerationMetadata]:
        """
        Execute structured JSON generation with schema validation against a Pydantic model.
        Guarantees the output matches the required schema or raises AISchemaValidationError.
        """
        self._validate_input_length(prompt)
        target_model = model or self.config.model
        request_id = str(uuid.uuid4())
        max_tokens = max_output_tokens or self.config.max_output_tokens

        SafeAILogger.log_operation_start(
            request_id=request_id,
            operation=operation,
            model=target_model,
            input_char_count=len(prompt),
            user_id=user_id,
        )

        start_time = time.time()
        last_error: Optional[AIGatewayError] = None
        retries = 0

        config_args: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
            "http_options": types.HttpOptions(timeout=self.config.timeout_seconds),
        }
        if system_instruction:
            config_args["system_instruction"] = system_instruction

        # Attempt to pass response_schema for native structured constraint
        try:
            config_args["response_schema"] = schema
            gen_config = types.GenerateContentConfig(**config_args)
        except Exception:
            # Fallback to response_mime_type="application/json" without native schema parameter
            config_args.pop("response_schema", None)
            gen_config = types.GenerateContentConfig(**config_args)

        for attempt in range(self.config.max_retries + 1):
            try:
                cli = self.client

                response = cli.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=gen_config,
                )

                raw_text = getattr(response, "text", None)
                if not raw_text or not raw_text.strip():
                    raise AIInvalidResponseError("Gemini returned an empty response for structured output.")

                # Extract and parse JSON
                clean_json = extract_json_payload(raw_text)
                try:
                    parsed_dict = json.loads(clean_json)
                except json.JSONDecodeError as json_err:
                    raise AIInvalidResponseError(
                        f"Response could not be parsed as valid JSON: {str(json_err)}"
                    ) from json_err

                # Validate against target Pydantic schema
                try:
                    validated_obj = schema.model_validate(parsed_dict)
                except ValidationError as val_err:
                    raise AISchemaValidationError(
                        message=f"Model output failed schema validation for {schema.__name__}.",
                        details={"errors": val_err.errors(include_url=False)},
                    ) from val_err

                latency_ms = (time.time() - start_time) * 1000

                token_usage = None
                usage = getattr(response, "usage_metadata", None)
                if usage:
                    token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                        "candidates_tokens": getattr(usage, "candidates_token_count", 0),
                        "total_tokens": getattr(usage, "total_token_count", 0),
                    }

                metadata = AIGenerationMetadata(
                    provider="gemini",
                    model=target_model,
                    request_id=request_id,
                    operation=operation,
                    latency_ms=latency_ms,
                    success=True,
                    retry_count=retries,
                    structured_output_status="PASSED",
                    token_usage=token_usage,
                )

                SafeAILogger.log_operation_success(metadata)
                return validated_obj, metadata

            except Exception as exc:
                mapped = self._map_exception(exc)
                last_error = mapped

                if attempt < self.config.max_retries and self._is_retryable(mapped):
                    retries += 1
                    backoff = self.config.retry_delay_seconds * (2 ** attempt)
                    SafeAILogger.log_operation_retry(
                        request_id=request_id,
                        attempt=attempt + 1,
                        max_retries=self.config.max_retries,
                        error_category=mapped.category,
                        backoff_seconds=backoff,
                    )
                    time.sleep(backoff)
                else:
                    break

        latency_ms = (time.time() - start_time) * 1000
        SafeAILogger.log_operation_failure(
            request_id=request_id,
            operation=operation,
            model=target_model,
            error_category=last_error.category if last_error else "AI_UNKNOWN_ERROR",
            error_message=str(last_error) if last_error else "Unknown error",
            latency_ms=latency_ms,
        )

        assert last_error is not None
        raise last_error


# Singleton default gateway instance
ai_gateway = AIGateway()


def get_ai_gateway() -> AIGateway:
    """Dependency provider for FastAPI route injection."""
    return ai_gateway
