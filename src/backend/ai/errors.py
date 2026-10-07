"""
MedBrief AI — Gemini AI Error Models
Step 8: Gemini AI Integration Foundation

Defines application-level AI exceptions and standardized error categories.
Ensures provider stack traces, API keys, or raw prompt contents never leak.
"""

from typing import Optional, Dict, Any


class AIGatewayError(Exception):
    """Base exception for all AI Gateway operations."""
    category: str = "AI_UNKNOWN_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        category: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        if category:
            self.category = category
        if status_code:
            self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Return safe error payload for client/log consumption."""
        return {
            "error_category": self.category,
            "message": self.message,
            "details": self.details,
        }


class AINotConfiguredError(AIGatewayError):
    """Raised when an AI operation is requested but GEMINI_API_KEY is missing."""
    category = "AI_NOT_CONFIGURED"
    status_code = 503

    def __init__(self, message: str = "Gemini AI service is not configured. GEMINI_API_KEY is missing."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AIAuthenticationError(AIGatewayError):
    """Raised when the provided Gemini API key is rejected by Google AI."""
    category = "AI_AUTHENTICATION_ERROR"
    status_code = 401

    def __init__(self, message: str = "Gemini AI authentication failed. Invalid API credentials."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AIRateLimitError(AIGatewayError):
    """Raised when the Gemini API returns HTTP 429 quota/rate limit exhaustion."""
    category = "AI_RATE_LIMITED"
    status_code = 429

    def __init__(self, message: str = "AI service quota or rate limit exceeded. Please retry shortly."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AITimeoutError(AIGatewayError):
    """Raised when an AI request exceeds the configured timeout threshold."""
    category = "AI_TIMEOUT"
    status_code = 504

    def __init__(self, message: str = "Gemini AI request timed out before receiving a response."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AIProviderError(AIGatewayError):
    """Raised when the upstream Gemini provider returns an unexpected 5xx or server fault."""
    category = "AI_PROVIDER_ERROR"
    status_code = 502

    def __init__(self, message: str = "Gemini AI provider encountered an internal service error."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AIInvalidResponseError(AIGatewayError):
    """Raised when Gemini returns an empty or unparseable response."""
    category = "AI_INVALID_RESPONSE"
    status_code = 502

    def __init__(self, message: str = "AI provider returned an invalid or empty response."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AISchemaValidationError(AIGatewayError):
    """Raised when structured JSON returned by Gemini fails Pydantic schema validation."""
    category = "AI_SCHEMA_VALIDATION_ERROR"
    status_code = 502

    def __init__(
        self,
        message: str = "AI-generated structured response failed schema validation.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, category=self.category, status_code=self.status_code, details=details)


class AIInputTooLargeError(AIGatewayError):
    """Raised when the prompt/input exceeds GEMINI_MAX_INPUT_CHARS."""
    category = "AI_INPUT_TOO_LARGE"
    status_code = 413

    def __init__(self, message: str = "Input prompt exceeds maximum allowed character limit."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)


class AINetworkError(AIGatewayError):
    """Raised on socket/DNS/connectivity failures communicating with Gemini."""
    category = "AI_NETWORK_ERROR"
    status_code = 503

    def __init__(self, message: str = "Network connectivity failure while communicating with Gemini AI."):
        super().__init__(message=message, category=self.category, status_code=self.status_code)
