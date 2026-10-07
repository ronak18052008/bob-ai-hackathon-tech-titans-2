"""
MedBrief AI — Domain Contracts & Architectural Schemas
Step 2: System Architecture

Pure Pydantic models defining the conceptual data contracts across the application.
No database or business logic is implemented here.
"""

from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


# ── Roles & User ─────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    ADMIN = "ADMIN"


class UserProfile(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    medical_license_id: Optional[str] = None
    created_at: datetime


# ── Patient Dossier ──────────────────────────────────────────────────────────

class PatientDemographics(BaseModel):
    id: uuid.UUID
    mrn: str = Field(..., description="Medical Record Number")
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    contact_phone: Optional[str] = None
    assigned_doctor_id: Optional[uuid.UUID] = None
    created_at: datetime


# ── Evidence Citation System ─────────────────────────────────────────────────

class EpistemicCategory(str, Enum):
    DOCUMENTED_FACT = "DOCUMENTED_FACT"
    AI_INTERPRETATION = "AI_INTERPRETATION"
    AI_SUGGESTION = "AI_SUGGESTION"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"


class EvidenceReference(BaseModel):
    document_id: uuid.UUID
    document_title: str
    page_number: int
    section: Optional[str] = None
    exact_snippet: str
    character_offset: Optional[List[int]] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    category: EpistemicCategory = EpistemicCategory.DOCUMENTED_FACT


# ── Document & Processing Job ────────────────────────────────────────────────

class DocumentType(str, Enum):
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    CLINIC_CONSULTATION = "CLINIC_CONSULTATION"
    LAB_PATHOLOGY = "LAB_PATHOLOGY"
    RADIOLOGY_REPORT = "RADIOLOGY_REPORT"
    PRESCRIPTION = "PRESCRIPTION"
    REFERRAL_LETTER = "REFERRAL_LETTER"
    OTHER = "OTHER"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class MedicalDocumentMeta(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    document_type: DocumentType
    page_count: int
    file_size_bytes: int
    checksum_sha256: str
    uploaded_at: datetime


class ProcessingJob(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: JobStatus
    progress_percentage: int = 0
    total_pages: int
    processed_pages: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Clinical Entities & Timeline ─────────────────────────────────────────────

class ClinicalEventType(str, Enum):
    CONSULTATION = "CONSULTATION"
    ADMISSION = "ADMISSION"
    DISCHARGE = "DISCHARGE"
    PROCEDURE = "PROCEDURE"
    DIAGNOSIS = "DIAGNOSIS"
    MEDICATION_CHANGE = "MEDICATION_CHANGE"
    INVESTIGATION_RESULT = "INVESTIGATION_RESULT"


class ClinicalEvent(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    event_type: ClinicalEventType
    event_date: Optional[datetime] = None
    approximate_date: Optional[str] = None
    title: str
    description: str
    is_conflict: bool = False
    conflict_notes: Optional[str] = None
    evidence: List[EvidenceReference] = []


# ── Medications ──────────────────────────────────────────────────────────────

class MedicationChangeType(str, Enum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    DOSE_INCREASED = "DOSE_INCREASED"
    DOSE_DECREASED = "DOSE_DECREASED"
    FREQUENCY_CHANGED = "FREQUENCY_CHANGED"
    SUBSTITUTED = "SUBSTITUTED"


class MedicationItem(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    drug_name: str
    dosage: str
    frequency: str
    route: str
    is_active: bool
    evidence: List[EvidenceReference] = []


class MedicationChangeRecord(BaseModel):
    id: uuid.UUID
    medication_id: uuid.UUID
    drug_name: str
    change_type: MedicationChangeType
    previous_dosage: Optional[str] = None
    new_dosage: Optional[str] = None
    reason: Optional[str] = None
    recorded_date: Optional[datetime] = None
    evidence: List[EvidenceReference] = []


# ── Diagnostic Investigations ────────────────────────────────────────────────

class InvestigationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    ORDERED_PENDING = "ORDERED_PENDING"
    RECOMMENDED_NEXT_STEP = "RECOMMENDED_NEXT_STEP"
    OVERDUE = "OVERDUE"


class InvestigationItem(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    test_name: str
    category: str  # Lab, Imaging, Pathology, Procedure
    status: InvestigationStatus
    result_value: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: Optional[bool] = None
    ordered_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    clinical_urgency: str = "NORMAL"  # LOW, NORMAL, HIGH, CRITICAL
    evidence: List[EvidenceReference] = []


# ── AI Clinical Summaries & Drafts ───────────────────────────────────────────

class SummaryMode(str, Enum):
    QUICK_BRIEF = "QUICK_BRIEF"
    DETAILED_SYSTEMIC = "DETAILED_SYSTEMIC"
    MEDICATION_FOCUSED = "MEDICATION_FOCUSED"
    INVESTIGATIONS_FOCUSED = "INVESTIGATIONS_FOCUSED"
    HANDOFF_SBAR = "HANDOFF_SBAR"


class ClinicalSummary(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    mode: SummaryMode
    generated_at: datetime
    content_markdown: str
    doctor_approved: bool = False
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    evidence_citations: List[EvidenceReference] = []


class DraftType(str, Enum):
    SPECIALIST_REFERRAL = "SPECIALIST_REFERRAL"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    CLINICAL_HANDOFF = "CLINICAL_HANDOFF"


class ClinicalDraft(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    draft_type: DraftType
    title: str
    ai_generated_body: str
    doctor_edited_body: Optional[str] = None
    is_signed_off: bool = False
    signed_by: Optional[uuid.UUID] = None
    signed_at: Optional[datetime] = None
    evidence_citations: List[EvidenceReference] = []


# ── Audit Trail ──────────────────────────────────────────────────────────────

class AuditAction(str, Enum):
    USER_LOGIN = "USER_LOGIN"
    PATIENT_VIEW = "PATIENT_VIEW"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_PROCESS = "DOCUMENT_PROCESS"
    SUMMARY_GENERATE = "SUMMARY_GENERATE"
    DRAFT_SIGN = "DRAFT_SIGN"


class AuditRecord(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    patient_id: Optional[uuid.UUID] = None
    action: AuditAction
    resource_type: str
    resource_id: str
    timestamp_utc: datetime
    metadata_json: Optional[Dict[str, Any]] = None
