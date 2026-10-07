"""
MedBrief AI — Gemini AI Gateway Tests
Step 8: Gemini AI Integration Foundation

Comprehensive test suite verifying:
1. Missing GEMINI_API_KEY behavior
2. Valid configuration initialization
3. Gemini client initialization & caching
4. Successful text generation
5. Successful structured JSON generation
6. Fenced markdown JSON handling
7. Invalid JSON response handling (AIInvalidResponseError)
8. Schema validation failure (AISchemaValidationError)
9. Request timeout handling (AITimeoutError)
10. Retry behavior on transient errors
11. Rate-limit quota exhaustion handling (AIRateLimitError)
12. Upstream provider 5xx error handling (AIProviderError)
13. Input-size constraint enforcement (AIInputTooLargeError)
14. Security assertion: API key never appears in logs, errors, or exceptions
15. Unauthenticated AI test endpoint rejection (HTTP 401)
16. Authenticated AI test endpoint execution (HTTP 200 with structured validation)
17. AI Health check endpoint behavior
"""

import logging
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel, Field
import httpx
from fastapi.testclient import TestClient

from google.genai import errors as genai_errors
from src.backend.main import app
from src.backend.ai.config import AIConfig, get_ai_config
from src.backend.ai.gateway import AIGateway, extract_json_payload
from src.backend.ai.prompts import PromptTemplate
from src.backend.ai.logging import sanitize_message
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

client = TestClient(app)


# Sample Pydantic model for structured test validation
class SampleClinicalAssessment(BaseModel):
    summary: str = Field(description="Summary text")
    confidence_score: float = Field(ge=0.0, le=1.0)
    requires_doctor_review: bool = True


