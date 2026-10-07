"""
MedBrief AI — AI Generation Metadata Contract
Step 8: Gemini AI Integration Foundation

Captures operational telemetry, latency, token consumption, and auditing markers
without logging or persisting sensitive patient PHI or prompt bodies.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AIGenerationMetadata(BaseModel):
    """Safe, auditable metadata for Gemini AI inference operations."""
    provider: str = Field(default="gemini", description="AI service provider")
    model: str = Field(..., description="Gemini model utilized for the operation")
    request_id: str = Field(..., description="Unique operation trace ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO-8601 execution timestamp"
    )
    operation: str = Field(..., description="Operation identifier (e.g., generate_text, generate_structured)")
    latency_ms: float = Field(..., description="Round-trip latency in milliseconds")
    success: bool = Field(..., description="Whether the operation completed successfully")
    retry_count: int = Field(default=0, description="Number of retry attempts required")
    structured_output_status: str = Field(
        default="NOT_APPLICABLE",
        description="Structured validation verdict (PASSED, FAILED, NOT_APPLICABLE)"
    )
    token_usage: Optional[Dict[str, int]] = Field(
        default=None,
        description="Token metrics if reported by Gemini API (prompt_tokens, candidates_tokens, total_tokens)"
    )
    error_category: Optional[str] = Field(
        default=None,
        description="Standardized error category if operation failed"
    )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return safe dictionary representation for logging and API telemetry."""
        return self.model_dump()
