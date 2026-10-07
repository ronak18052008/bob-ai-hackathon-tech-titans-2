"""
MedBrief AI — Medical Information Extraction API Router
Step 9: Medical Information Extraction

Provides REST endpoints for:
- Triggering page-aware clinical extraction on an authorized document (POST /api/v1/documents/{id}/extract)
- Querying structured extraction dossiers, entity counts, and evidence snippets (GET /api/v1/documents/{id}/extraction)
- Strict patient-level clinician authorization enforcement (can_user_access_patient)
- Full idempotency: re-running replaces prior AI extractions safely
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.backend.db.connection import get_db
from src.backend.db.models import (
    Document,
    ProcessingJob,
    ClinicalEvent,
    Medication,
    Investigation,
    OutstandingItem,
    EvidenceReference,
    User,
)
from src.backend.auth.dependencies import (
    get_current_active_user,
    can_user_access_patient,
)
from src.backend.auth.security import log_auth_audit_event
from src.backend.ai.extraction_service import (
    ExtractionService,
    get_extraction_service,
)
from src.backend.ai.errors import AIGatewayError
from src.backend.ai.logging import SafeAILogger

router = APIRouter(tags=["Medical Information Extraction"])


# ── Pydantic Response Schemas ──────────────────────────────────────────────────

class ExtractionCountSummary(BaseModel):
    events: int = 0
    conditions: int = 0
    medications: int = 0
    investigations: int = 0
    procedures: int = 0
    follow_ups: int = 0
    total: int = 0


class EvidenceReferenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parent_entity_type: str
    parent_entity_id: str
    source_section: Optional[str] = None
    source_text: str
    source_type: str
    confidence: Optional[float] = None
    page_number: Optional[int] = None


class ExtractedEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    event_date: Optional[datetime] = None
    event_date_precision: str
    title: str
    description: str
    confidence: Optional[float] = None
    is_conflict: bool = False
    conflict_details: Optional[str] = None
    source_page_id: Optional[str] = None
    evidence_snippet: Optional[str] = None


class ExtractedMedicationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    medication_name: str
    generic_name: Optional[str] = None
    dosage: Optional[str] = None
    dose_unit: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    source_page_id: Optional[str] = None
    evidence_snippet: Optional[str] = None


class ExtractedInvestigationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    investigation_name: str
    investigation_type: str
    ordered_date: Optional[str] = None
    completed_date: Optional[str] = None
    status: str
    result_summary: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: Optional[bool] = None
    clinical_urgency: str
    source_page_id: Optional[str] = None
    evidence_snippet: Optional[str] = None


class ExtractedFollowUpItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_type: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    due_date: Optional[str] = None
    source_page_id: Optional[str] = None
    evidence_snippet: Optional[str] = None


class DocumentExtractionTriggerResponse(BaseModel):
    status: str
    message: str
    document_id: str
    patient_id: str
    job_id: str
    job_status: str
    processed_pages: int
    total_pages: int
    failed_pages: List[int] = Field(default_factory=list)
    extracted_counts: Dict[str, int]
    error_message: Optional[str] = None


class DocumentExtractionSummaryResponse(BaseModel):
    document_id: str
    patient_id: str
    document_status: str
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    job_progress: int = 0
    job_error: Optional[str] = None
    counts: ExtractionCountSummary
    events: List[ExtractedEventItem] = Field(default_factory=list)
    conditions: List[ExtractedEventItem] = Field(default_factory=list)
    procedures: List[ExtractedEventItem] = Field(default_factory=list)
    medications: List[ExtractedMedicationItem] = Field(default_factory=list)
    investigations: List[ExtractedInvestigationItem] = Field(default_factory=list)
    follow_ups: List[ExtractedFollowUpItem] = Field(default_factory=list)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/api/v1/documents/{document_id}/extract",
    response_model=DocumentExtractionTriggerResponse,
    summary="Trigger Medical Information Extraction for Document",
)
def trigger_document_extraction(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    extraction_service: ExtractionService = Depends(get_extraction_service),
):
    """
    Trigger page-aware medical entity extraction on an uploaded PDF record.
    - Strictly verifies patient assignment authorization for the clinician
    - Enforces idempotency (safely replaces prior AI extractions upon re-run)
    - Records audit log with zero PHI leakage
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical document not found.",
        )

    # Patient authorization enforcement
    has_access = can_user_access_patient(current_user.id, doc.patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="DOCUMENT",
            resource_id=document_id,
            metadata={"patient_id": doc.patient_id, "action": "trigger_extraction"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to process this patient's medical records.",
        )

    try:
        result = extraction_service.process_document_extraction(
            db=db,
            document=doc,
            user_id=str(current_user.id),
        )

        status_text = result["status"]
        if status_text == "PROCESSED":
            message = "Medical information extracted successfully."
        elif status_text == "PARTIAL":
            message = result.get("error_message") or f"Medical extraction completed with partial errors on page(s): {result.get('failed_pages', [])}."
        elif status_text == "FAILED":
            message = result.get("error_message") or "Medical extraction failed during AI parsing."
        else:
            message = f"Medical extraction finished with status: {status_text}"

        return DocumentExtractionTriggerResponse(
            status=result["status"],
            message=message,
            document_id=result["document_id"],
            patient_id=result["patient_id"],
            job_id=result["job_id"],
            job_status=result["job_status"],
            processed_pages=result["processed_pages"],
            total_pages=result["total_pages"],
            failed_pages=result.get("failed_pages", []),
            extracted_counts=result.get("extracted_counts", {}),
            error_message=result.get("error_message"),
        )

    except AIGatewayError as ai_err:
        SafeAILogger.log_operation_failure(
            request_id=f"doc_{doc.id}_extract_route",
            operation="route_trigger_document_extraction",
            model=extraction_service.gateway.config.model,
            error_category="AI_GATEWAY_ERROR",
            error_message=str(ai_err.message),
        )
        raise HTTPException(
            status_code=ai_err.status_code,
            detail=ai_err.to_dict(),
        ) from ai_err

    except Exception as exc:
        SafeAILogger.log_operation_failure(
            request_id=f"doc_{doc.id}_extract_route",
            operation="route_trigger_document_extraction",
            model=extraction_service.gateway.config.model,
            error_category="UNEXPECTED_EXTRACTION_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while extracting clinical information: {str(exc)}",
        ) from exc


@router.get(
    "/api/v1/documents/{document_id}/extraction",
    response_model=DocumentExtractionSummaryResponse,
    summary="Retrieve Extracted Clinical Information Dossier for Document",
)
def get_document_extraction(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve structured medical extraction records linked to this document:
    - Clinical Events, Diagnoses/Conditions, Procedures
    - Medications
    - Diagnostic Investigations / Labs
    - Outstanding Follow-up items
    - Page-level source snippets
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical document not found.",
        )

    has_access = can_user_access_patient(current_user.id, doc.patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="DOCUMENT",
            resource_id=document_id,
            metadata={"patient_id": doc.patient_id, "action": "get_extraction"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to view this patient's medical extractions.",
        )

    # 1. Processing job info
    latest_job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document_id)
        .order_by(desc(ProcessingJob.created_at))
        .first()
    )

    # 2. Evidence references index (parent_entity_id -> source_text)
    evidence_rows = (
        db.query(EvidenceReference)
        .filter(EvidenceReference.document_id == document_id)
        .all()
    )
    evidence_map: Dict[str, str] = {e.parent_entity_id: e.source_text for e in evidence_rows}

    # 3. Clinical events (all types for this document)
    raw_events = (
        db.query(ClinicalEvent)
        .filter(ClinicalEvent.source_document_id == document_id)
        .order_by(desc(ClinicalEvent.event_date))
        .all()
    )

    events_list: List[ExtractedEventItem] = []
    conditions_list: List[ExtractedEventItem] = []
    procedures_list: List[ExtractedEventItem] = []

    for ev in raw_events:
        item = ExtractedEventItem(
            id=ev.id,
            event_type=ev.event_type,
            event_date=ev.event_date,
            event_date_precision=ev.event_date_precision or "EXACT",
            title=ev.title,
            description=ev.description,
            confidence=ev.confidence,
            is_conflict=bool(ev.is_conflict),
            conflict_details=ev.conflict_details,
            source_page_id=ev.source_page_id,
            evidence_snippet=evidence_map.get(ev.id),
        )
        if ev.event_type == "diagnosis":
            conditions_list.append(item)
        elif ev.event_type == "procedure":
            procedures_list.append(item)
        else:
            events_list.append(item)

    # 4. Medications
    raw_meds = (
        db.query(Medication)
        .filter(Medication.source_document_id == document_id)
        .order_by(Medication.medication_name.asc())
        .all()
    )
    medications_list: List[ExtractedMedicationItem] = [
        ExtractedMedicationItem(
            id=m.id,
            medication_name=m.medication_name,
            generic_name=m.generic_name,
            dosage=m.dosage,
            dose_unit=m.dose_unit,
            route=m.route,
            frequency=m.frequency,
            status=m.status,
            start_date=m.start_date.isoformat() if m.start_date else None,
            end_date=m.end_date.isoformat() if m.end_date else None,
            source_page_id=m.source_page_id,
            evidence_snippet=evidence_map.get(m.id),
        )
        for m in raw_meds
    ]

    # 5. Investigations
    raw_invs = (
        db.query(Investigation)
        .filter(Investigation.source_document_id == document_id)
        .order_by(Investigation.investigation_name.asc())
        .all()
    )
    investigations_list: List[ExtractedInvestigationItem] = [
        ExtractedInvestigationItem(
            id=i.id,
            investigation_name=i.investigation_name,
            investigation_type=i.investigation_type,
            ordered_date=i.ordered_date.isoformat() if i.ordered_date else None,
            completed_date=i.completed_date.isoformat() if i.completed_date else None,
            status=i.status,
            result_summary=i.result_summary,
            reference_range=i.reference_range,
            is_abnormal=i.is_abnormal,
            clinical_urgency=i.clinical_urgency or "NORMAL",
            source_page_id=i.source_page_id,
            evidence_snippet=evidence_map.get(i.id),
        )
        for i in raw_invs
    ]

    # 6. Follow-up items
    raw_fus = (
        db.query(OutstandingItem)
        .filter(OutstandingItem.source_document_id == document_id)
        .order_by(OutstandingItem.due_date.asc().nulls_last())
        .all()
    )
    follow_ups_list: List[ExtractedFollowUpItem] = [
        ExtractedFollowUpItem(
            id=f.id,
            item_type=f.item_type,
            title=f.title,
            description=f.description,
            priority=f.priority or "NORMAL",
            status=f.status or "OPEN",
            due_date=f.due_date.isoformat() if f.due_date else None,
            source_page_id=f.source_page_id,
            evidence_snippet=evidence_map.get(f.id),
        )
        for f in raw_fus
    ]

    counts = ExtractionCountSummary(
        events=len(events_list),
        conditions=len(conditions_list),
        medications=len(medications_list),
        investigations=len(investigations_list),
        procedures=len(procedures_list),
        follow_ups=len(follow_ups_list),
        total=(
            len(events_list)
            + len(conditions_list)
            + len(medications_list)
            + len(investigations_list)
            + len(procedures_list)
            + len(follow_ups_list)
        ),
    )

    return DocumentExtractionSummaryResponse(
        document_id=doc.id,
        patient_id=doc.patient_id,
        document_status=doc.status,
        job_id=latest_job.id if latest_job else None,
        job_status=latest_job.status if latest_job else None,
        job_progress=latest_job.progress if latest_job else 0,
        job_error=latest_job.error_message if latest_job else None,
        counts=counts,
        events=events_list,
        conditions=conditions_list,
        procedures=procedures_list,
        medications=medications_list,
        investigations=investigations_list,
        follow_ups=follow_ups_list,
    )
