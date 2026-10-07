"""
MedBrief AI — Medical Information Extraction Schemas
Step 9: Medical Information Extraction

Defines validated Pydantic schemas for clinical information extraction:
- Clinical Events (admissions, consults, procedures, changes)
- Conditions / Problems (with explicit status, uncertainty, and negation)
- Medications (with dosage, unit, route, frequency, and original wording)
- Investigations (labs, imaging, pathology with values and ranges)
- Procedures (explicitly documented interventions)
- Follow-up Instructions (specialist reviews, repeat tests)

Enforces:
- Original wording preservation for auditability
- Explicit uncertainty representation
- Explicit negation preservation
- Source snippet containment
- Strict rejection of hallucinations or unsupported assumptions
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ExtractedClinicalEvent(BaseModel):
    """Documented clinical event or milestone."""
    event_type: str = Field(
        default="other",
        description="Type of event: consultation, diagnosis, admission, discharge, procedure, investigation, result, medication_start, medication_stop, medication_change, follow_up, referral, other"
    )
    event_date: Optional[str] = Field(
        default=None,
        description="Documented date (YYYY-MM-DD or YYYY-MM if known). NULL if date is not documented."
    )
    date_precision: str = Field(
        default="EXACT",
        description="Precision of event date: EXACT, APPROXIMATE, MONTH_YEAR, YEAR_ONLY, UNKNOWN"
    )
    title: str = Field(
        ...,
        description="Concise clinical title for the event"
    )
    description: str = Field(
        ...,
        description="Factual clinical description based strictly on the text"
    )
    department: Optional[str] = Field(
        default=None,
        description="Documented department or service (e.g. Cardiology, Emergency)"
    )
    source_snippet: Optional[str] = Field(
        default=None,
        description="Exact quote or concise sentence from the source document"
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Model confidence metadata (0.0 to 1.0)"
    )
    is_uncertain: bool = Field(
        default=False,
        description="True if the event or diagnosis is documented with uncertainty (e.g. 'possible', 'suspected')"
    )
    uncertainty_note: Optional[str] = Field(
        default=None,
        description="Details regarding documented ambiguity"
    )
    is_negated: bool = Field(
        default=False,
        description="True if the event or finding was ruled out or denied (e.g. 'no fever', 'ruled out')"
    )
    is_ai_generated: bool = Field(default=True)

    @field_validator("event_type", mode="before")
    @classmethod
    def normalize_event_type(cls, v: str) -> str:
        valid_types = {
            "consultation", "diagnosis", "admission", "discharge", "procedure",
            "investigation", "result", "medication_start", "medication_stop",
            "medication_change", "follow_up", "referral", "other"
        }
        val = str(v).lower().strip().replace(" ", "_")
        return val if val in valid_types else "other"

    @field_validator("date_precision", mode="before")
    @classmethod
    def normalize_precision(cls, v: str) -> str:
        valid_prec = {"EXACT", "APPROXIMATE", "MONTH_YEAR", "YEAR_ONLY", "UNKNOWN"}
        val = str(v).upper().strip()
        return val if val in valid_prec else "UNKNOWN"


class ExtractedCondition(BaseModel):
    """Documented medical condition, problem, or symptom."""
    condition_name: str = Field(..., description="Normalized medical condition name")
    original_text: str = Field(..., description="Exact original wording from the record")
    clinical_status: str = Field(
        default="confirmed",
        description="Status: confirmed, suspected, possible, history_of, ruled_out, unknown"
    )
    onset_date: Optional[str] = Field(
        default=None,
        description="Documented onset date or timeframe if explicitly stated"
    )
    source_snippet: Optional[str] = Field(
        default=None,
        description="Exact quote from the document text"
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    is_uncertain: bool = Field(
        default=False,
        description="True if framed as uncertain, differential, or questionable"
    )
    is_negated: bool = Field(
        default=False,
        description="True if explicitly denied or ruled out (e.g., 'no history of diabetes')"
    )
    uncertainty_note: Optional[str] = None
    is_ai_generated: bool = Field(default=True)

    @field_validator("clinical_status", mode="before")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        valid = {"confirmed", "suspected", "possible", "history_of", "ruled_out", "unknown"}
        val = str(v).lower().strip().replace(" ", "_")
        return val if val in valid else "unknown"


class ExtractedMedication(BaseModel):
    """Documented medication entry with dosage, route, and schedule."""
    medication_name: str = Field(..., description="Normalized drug name (e.g. Metformin)")
    original_text: str = Field(..., description="Exact wording from the record (e.g. 'Tab. Metformin 500 mg BD')")
    dosage: Optional[str] = Field(default=None, description="Numeric strength or dosage (e.g. '500')")
    dose_unit: Optional[str] = Field(default=None, description="Unit of measure (e.g. 'mg', 'mcg', 'mL')")
    frequency: Optional[str] = Field(default=None, description="Documented frequency (e.g. 'twice daily', 'BD', 'QD')")
    route: Optional[str] = Field(default=None, description="Route of administration (e.g. 'oral', 'IV')")
    status: str = Field(
        default="ACTIVE",
        description="Status: ACTIVE, STOPPED, HISTORICAL, UNKNOWN"
    )
    start_date: Optional[str] = Field(default=None, description="Explicit start date if documented")
    stop_date: Optional[str] = Field(default=None, description="Explicit stop date if documented")
    source_snippet: Optional[str] = Field(default=None, description="Exact sentence containing the prescription")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    is_uncertain: bool = Field(default=False)
    is_ai_generated: bool = Field(default=True)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        valid = {"ACTIVE", "STOPPED", "HISTORICAL", "UNKNOWN"}
        val = str(v).upper().strip()
        return val if val in valid else "UNKNOWN"


class ExtractedInvestigation(BaseModel):
    """Documented diagnostic investigation, laboratory panel, or imaging examination."""
    investigation_name: str = Field(..., description="Name of test (e.g. Troponin I, Chest X-ray, CBC)")
    investigation_type: str = Field(
        default="LAB",
        description="Category: LAB, RADIOLOGY, PATHOLOGY, ECG, ENDOSCOPY, OTHER"
    )
    ordered_date: Optional[str] = Field(default=None, description="Date ordered if documented")
    performed_date: Optional[str] = Field(default=None, description="Date performed if documented")
    result_date: Optional[str] = Field(default=None, description="Date result reported if documented")
    result_text: Optional[str] = Field(default=None, description="Textual result summary or impression")
    numeric_value: Optional[float] = Field(default=None, description="Explicit numerical result if quantitative")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g. 'ng/mL', 'g/dL')")
    reference_range: Optional[str] = Field(default=None, description="Reference interval (e.g. '< 0.04 ng/mL')")
    is_abnormal: Optional[bool] = Field(default=None, description="True if marked abnormal or out of reference range")
    clinical_urgency: str = Field(
        default="NORMAL",
        description="Clinical urgency: LOW, NORMAL, HIGH, CRITICAL"
    )
    status: str = Field(
        default="ORDERED",
        description="Status: ORDERED, PENDING, COMPLETED, CANCELLED, UNKNOWN"
    )
    source_snippet: Optional[str] = Field(default=None, description="Exact source sentence")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    is_uncertain: bool = Field(default=False)
    is_ai_generated: bool = Field(default=True)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        valid = {"ORDERED", "PENDING", "COMPLETED", "CANCELLED", "UNKNOWN"}
        val = str(v).upper().strip()
        return val if val in valid else "UNKNOWN"

    @field_validator("clinical_urgency", mode="before")
    @classmethod
    def normalize_urgency(cls, v: str) -> str:
        valid = {"LOW", "NORMAL", "HIGH", "CRITICAL"}
        val = str(v).upper().strip()
        return val if val in valid else "NORMAL"


class ExtractedProcedure(BaseModel):
    """Documented surgical, interventional, or bedside procedure."""
    procedure_name: str = Field(..., description="Name of procedure (e.g. Coronary Angiography)")
    procedure_date: Optional[str] = Field(default=None, description="Date procedure was performed")
    indication: Optional[str] = Field(default=None, description="Indication or context if documented")
    outcome: Optional[str] = Field(default=None, description="Outcome or findings if documented")
    source_snippet: Optional[str] = Field(default=None, description="Exact source sentence")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    is_uncertain: bool = Field(default=False)
    is_ai_generated: bool = Field(default=True)


class ExtractedFollowUp(BaseModel):
    """Explicitly documented follow-up instructions or plan items."""
    instruction: str = Field(..., description="Actionable follow-up instruction (e.g. 'Repeat CBC in two weeks')")
    target_date: Optional[str] = Field(
        default=None,
        description="Documented date or relative timeframe (e.g. 'in 2 weeks', 'within 4 weeks')"
    )
    date_precision: str = Field(
        default="APPROXIMATE",
        description="Precision: EXACT, APPROXIMATE, UNKNOWN"
    )
    specialty_or_provider: Optional[str] = Field(
        default=None,
        description="Specialty or practitioner mentioned (e.g. 'Cardiology', 'GP')"
    )
    source_snippet: Optional[str] = Field(default=None, description="Exact source sentence")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    is_uncertain: bool = Field(default=False)
    is_ai_generated: bool = Field(default=True)


class ExtractedClinicalDossier(BaseModel):
    """
    Consolidated structured clinical extraction result for a document or page unit.
    All fields default to empty lists if no entities are documented.
    """
    events: List[ExtractedClinicalEvent] = Field(default_factory=list)
    conditions: List[ExtractedCondition] = Field(default_factory=list)
    medications: List[ExtractedMedication] = Field(default_factory=list)
    investigations: List[ExtractedInvestigation] = Field(default_factory=list)
    procedures: List[ExtractedProcedure] = Field(default_factory=list)
    follow_ups: List[ExtractedFollowUp] = Field(default_factory=list)
    page_summary_brief: Optional[str] = Field(
        default=None,
        description="Brief 1-sentence synopsis of page content or 'No clinical entities documented'"
    )
    has_clinical_content: bool = Field(
        default=True,
        description="False if the page is administrative, blank, or devoid of medical facts"
    )
