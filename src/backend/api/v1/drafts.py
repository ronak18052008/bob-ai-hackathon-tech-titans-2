"""
MedBrief AI — Clinical Draft API Router
Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow

Provides REST endpoints for:
- POST /api/v1/patients/{patient_id}/drafts — Generate AI clinical draft with evidence grounding
- GET /api/v1/patients/{patient_id}/drafts — List patient drafts with pagination and type filtering
- GET /api/v1/drafts/{draft_id} — Retrieve full draft details and backed evidence references
- PATCH /api/v1/drafts/{draft_id} — Edit draft content, title, or review status (DRAFT -> IN_REVIEW -> APPROVED)
- Enforces strict patient-level clinician authorization (can_user_access_patient)
- Zero PHI logging in audit events
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.backend.db.connection import get_db
from src.backend.db.models import Patient, User, Draft, EvidenceReference, Document, DocumentPage
from src.backend.auth.dependencies import (
    get_current_active_user,
    can_user_access_patient,
)
from src.backend.auth.security import log_auth_audit_event
from src.backend.ai.draft_schemas import (
    DraftType,
    DraftStatus,
    DraftGenerateRequest,
    DraftUpdateRequest,
    DraftItemResponse,
    DraftDetailResponse,
    PatientDraftsListResponse,
    DraftEvidenceReferenceResponse,
    StructuredDraftSection,
)
from src.backend.ai.draft_service import (
    ClinicalDraftService,
    get_draft_service,
)
from src.backend.ai.errors import (
    AIGatewayError,
    AIRateLimitError,
    AIAuthenticationError,
    AITimeoutError,
)

router = APIRouter(tags=["Clinical Drafts & Document Composers"])


def _authorize_patient_access(
    current_user: User,
    patient_id: str,
    db: Session,
    resource_type: str = "PATIENT_DRAFT",
) -> Patient:
    """
    Authorization helper ensuring patient exists and clinician has access.
    Raises 404 if patient not found, 403 if clinician lacks authorization.
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


