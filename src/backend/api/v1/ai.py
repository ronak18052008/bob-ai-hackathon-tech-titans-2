"""
MedBrief AI — Gemini AI Endpoints
Step 8: Gemini AI Integration Foundation

Exposes:
- GET /api/v1/ai/health: Backend AI readiness and configuration status (never leaks keys)
- POST /api/v1/ai/test: Authenticated, non-medical end-to-end integration test
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.backend.auth.dependencies import get_current_active_user
from src.backend.db.models import User
from src.backend.ai.gateway import get_ai_gateway, AIGateway
from src.backend.ai.errors import AIGatewayError
from src.backend.ai.prompts import PromptTemplate

router = APIRouter(prefix="/api/v1/ai", tags=["AI Gateway"])


class AITestOutput(BaseModel):
    """Structured test schema for non-medical connectivity verification."""
    status: str = Field(description="Health status indicator, e.g. 'ok'")
    message: str = Field(description="Test greeting message from the AI model")
    echo_timestamp: Optional[str] = Field(default=None, description="Timestamp echoed by model")


class AITestRequest(BaseModel):
    """Optional customization for test prompt."""
    custom_message: Optional[str] = Field(
        default=None,
        description="Optional brief test message to echo (must be non-medical)"
    )


@router.get("/health", summary="Gemini AI Health & Configuration Check")
def check_ai_health(
    gateway: AIGateway = Depends(get_ai_gateway),
) -> Dict[str, Any]:
    """
    Returns AI service availability and model configuration.
    Strictly never exposes the Gemini API key or credentials.
    """
    return gateway.health_check()


@router.get("/info", summary="Gemini Model Information")
def get_ai_model_info(
    gateway: AIGateway = Depends(get_ai_gateway),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Returns non-sensitive model operational parameters (authenticated users only).
    """
    return gateway.get_model_info()


@router.post("/test", summary="Controlled Authenticated AI Integration Test")
def test_ai_connectivity(
    request: Optional[AITestRequest] = None,
    current_user: User = Depends(get_current_active_user),
    gateway: AIGateway = Depends(get_ai_gateway),
) -> Dict[str, Any]:
    """
    Executes a controlled test prompt through the AI Gateway.
    - Requires authenticated clinician or administrator session
    - Strictly non-medical test data only
    - Validates structured JSON response parsing
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    client_msg = request.custom_message if request and request.custom_message else "MedBrief AI verification ping"

    template = PromptTemplate(
        system_instruction=(
            "You are an automated backend health verification responder for MedBrief AI. "
            "Output strictly valid JSON conforming to the requested schema. No conversational preamble."
        ),
        task_instruction=(
            "Acknowledge the test verification ping with status 'ok' and a brief greeting message. "
            "Echo the provided timestamp in 'echo_timestamp'."
        ),
        structured_output_requirements="Schema: {\"status\": \"ok\", \"message\": string, \"echo_timestamp\": string}",
        safety_rules="Do NOT reference or invent any medical or patient records. This is a synthetic infrastructure ping.",
    )

    prompt = template.render(
        context_input=f"Verification Message: {client_msg}\nTimestamp: {now_iso}"
    )

    try:
        validated_result, metadata = gateway.generate_structured(
            schema=AITestOutput,
            prompt=prompt,
            system_instruction=template.system_instruction,
            user_id=str(current_user.id),
            operation="ai_test_ping",
        )
        return {
            "test_result": validated_result.model_dump(),
            "metadata": metadata.to_safe_dict(),
        }
    except AIGatewayError as err:
        raise HTTPException(
            status_code=err.status_code,
            detail=err.to_dict(),
        ) from err
