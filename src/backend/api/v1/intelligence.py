"""
MedBrief AI — Medication & Investigation Intelligence API Router
Step 11: Medication + Investigation Intelligence

Provides REST endpoints for:
- Querying structured patient medications (GET /api/v1/patients/{patient_id}/medications)
- Querying medication changes and dose comparisons (GET /api/v1/patients/{patient_id}/medication-changes)
- Querying investigations with strict pending verification (GET /api/v1/patients/{patient_id}/investigations)
- Querying outstanding clinical items & follow-ups (GET /api/v1/patients/{patient_id}/outstanding-items)
- Aggregated clinical intelligence summary (GET /api/v1/patients/{patient_id}/intelligence/summary)
- Enforcing strict patient-level clinician authorization (can_user_access_patient)
- Zero PHI logging in audit events
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.backend.db.connection import get_db
from src.backend.db.models import Patient, User
from src.backend.auth.dependencies import (
    get_current_active_user,
    can_user_access_patient,
)
from src.backend.auth.security import log_auth_audit_event
from src.backend.intelligence.intelligence_service import (
    ClinicalIntelligenceService,
    get_intelligence_service,
)

router = APIRouter(prefix="/api/v1/patients", tags=["Medication & Investigation Intelligence"])


# ── Pydantic Response Schemas ──────────────────────────────────────────────────

class IntelligenceSourceReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: Optional[str] = None
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    page_id: Optional[str] = None
    page_number: Optional[int] = None
    source_snippet: Optional[str] = None
    source_section: Optional[str] = None


# 1. Medications Schemas
class MedicationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    medication_name: str
    generic_name: Optional[str] = None
    dosage: Optional[str] = None
    dose_unit: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    display_start_date: str
    display_end_date: Optional[str] = None
    source: IntelligenceSourceReference
    origin: str = "DOCUMENTED"
    is_conflict: bool = False
    conflict_details: Optional[str] = None
    changes_count: int = 0
    created_at: str


class MedicationSummaryStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_medications: int = 0
    active_count: int = 0
    stopped_count: int = 0
    historical_count: int = 0
    unknown_count: int = 0


class PatientMedicationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    summary: MedicationSummaryStats
    items: List[MedicationItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: Optional[str] = None


# 2. Medication Changes Schemas
class MedicationChangeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    medication_id: str
    medication_name: str
    generic_name: Optional[str] = None
    change_type: str
    change_type_label: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    change_date: Optional[str] = None
    display_date: str
    description: str
    reason: Optional[str] = None
    origin: str = "DOCUMENTED"
    is_conflict: bool = False
    conflict_details: Optional[str] = None
    is_ai_generated: bool = False
    source: IntelligenceSourceReference
    created_at: str


class MedicationChangeSummaryStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_changes: int = 0
    started_count: int = 0
    stopped_count: int = 0
    dose_changes_count: int = 0
    frequency_changes_count: int = 0
    route_changes_count: int = 0


class PatientMedicationChangesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    summary: MedicationChangeSummaryStats
    items: List[MedicationChangeItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: Optional[str] = None


# 3. Investigations Schemas
class InvestigationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    investigation_name: str
    investigation_type: str
    ordered_date: Optional[str] = None
    completed_date: Optional[str] = None
    display_date: str
    status: str
    result_summary: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: bool = False
    clinical_urgency: str
    origin: str = "DOCUMENTED"
    is_conflict: bool = False
    conflict_details: Optional[str] = None
    source: IntelligenceSourceReference
    created_at: str


class InvestigationSummaryStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_investigations: int = 0
    completed_count: int = 0
    pending_count: int = 0
    ordered_count: int = 0
    cancelled_count: int = 0
    unknown_count: int = 0
    abnormal_count: int = 0


class PatientInvestigationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    summary: InvestigationSummaryStats
    items: List[InvestigationItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: Optional[str] = None


# 4. Outstanding Items Schemas
class OutstandingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    item_type: str
    item_type_label: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    due_date: Optional[str] = None
    display_due_date: str
    origin: str = "DOCUMENTED"
    is_ai_generated: bool = False
    review_status: str
    source: IntelligenceSourceReference
    created_at: str


class OutstandingSummaryStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_outstanding: int = 0
    open_count: int = 0
    high_priority_count: int = 0
    type_counts: Dict[str, int] = {}


class PatientOutstandingItemsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    summary: OutstandingSummaryStats
    items: List[OutstandingItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: Optional[str] = None


# 5. Combined Intelligence Summary Schema
class PatientIntelligenceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    medications: Dict[str, Any]
    investigations: Dict[str, Any]
    outstanding_items: Dict[str, Any]


# ── Helper for Access Validation ───────────────────────────────────────────────

def _authorize_patient_access(
    current_user: User,
    patient_id: str,
    db: Session,
    resource_type: str,
) -> Patient:
    """Validate patient authorization and existence."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found in system.",
        )

    if not can_user_access_patient(current_user.id, patient_id, db):
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type=resource_type,
            resource_id=patient_id,
            metadata={"reason": f"Clinician not authorized for patient {resource_type}"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to access this patient's records.",
        )
    return patient


