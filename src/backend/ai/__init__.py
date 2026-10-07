"""
MedBrief AI — AI Gateway Package
Step 8: Gemini AI Integration Foundation
"""

from src.backend.ai.config import AIConfig, get_ai_config
from src.backend.ai.gateway import AIGateway, get_ai_gateway, extract_json_payload
from src.backend.ai.metadata import AIGenerationMetadata
from src.backend.ai.prompts import PromptTemplate, CLINICAL_SAFETY_PRINCIPLES
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

__all__ = [
    "AIConfig",
    "get_ai_config",
    "AIGateway",
    "get_ai_gateway",
    "extract_json_payload",
    "AIGenerationMetadata",
    "PromptTemplate",
    "CLINICAL_SAFETY_PRINCIPLES",
    "AIGatewayError",
    "AINotConfiguredError",
    "AIAuthenticationError",
    "AIRateLimitError",
    "AITimeoutError",
    "AIProviderError",
    "AIInvalidResponseError",
    "AISchemaValidationError",
    "AIInputTooLargeError",
    "AINetworkError",
    # Step 9: Extraction Exports
    "ExtractionService",
    "get_extraction_service",
    "ExtractedClinicalDossier",
    "ExtractedClinicalEvent",
    "ExtractedCondition",
    "ExtractedMedication",
    "ExtractedInvestigation",
    "ExtractedProcedure",
    "ExtractedFollowUp",
    "get_medical_extraction_template",
]

from src.backend.ai.extraction_service import ExtractionService, get_extraction_service
from src.backend.ai.extraction_schemas import (
    ExtractedClinicalDossier,
    ExtractedClinicalEvent,
    ExtractedCondition,
    ExtractedMedication,
    ExtractedInvestigation,
    ExtractedProcedure,
    ExtractedFollowUp,
)
from src.backend.ai.extraction_prompts import get_medical_extraction_template
