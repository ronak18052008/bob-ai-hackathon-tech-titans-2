"""
MedBrief AI — AI Clinical Summary API Router
Step 12: AI Clinical Summary + Evidence/Source Reference Layer

Provides REST endpoints for:
- POST /api/v1/patients/{patient_id}/summaries — Generate AI clinical summary with evidence grounding
- GET /api/v1/patients/{patient_id}/summaries — List patient summaries with pagination and type filtering
- GET /api/v1/summaries/{summary_id} — Retrieve full summary details and backed evidence references
- Enforces strict patient-level clinician authorization (can_user_access_patient)
- Zero PHI logging in audit events
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.backend.db.connection import get_db
from src.backend.db.models import Patient, User, Summary, EvidenceReference, Document, DocumentPage
from src.backend.auth.dependencies import (
    get_current_active_user,
    can_user_access_patient,
)
from src.backend.auth.security import log_auth_audit_event
from src.backend.ai.summary_schemas import (
    SummaryType,
    SummaryStatus,
    SummaryGenerateRequest,
    SummaryItemResponse,
    SummaryDetailResponse,
    PatientSummariesListResponse,
    EvidenceReferenceResponse,
    StructuredClinicalSummaryOutput,
)
from src.backend.ai.summary_service import (
    ClinicalSummaryService,
    get_summary_service,
)
from src.backend.ai.errors import (
    AIGatewayError,
    AIRateLimitError,
    AIAuthenticationError,
    AITimeoutError,
)

router = APIRouter(tags=["AI Clinical Summary & Evidence"])


def _authorize_patient_access(
    current_user: User,
    patient_id: str,
    db: Session,
    resource_type: str = "PATIENT_SUMMARY",
) -> Patient:
    """
    Common authorization helper ensuring patient exists and clinician is authorized.
    Raises 404 if patient not found, 403 if clinician lacks assignment/permission.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
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


def _build_summary_detail_response(
    summary: Summary,
    patient: Patient,
    evidence_refs: List[EvidenceReference],
    db: Session,
) -> SummaryDetailResponse:
    """Construct full detail response including parsed structured content and resolved evidence metadata."""
    # Parse structured content
    try:
        content_dict = json.loads(summary.content)
        structured_content = StructuredClinicalSummaryOutput.model_validate(content_dict)
    except Exception:
        structured_content = StructuredClinicalSummaryOutput(
            patient_id=patient.id,
            patient_name=f"{patient.first_name} {patient.last_name}".strip(),
            summary_type=summary.summary_type,
            title=summary.title,
            overview=summary.content or "",
            sections=[],
            overall_evidence_count=len(evidence_refs),
        )

    # Preload document names and page numbers for evidence refs
    doc_ids = list({e.document_id for e in evidence_refs if e.document_id})
    doc_map = {}
    if doc_ids:
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_map = {d.id: d for d in docs}

    page_ids = list({e.document_page_id for e in evidence_refs if e.document_page_id})
    page_map = {}
    if page_ids:
        pages = db.query(DocumentPage).filter(DocumentPage.id.in_(page_ids)).all()
        page_map = {p.id: p for p in pages}

    evidence_items = []
    for ref in evidence_refs:
        doc = doc_map.get(ref.document_id)
        page = page_map.get(ref.document_page_id) if ref.document_page_id else None

        evidence_items.append(
            EvidenceReferenceResponse(
                id=ref.id,
                patient_id=ref.patient_id,
                document_id=ref.document_id,
                document_name=doc.file_name if doc else None,
                document_page_id=ref.document_page_id,
                page_number=page.page_number if page else None,
                parent_entity_type=ref.parent_entity_type,
                parent_entity_id=ref.parent_entity_id,
                source_section=ref.source_section,
                source_text=ref.source_text,
                source_type=ref.source_type,
                confidence=ref.confidence,
                created_at=ref.created_at.isoformat() if ref.created_at else "",
            )
        )

    return SummaryDetailResponse(
        id=summary.id,
        patient_id=patient.id,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        patient_mrn=patient.mrn or "UNASSIGNED",
        summary_type=summary.summary_type,
        summary_type_label=summary.summary_type.replace("_", " ").title(),
        title=summary.title,
        overview=structured_content.overview,
        structured_content=structured_content,
        evidence_references=evidence_items,
        status=summary.status,
        is_ai_generated=summary.is_ai_generated,
        model_name=summary.model_name,
        model_version=summary.model_version,
        created_at=summary.created_at.isoformat() if summary.created_at else "",
        updated_at=summary.updated_at.isoformat() if summary.updated_at else "",
    )