def _build_draft_detail_response(
    draft: Draft,
    patient: Patient,
    evidence_refs: List[EvidenceReference],
    db: Session,
) -> DraftDetailResponse:
    """Construct full detail response including parsed structured content and resolved evidence metadata."""
    # Parse content
    document_body = ""
    sections: List[StructuredDraftSection] = []

    try:
        content_dict = json.loads(draft.content)
        if isinstance(content_dict, dict):
            document_body = content_dict.get("document_body", "")
            raw_sections = content_dict.get("sections", [])
            sections = [StructuredDraftSection.model_validate(s) for s in raw_sections]
        else:
            document_body = str(draft.content or "")
    except Exception:
        document_body = draft.content or ""

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
            DraftEvidenceReferenceResponse(
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

    return DraftDetailResponse(
        id=draft.id,
        patient_id=patient.id,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        patient_mrn=patient.mrn or "UNASSIGNED",
        draft_type=draft.draft_type,
        draft_type_label=draft.draft_type.replace("_", " ").title(),
        title=draft.title,
        content=document_body,
        structured_sections=sections,
        evidence_references=evidence_items,
        status=draft.status,
        is_ai_generated=draft.is_ai_generated,
        model_name=draft.model_name,
        model_version=draft.model_version,
        created_by=draft.created_by,
        reviewed_by=draft.reviewed_by,
        reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        created_at=draft.created_at.isoformat() if draft.created_at else "",
        updated_at=draft.updated_at.isoformat() if draft.updated_at else "",
    )


# ── 1. GENERATE DRAFT ─────────────────────────────────────────────────────────

@router.post(
    "/api/v1/patients/{patient_id}/drafts",
    response_model=DraftDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI clinical draft with evidence grounding",
)
def generate_patient_draft(
    patient_id: str,
    payload: DraftGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalDraftService = Depends(get_draft_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_DRAFT")

    try:
        draft = service.generate_draft(
            db=db,
            patient_id=patient_id,
            draft_type=payload.draft_type.value,
            user_id=current_user.id,
            custom_instructions=payload.custom_instructions,
            recipient_info=payload.recipient_info,
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
            detail="AI Gateway draft generation timed out.",
        ) from exc
    except AIGatewayError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Gateway error: {str(exc)}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate clinical draft: {str(exc)}",
        ) from exc

    # Zero-PHI audit logging
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="GENERATE_PATIENT_DRAFT",
        resource_type="PATIENT_DRAFT",
        resource_id=draft.id,
        metadata={
            "draft_type": payload.draft_type.value,
            "has_custom_instructions": bool(payload.custom_instructions),
            "has_recipient_info": bool(payload.recipient_info),
        },
    )

    evidence_refs = service.get_draft_evidence(db, draft.id)
    return _build_draft_detail_response(draft, patient, evidence_refs, db)


# ── 2. LIST PATIENT DRAFTS ───────────────────────────────────────────────────

@router.get(
    "/api/v1/patients/{patient_id}/drafts",
    response_model=PatientDraftsListResponse,
    summary="List patient clinical drafts",
)
def list_patient_drafts(
    patient_id: str,
    draft_type: Optional[str] = Query(None, description="Filter by draft type (REFERRAL, DISCHARGE, HANDOFF)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (DRAFT, IN_REVIEW, APPROVED, ARCHIVED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalDraftService = Depends(get_draft_service),
):
    patient = _authorize_patient_access(current_user, patient_id, db, "PATIENT_DRAFT")

    result = service.list_patient_drafts(
        db=db,
        patient_id=patient_id,
        draft_type=draft_type,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_PATIENT_DRAFTS",
        resource_type="PATIENT_DRAFT",
        resource_id=patient.id,
        metadata={
            "filter_type": draft_type,
            "filter_status": status_filter,
            "page": page,
        },
    )

    return PatientDraftsListResponse(
        patient_id=patient.id,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        patient_mrn=patient.mrn or "UNASSIGNED",
        items=[DraftItemResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


# ── 3. GET DRAFT DETAIL ───────────────────────────────────────────────────────

@router.get(
    "/api/v1/drafts/{draft_id}",
    response_model=DraftDetailResponse,
    summary="Get clinical draft details and backed evidence references",
)
def get_draft_detail(
    draft_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalDraftService = Depends(get_draft_service),
):
    draft = service.get_draft_by_id(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical draft with ID {draft_id} not found.",
        )

    patient = _authorize_patient_access(current_user, draft.patient_id, db, "PATIENT_DRAFT")
    evidence_refs = service.get_draft_evidence(db, draft.id)

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="VIEW_DRAFT_DETAIL",
        resource_type="PATIENT_DRAFT",
        resource_id=draft.id,
        metadata={"draft_type": draft.draft_type},
    )

    return _build_draft_detail_response(draft, patient, evidence_refs, db)


# ── 4. PATCH / UPDATE DRAFT (Editable Draft Workflow) ─────────────────────────

@router.patch(
    "/api/v1/drafts/{draft_id}",
    response_model=DraftDetailResponse,
    summary="Edit clinical draft content, title, or review status",
)
def update_draft(
    draft_id: str,
    payload: DraftUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: ClinicalDraftService = Depends(get_draft_service),
):
    draft = service.get_draft_by_id(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical draft with ID {draft_id} not found.",
        )

    patient = _authorize_patient_access(current_user, draft.patient_id, db, "PATIENT_DRAFT")

    updated_draft = service.update_draft(
        db=db,
        draft_id=draft_id,
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        status=payload.status.value if payload.status else None,
    )

    is_approved = payload.status == DraftStatus.APPROVED
    audit_action = "APPROVE_DRAFT" if is_approved else "UPDATE_DRAFT"

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action=audit_action,
        resource_type="PATIENT_DRAFT",
        resource_id=draft.id,
        metadata={
            "draft_type": updated_draft.draft_type,
            "status": updated_draft.status,
            "is_approved": is_approved,
        },
    )

    evidence_refs = service.get_draft_evidence(db, updated_draft.id)
    return _build_draft_detail_response(updated_draft, patient, evidence_refs, db)