# ── REST Endpoints ─────────────────────────────────────────────────────────────

@router.get(
    "/{patient_id}/medications",
    response_model=PatientMedicationsResponse,
    summary="Get patient medications",
)
def get_patient_medications(
    patient_id: str,
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, STOPPED, HISTORICAL, UNKNOWN, ALL)"),
    search: Optional[str] = Query(None, description="Search drug name or generic name"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalIntelligenceService = Depends(get_intelligence_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_MEDICATIONS")

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_MEDICATIONS",
        resource_type="PATIENT_MEDICATIONS",
        resource_id=patient.id,
        metadata={"filter_status": status, "sort": sort},
    )

    result = service.get_patient_medications(
        db=db,
        patient_id=patient_id,
        status=status,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/{patient_id}/medication-changes",
    response_model=PatientMedicationChangesResponse,
    summary="Get patient medication changes & history comparisons",
)
def get_patient_medication_changes(
    patient_id: str,
    change_type: Optional[str] = Query(None, description="Filter by change type (STARTED, STOPPED, DOSE_CHANGED, etc.)"),
    date_from: Optional[str] = Query(None, description="Filter changes on or after date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter changes on or before date (YYYY-MM-DD)"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalIntelligenceService = Depends(get_intelligence_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_MEDICATION_CHANGES")

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_MEDICATION_CHANGES",
        resource_type="PATIENT_MEDICATION_CHANGES",
        resource_id=patient.id,
        metadata={"filter_type": change_type, "sort": sort},
    )

    result = service.get_patient_medication_changes(
        db=db,
        patient_id=patient_id,
        change_type=change_type,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/{patient_id}/investigations",
    response_model=PatientInvestigationsResponse,
    summary="Get patient diagnostic investigations",
)
def get_patient_investigations(
    patient_id: str,
    status: Optional[str] = Query(None, description="Filter by status (ORDERED, PENDING, COMPLETED, CANCELLED, UNKNOWN, ALL)"),
    investigation_type: Optional[str] = Query(None, description="Filter by type (LAB, IMAGING, PATHOLOGY, ALL)"),
    search: Optional[str] = Query(None, description="Search investigation name or result summary"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalIntelligenceService = Depends(get_intelligence_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_INVESTIGATIONS")

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_INVESTIGATIONS",
        resource_type="PATIENT_INVESTIGATIONS",
        resource_id=patient.id,
        metadata={"filter_status": status, "filter_type": investigation_type, "sort": sort},
    )

    result = service.get_patient_investigations(
        db=db,
        patient_id=patient_id,
        status=status,
        investigation_type=investigation_type,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/{patient_id}/outstanding-items",
    response_model=PatientOutstandingItemsResponse,
    summary="Get patient outstanding items & follow-ups",
)
def get_patient_outstanding_items(
    patient_id: str,
    item_type: Optional[str] = Query(None, description="Filter by type (PENDING_INVESTIGATION, FOLLOW_UP, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED, ALL)"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, NORMAL, HIGH, CRITICAL, ALL)"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalIntelligenceService = Depends(get_intelligence_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_OUTSTANDING_ITEMS")

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_OUTSTANDING_ITEMS",
        resource_type="PATIENT_OUTSTANDING_ITEMS",
        resource_id=patient.id,
        metadata={"filter_type": item_type, "filter_status": status, "filter_priority": priority},
    )

    result = service.get_patient_outstanding_items(
        db=db,
        patient_id=patient_id,
        item_type=item_type,
        status=status,
        priority=priority,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/{patient_id}/intelligence/summary",
    response_model=PatientIntelligenceSummaryResponse,
    summary="Get patient clinical intelligence overview summary",
)
def get_patient_intelligence_summary(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalIntelligenceService = Depends(get_intelligence_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_INTELLIGENCE_SUMMARY")

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_INTELLIGENCE_SUMMARY",
        resource_type="PATIENT_INTELLIGENCE_SUMMARY",
        resource_id=patient.id,
        metadata={"scope": "clinical_intelligence_overview"},
    )

    result = service.get_patient_intelligence_summary(db=db, patient_id=patient_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result