@pytest.fixture
def doctor_token():
    """Login as seeded doctor and retrieve bearer token."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "MedBrief2026!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ── TEST 1: Missing GEMINI_API_KEY Behavior ──────────────────────────────────
def test_missing_api_key_raises_not_configured():
    config = AIConfig(api_key=None)
    gateway = AIGateway(config=config)

    assert gateway.health_check()["status"] == "unconfigured"
    assert gateway.health_check()["configured"] is False

    with pytest.raises(AINotConfiguredError) as exc_info:
        gateway.generate_text(prompt="Hello")

    assert exc_info.value.category == "AI_NOT_CONFIGURED"
    assert exc_info.value.status_code == 503


# ── TEST 2: Valid Configuration Initialization ────────────────────────────────
def test_valid_configuration():
    config = AIConfig(
        api_key="AIzaSyFakeTestKey1234567890abcdefghij",
        model="gemini-2.5-flash",
        max_input_chars=50000,
        max_output_tokens=2048,
        timeout_seconds=15.0,
        max_retries=2,
    )
    gateway = AIGateway(config=config)

    health = gateway.health_check()
    assert health["configured"] is True
    assert health["provider"] == "gemini"
    assert health["model"] == "gemini-2.5-flash"
    assert health["status"] == "ready"

    # API key is never exposed in model info
    info = gateway.get_model_info()
    assert "api_key" not in info
    assert info["configured"] is True
    assert info["max_input_chars"] == 50000


# ── TEST 3: Gemini Client Initialization & Caching ───────────────────────────
def test_client_caching():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij")
    gateway = AIGateway(config=config)

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai_client:
        mock_instance = MagicMock()
        mock_genai_client.return_value = mock_instance

        cli1 = gateway.client
        cli2 = gateway.client

        assert cli1 is cli2
        mock_genai_client.assert_called_once_with(api_key="AIzaSyFakeTestKey1234567890abcdefghij")


# ── TEST 4: Successful Text Generation ────────────────────────────────────────
def test_successful_text_generation():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij")
    gateway = AIGateway(config=config)

    mock_response = MagicMock()
    mock_response.text = "Patient displays sinus rhythm."
    mock_response.usage_metadata.prompt_token_count = 15
    mock_response.usage_metadata.candidates_token_count = 10
    mock_response.usage_metadata.total_token_count = 25

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_cli

        text, meta = gateway.generate_text(prompt="Analyze rhythm", user_id="doc-123")

        assert text == "Patient displays sinus rhythm."
        assert meta.success is True
        assert meta.provider == "gemini"
        assert meta.retry_count == 0
        assert meta.token_usage["total_tokens"] == 25
        assert meta.latency_ms >= 0


# ── TEST 5: Successful Structured Generation ─────────────────────────────────
def test_successful_structured_generation():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij")
    gateway = AIGateway(config=config)

    mock_response = MagicMock()
    mock_response.text = '{"summary": "Normal vitals recorded", "confidence_score": 0.95, "requires_doctor_review": true}'

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_cli

        result, meta = gateway.generate_structured(
            schema=SampleClinicalAssessment,
            prompt="Assess report",
        )

        assert isinstance(result, SampleClinicalAssessment)
        assert result.summary == "Normal vitals recorded"
        assert result.confidence_score == 0.95
        assert result.requires_doctor_review is True
        assert meta.structured_output_status == "PASSED"


# ── TEST 6: Fenced Markdown JSON Extraction ──────────────────────────────────
def test_fenced_markdown_json_extraction():
    fenced = "```json\n{\"summary\": \"Fenced data\", \"confidence_score\": 0.88, \"requires_doctor_review\": false}\n```"
    extracted = extract_json_payload(fenced)
    assert extracted.startswith("{")
    assert extracted.endswith("}")

    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij")
    gateway = AIGateway(config=config)

    mock_response = MagicMock()
    mock_response.text = fenced

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_cli

        result, meta = gateway.generate_structured(
            schema=SampleClinicalAssessment,
            prompt="Assess report",
        )
        assert result.summary == "Fenced data"
        assert meta.structured_output_status == "PASSED"


# ── TEST 7: Invalid JSON Response Handling ────────────────────────────────────
def test_invalid_json_raises_invalid_response_error():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij")
    gateway = AIGateway(config=config)

    mock_response = MagicMock()
    mock_response.text = "Here is the summary: {not valid json at all...}"

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_cli

        with pytest.raises(AIInvalidResponseError) as exc_info:
            gateway.generate_structured(
                schema=SampleClinicalAssessment,
                prompt="Assess report",
            )
        assert exc_info.value.category == "AI_INVALID_RESPONSE"


# ── TEST 8: Schema Validation Failure ─────────────────────────────────────────
def test_schema_validation_failure():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij")
    gateway = AIGateway(config=config)

    # Valid JSON, but missing required field 'summary' and invalid confidence_score (out of bounds > 1.0)
    mock_response = MagicMock()
    mock_response.text = '{"wrong_field": "test", "confidence_score": 5.0}'

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_cli

        with pytest.raises(AISchemaValidationError) as exc_info:
            gateway.generate_structured(
                schema=SampleClinicalAssessment,
                prompt="Assess report",
            )
        assert exc_info.value.category == "AI_SCHEMA_VALIDATION_ERROR"
        assert "errors" in exc_info.value.details


# ── TEST 9: Request Timeout Handling ──────────────────────────────────────────
def test_timeout_handling():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij", max_retries=1, retry_delay_seconds=0.01)
    gateway = AIGateway(config=config)

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.side_effect = httpx.TimeoutException("Read timed out")
        mock_genai.return_value = mock_cli

        with pytest.raises(AITimeoutError) as exc_info:
            gateway.generate_text(prompt="Timeout test")

        assert exc_info.value.category == "AI_TIMEOUT"
        assert exc_info.value.status_code == 504


# ── TEST 10: Retry Behavior on Transient Error ────────────────────────────────
def test_retry_on_transient_error_succeeds_on_second_attempt():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij", max_retries=2, retry_delay_seconds=0.01)
    gateway = AIGateway(config=config)

    mock_success = MagicMock()
    mock_success.text = "Recovered response after transient error"

    transient_error = genai_errors.APIError(code=503, response_json={"error": {"message": "Service unavailable"}})

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        # First attempt fails with 503, second attempt succeeds
        mock_cli.models.generate_content.side_effect = [transient_error, mock_success]
        mock_genai.return_value = mock_cli

        text, meta = gateway.generate_text(prompt="Retry test")
        assert text == "Recovered response after transient error"
        assert meta.retry_count == 1


# ── TEST 11: Rate-Limit Quota Exhaustion Handling ─────────────────────────────
def test_rate_limit_handling():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij", max_retries=0)
    gateway = AIGateway(config=config)

    rate_limit_err = genai_errors.APIError(code=429, response_json={"error": {"message": "Quota exceeded"}})

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.side_effect = rate_limit_err
        mock_genai.return_value = mock_cli

        with pytest.raises(AIRateLimitError) as exc_info:
            gateway.generate_text(prompt="Rate limit test")

        assert exc_info.value.category == "AI_RATE_LIMITED"
        assert exc_info.value.status_code == 429


# ── TEST 12: Upstream Provider 5xx Error Handling ─────────────────────────────
def test_provider_server_error_handling():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij", max_retries=0)
    gateway = AIGateway(config=config)

    server_err = genai_errors.APIError(code=500, response_json={"error": {"message": "Internal error"}})

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.side_effect = server_err
        mock_genai.return_value = mock_cli

        with pytest.raises(AIProviderError) as exc_info:
            gateway.generate_text(prompt="Server error test")

        assert exc_info.value.category == "AI_PROVIDER_ERROR"
        assert exc_info.value.status_code == 502


# ── TEST 13: Input Size Limit Rejection ───────────────────────────────────────
def test_input_size_rejection():
    config = AIConfig(api_key="AIzaSyFakeTestKey1234567890abcdefghij", max_input_chars=100)
    gateway = AIGateway(config=config)

    oversized_prompt = "A" * 150
    with pytest.raises(AIInputTooLargeError) as exc_info:
        gateway.generate_text(prompt=oversized_prompt)

    assert exc_info.value.category == "AI_INPUT_TOO_LARGE"
    assert exc_info.value.status_code == 413


# ── TEST 14: Security Assertion — API Key Never in Logs or Errors ────────────
def test_api_key_sanitization_in_logs():
    fake_key = "AIzaSyFakeTestKey1234567890abcdefghij"
    message_with_key = f"Provider rejected request with key {fake_key} and Bearer eyJhbGciOi.token.sig"

    sanitized = sanitize_message(message_with_key)
    assert fake_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_BEARER_TOKEN]" in sanitized


# ── TEST 15: Unauthenticated AI Test Endpoint Rejection ───────────────────────
def test_ai_test_endpoint_unauthenticated():
    res = client.post("/api/v1/ai/test", json={"custom_message": "Ping"})
    assert res.status_code == 401


# ── TEST 16: Authenticated AI Test Endpoint Execution ─────────────────────────
def test_ai_test_endpoint_authenticated(doctor_token):
    mock_response = MagicMock()
    mock_response.text = '{"status": "ok", "message": "Verification acknowledged", "echo_timestamp": "2026-10-06T12:00:00Z"}'

    with patch("src.backend.ai.gateway.genai.Client") as mock_genai:
        mock_cli = MagicMock()
        mock_cli.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_cli

        # Temporarily provide config key for test call
        with patch("src.backend.ai.gateway.ai_gateway.config.api_key", "AIzaSyFakeTestKey1234567890abcdefghij"):
            res = client.post(
                "/api/v1/ai/test",
                json={"custom_message": "Connectivity ping"},
                headers={"Authorization": f"Bearer {doctor_token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert "test_result" in data
            assert data["test_result"]["status"] == "ok"
            assert data["test_result"]["message"] == "Verification acknowledged"
            assert "metadata" in data
            assert data["metadata"]["structured_output_status"] == "PASSED"


# ── TEST 17: AI Health Check Endpoint ─────────────────────────────────────────
def test_ai_health_endpoint():
    res = client.get("/api/v1/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert data["provider"] == "gemini"
    assert "model" in data
    assert "status" in data
    # Crucial security check: api_key must never be returned in response
    assert "api_key" not in data
    assert "key" not in data
