"""
MedBrief AI — Clinical Draft Schemas
Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow

Defines strict Pydantic schemas for:
1. Gemini structured draft output generation across:
   - REFERRAL
   - DISCHARGE
   - HANDOFF
2. Evidence citations linking clinical assertions to source records
3. Structured sections and complete editable document body
4. API request and response DTOs with physician review and approval metadata
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DraftType(str, Enum):
    REFERRAL = "REFERRAL"
    DISCHARGE = "DISCHARGE"
    HANDOFF = "HANDOFF"


class DraftStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class DraftEvidenceCitation(BaseModel):
    """
    Direct citation pointing to a verifiable patient document and page.
    Every factual claim generated in the draft must resolve to genuine source evidence.
    """
    model_config = ConfigDict(from_attributes=True)

    document_id: Optional[str] = Field(
        default=None,
        description="UUID of the source document in the database.",
    )
    document_name: Optional[str] = Field(
        default=None,
        description="Filename of the source document.",
    )
    page_number: Optional[int] = Field(
        default=None,
        description="1-based page number where the clinical fact was documented.",
    )
    document_page_id: Optional[str] = Field(
        default=None,
        description="UUID of the specific document_page record if available.",
    )
    source_snippet: str = Field(
        ...,
        description="Exact quote from the medical record supporting this claim.",
    )
    source_section: Optional[str] = Field(
        default=None,
        description="Section where the fact was located (e.g. 'Discharge Plan', 'Current Medications').",
    )


class DraftStatement(BaseModel):
    """
    An individual clinical assertion with source citations and uncertainty flags.
    """
    model_config = ConfigDict(from_attributes=True)

    statement: str = Field(
        ...,
        description="Clinical statement synthesized strictly from documented patient data.",
    )
    citations: List[DraftEvidenceCitation] = Field(
        default_factory=list,
        description="List of document citations directly grounding this statement.",
    )
    is_uncertain: bool = Field(
        default=False,
        description="True if the documented fact has conflicting sources, is suspected, or lacks verifiable evidence.",
    )
    uncertainty_note: Optional[str] = Field(
        default=None,
        description="Explanation of why this fact is uncertain or conflicting.",
    )


class StructuredDraftSection(BaseModel):
    """
    A modular clinical section within the draft (e.g. Reason for Referral, Medication Changes, Follow-up).
    """
    model_config = ConfigDict(from_attributes=True)

    section_key: str = Field(
        ...,
        description="Unique programmatic identifier (e.g. 'reason_for_referral', 'clinical_course', 'medications').",
    )
    title: str = Field(
        ...,
        description="Human-readable section title (e.g. 'Reason for Referral', 'Discharge Medications').",
    )
    content_text: Optional[str] = Field(
        default=None,
        description="Narrative text for this section.",
    )
    bullet_points: List[DraftStatement] = Field(
        default_factory=list,
        description="Grounded clinical bullet points with evidence citations.",
    )


class StructuredClinicalDraftOutput(BaseModel):
    """
    Complete structured clinical draft output produced by Gemini and validated by Pydantic.
    """
    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(
        ...,
        description="UUID of the patient.",
    )
    patient_name: Optional[str] = Field(
        default=None,
        description="Full name of the patient.",
    )
    draft_type: str = Field(
        ...,
        description="Type of draft: REFERRAL, DISCHARGE, or HANDOFF.",
    )
    title: str = Field(
        ...,
        description="Descriptive clinical document title.",
    )
    document_body: str = Field(
        ...,
        description="Cohesive formatted clinical document text ready for clinician editing and sign-off.",
    )
    sections: List[StructuredDraftSection] = Field(
        default_factory=list,
        description="Structured sections composing the draft document.",
    )
    overall_evidence_count: int = Field(
        default=0,
        description="Total count of verifiable evidence citations in the draft.",
    )
    has_insufficient_data: bool = Field(
        default=False,
        description="True if the uploaded record did not contain enough clinical information.",
    )
    clinical_notes: Optional[str] = Field(
        default=None,
        description="Safety provenance notes or instructions for the reviewing physician.",
    )


# ── REST API DTOs ─────────────────────────────────────────────────────────────

class DraftGenerateRequest(BaseModel):
    draft_type: DraftType = Field(
        default=DraftType.REFERRAL,
        description="Type of clinical document draft to generate (REFERRAL, DISCHARGE, HANDOFF).",
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional clinician instructions (e.g. 'Referral to Dr. Miller for coronary angiography').",
    )
    recipient_info: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional recipient clinician, department, or facility name.",
    )


class DraftUpdateRequest(BaseModel):
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated document title.",
    )
    content: Optional[str] = Field(
        default=None,
        description="Updated clinical document content edited by the doctor.",
    )
    status: Optional[DraftStatus] = Field(
        default=None,
        description="Updated review status (DRAFT, IN_REVIEW, APPROVED, ARCHIVED).",
    )


class DraftItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    draft_type: str
    draft_type_label: str
    title: str
    status: str
    is_ai_generated: bool
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    evidence_count: int = 0
    created_at: str
    updated_at: str


class DraftEvidenceReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    document_id: str
    document_name: Optional[str] = None
    document_page_id: Optional[str] = None
    page_number: Optional[int] = None
    parent_entity_type: str
    parent_entity_id: str
    source_section: Optional[str] = None
    source_text: str
    source_type: str
    confidence: Optional[float] = 1.0
    created_at: str


class DraftDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    patient_name: str
    patient_mrn: str
    draft_type: str
    draft_type_label: str
    title: str
    content: str
    structured_sections: List[StructuredDraftSection]
    evidence_references: List[DraftEvidenceReferenceResponse]
    status: str
    is_ai_generated: bool
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    created_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str
    updated_at: str


class PatientDraftsListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    items: List[DraftItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