# ── 1. GENERATE SUMMARY ───────────────────────────────────────────────────────

@router.post(
    "/api/v1/patients/{patient_id}/summaries",
    response_model=SummaryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI clinical summary with evidence grounding",
)
def generate_patient_summary(
    patient_id: str,
    payload: SummaryGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalSummaryService = Depends(get_summary_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_SUMMARY")

    try:
        summary = service.generate_summary(
            db=db,
            patient_id=patient_id,
            summary_type=payload.summary_type.value,
            user_id=current_user.id,
            custom_instructions=payload.custom_instructions,
        )
    except AIRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI Gateway rate limit exceeded. Please try again shortly.",
        ) from exc
    except AIAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service authentication error. Check server configuration.",
        ) from exc
    except AITimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI Gateway generation timed out.",
        ) from exc
    except AIGatewayError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Gateway error: {str(exc)}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate clinical summary: {str(exc)}",
        ) from exc

    # Zero-PHI audit logging
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="GENERATE_PATIENT_SUMMARY",
        resource_type="PATIENT_SUMMARY",
        resource_id=summary.id,
        metadata={
            "summary_type": payload.summary_type.value,
            "has_custom_instructions": bool(payload.custom_instructions),
        },
    )

    evidence_refs = service.get_summary_evidence(db, summary.id)
    return _build_summary_detail_response(summary, patient, evidence_refs, db)


# ── 2. LIST PATIENT SUMMARIES ─────────────────────────────────────────────────

@router.get(
    "/api/v1/patients/{patient_id}/summaries",
    response_model=PatientSummariesListResponse,
    summary="List patient clinical summaries",
)
def list_patient_summaries(
    patient_id: str,
    summary_type: Optional[str] = Query(None, description="Filter by summary type (QUICK_CLINICAL, DETAILED_CLINICAL, etc.)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (DRAFT, GENERATED, REVIEWED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalSummaryService = Depends(get_summary_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_SUMMARY")

    result = service.list_patient_summaries(
        db=db,
        patient_id=patient_id,
        summary_type=summary_type,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_SUMMARIES",
        resource_type="PATIENT_SUMMARY",
        resource_id=patient.id,
        metadata={
            "filter_type": summary_type,
            "filter_status": status_filter,
            "page": page,
        },
    )

    return PatientSummariesListResponse(
        patient_id=patient.id,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        patient_mrn=patient.mrn or "UNASSIGNED",
        items=[SummaryItemResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


# ── 3. GET SUMMARY DETAIL ─────────────────────────────────────────────────────

@router.get(
    "/api/v1/summaries/{summary_id}",
    response_model=SummaryDetailResponse,
    summary="Get clinical summary details and backed evidence references",
)
def get_summary_detail(
    summary_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalSummaryService = Depends(get_summary_service),
):
    summary = service.get_summary_by_id(db, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical summary with ID {summary_id} not found.",
        )

    patient = _authorize_patient_access(current_user, summary.patient_id, db, "PATIENT_SUMMARY")
    evidence_refs = service.get_summary_evidence(db, summary.id)

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_SUMMARY_DETAIL",
        resource_type="PATIENT_SUMMARY",
        resource_id=summary.id,
        metadata={"summary_type": summary.summary_type},
    )

    return _build_summary_detail_response(summary, patient, evidence_refs, db)
