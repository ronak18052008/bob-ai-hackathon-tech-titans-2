"""
MedBrief AI — Clinical Timeline API Router
Step 10: Clinical Timeline

Provides REST endpoints for:
- Querying a deterministic, chronological patient timeline (GET /api/v1/patients/{patient_id}/timeline)
- Querying a lightweight summary widget for the Patient Overview (GET /api/v1/patients/{patient_id}/timeline/summary)
- Enforcing strict patient-level clinician authorization (can_user_access_patient)
- Comprehensive filtering by event type, date range, search query, and sort direction
- Zero LLM calls — 100% deterministic timeline assembly from structured clinical data
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
from src.backend.timeline.timeline_service import (
    TimelineService,
    get_timeline_service,
)

router = APIRouter(prefix="/api/v1/patients", tags=["Clinical Timeline"])


# ── Pydantic Response Schemas ──────────────────────────────────────────────────

class TimelineSourceReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: Optional[str] = None
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    page_id: Optional[str] = None
    page_number: Optional[int] = None
    source_snippet: Optional[str] = None
    source_section: Optional[str] = None


class TimelineEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    event_type: str
    event_type_label: str
    event_type_icon: str
    badge_class: str
    event_date: Optional[str] = None
    display_date: str
    date_precision: str
    title: str
    description: str
    source: TimelineSourceReference
    confidence: Optional[float] = None
    is_conflict: bool = False
    conflict_details: Optional[str] = None
    is_ai_generated: bool = False
    review_status: str = "UNREVIEWED"
    created_at: str


class TimelinePeriodGroup(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_key: str
    year: int
    month_name: Optional[str] = None
    period_label: str
    event_count: int
    events: List[TimelineEventItem]


class TimelineSummaryStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_events: int = 0
    dated_events_count: int = 0
    undated_events_count: int = 0
    first_event_date: Optional[str] = None
    last_event_date: Optional[str] = None
    event_types: Dict[str, int] = {}


class PatientTimelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    summary: TimelineSummaryStats
    groups: List[TimelinePeriodGroup]
    undated_events: List[TimelineEventItem]
    items: List[TimelineEventItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    sort: str


class RecentTimelineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    event_type: str
    event_type_label: str
    event_type_icon: str
    display_date: str
    date_precision: str
    description: str


class PatientTimelineSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    patient_name: str
    patient_mrn: str
    total_events: int
    recent_events: List[RecentTimelineItem]


# ── REST Endpoints ─────────────────────────────────────────────────────────────

@router.get(
    "/{patient_id}/timeline",
    response_model=PatientTimelineResponse,
    summary="Get patient clinical timeline",
)
def get_patient_timeline(
    patient_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g. ALL, consultation, diagnosis, medication_start)"),
    date_from: Optional[str] = Query(None, description="Filter events on or after ISO date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter events on or before ISO date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Keyword search in event title or description"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order: desc (newest first) or asc (oldest first)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    timeline_svc: TimelineService = Depends(get_timeline_service),
):
    """
    Retrieve the chronological clinical timeline for an authorized patient.
    - Clinicians must have authorized relationship or administrator privileges.
    - Deterministic assembly from structured clinical data with strict date precision.
    - Dated events grouped by year/month; undated events clearly separated.
    - Full source traceability (document name, page number, verbatim snippet).
    """
    # 1. Authoritative access check
    if not can_user_access_patient(current_user.id, patient_id, db):
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_TIMELINE",
            resource_id=patient_id,
            metadata={"reason": "Clinician not authorized for this patient's timeline"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to access this patient's records.",
        )

    # 2. Patient existence verification
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found in system.",
        )

    # 3. Log audit event
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="TIMELINE_VIEW",
        resource_type="PATIENT_TIMELINE",
        resource_id=patient.id,
        metadata={
            "patient_mrn": patient.mrn,
            "filter_event_type": event_type,
            "sort": sort,
        },
    )

    # 4. Construct timeline deterministically
    result = timeline_svc.get_patient_timeline(
        db=db,
        patient_id=patient_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    return result


@router.get(
    "/{patient_id}/timeline/summary",
    response_model=PatientTimelineSummaryResponse,
    summary="Get patient clinical timeline summary widget data",
)
def get_patient_timeline_summary(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    timeline_svc: TimelineService = Depends(get_timeline_service),
):
    """
    Lightweight endpoint returning timeline statistics and the most recent 5 events
    for embedding directly inside the Patient Overview dashboard card.
    """
    # 1. Authoritative access check
    if not can_user_access_patient(current_user.id, patient_id, db):
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_TIMELINE_SUMMARY",
            resource_id=patient_id,
            metadata={"reason": "Clinician not authorized for this patient's timeline summary"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to access this patient's records.",
        )

    # 2. Patient existence verification
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found in system.",
        )

    # 3. Retrieve summary
    result = timeline_svc.get_patient_timeline_summary(db=db, patient_id=patient_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    return result
