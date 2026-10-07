"""
MedBrief AI — Document Ingestion & Management API Router
Step 7: PDF / Medical Document Upload & Ingestion Foundation

Provides REST endpoints for:
- Uploading PDF medical records associated with authorized patient dossiers
- File validation (PDF format, magic bytes %PDF-, configurable size limits, duplicate detection)
- Secure, private storage foundation with path traversal prevention
- Document metadata retrieval and listing (scoped to authorized clinicians)
- Controlled, authenticated streaming for document preview/download
- Processing job initialization (QUEUED status establishing Step 8 pipeline foundation)
- Safe failure and retry handling
- Authoritative audit event logging (DOCUMENT_UPLOAD, DOCUMENT_VIEW, PROCESSING_RETRY)
"""

import os
import io
import math
import hashlib
from datetime import datetime
from typing import List, Optional
import pypdf
from pydantic import BaseModel, Field, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from src.backend.db.connection import get_db
from src.backend.db.models import (
    Document,
    DocumentPage,
    ProcessingJob,
    Patient,
    PatientUserAccess,
    User,
    generate_uuid,
    utc_now,
)
from src.backend.auth.dependencies import (
    get_current_user,
    can_user_access_patient,
)
from src.backend.auth.security import log_auth_audit_event
from src.backend.storage.document_storage import (
    store_document_bytes,
    get_safe_absolute_path,
    delete_stored_document,
    sanitize_filename,
)

router = APIRouter(tags=["Document Management"])

ALLOWED_DOC_TYPES = {
    "DISCHARGE_SUMMARY",
    "CLINIC_CONSULTATION",
    "LAB_PATHOLOGY",
    "RADIOLOGY_REPORT",
    "PRESCRIPTION",
    "REFERRAL_LETTER",
    "OTHER",
}


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploader_name: Optional[str] = None
    file_name: str
    file_type: str
    document_type: str
    file_size: int
    page_count: int
    checksum_sha256: Optional[str] = None
    status: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    job_progress: Optional[int] = 0
    job_error: Optional[str] = None


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentRetryResponse(BaseModel):
    status: str
    message: str
    document: DocumentResponse


# ── Helper Functions ─────────────────────────────────────────────────────────

def _enrich_document_response(doc: Document, db: Session) -> DocumentResponse:
    """Helper to attach patient demographics, uploader name, and latest job status."""
    # 1. Patient info
    p = db.query(Patient.first_name, Patient.last_name, Patient.mrn).filter(Patient.id == doc.patient_id).first()
    p_name = f"{p[0]} {p[1]}" if p else None
    p_mrn = p[2] if p else None

    # 2. Uploader info
    u_name = None
    if doc.uploaded_by:
        u = db.query(User.display_name).filter(User.id == doc.uploaded_by).first()
        u_name = u[0] if u else None

    # 3. Latest processing job
    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == doc.id)
        .order_by(desc(ProcessingJob.created_at))
        .first()
    )

    return DocumentResponse(
        id=doc.id,
        patient_id=doc.patient_id,
        patient_name=p_name,
        patient_mrn=p_mrn,
        uploaded_by=doc.uploaded_by,
        uploader_name=u_name,
        file_name=doc.file_name,
        file_type=doc.file_type,
        document_type=doc.document_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        checksum_sha256=doc.checksum_sha256,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        job_id=job.id if job else None,
        job_status=job.status if job else "QUEUED",
        job_progress=job.progress if job else 0,
        job_error=job.error_message if job else None,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/api/v1/patients/{patient_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_patient_document(
    patient_id: str,
    file: UploadFile = File(..., description="PDF medical record file"),
    document_type: str = Form("DISCHARGE_SUMMARY", description="Classification of medical document"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a medical record PDF document for an authorized patient.
    - Validates clinician access to the patient record
    - Enforces strict PDF MIME and magic byte verification (%PDF-)
    - Enforces configurable MAX_DOCUMENT_SIZE_MB file size limits
    - Detects accidental duplicate uploads for the same patient
    - Stores file in private filesystem storage
    - Records document metadata and queues a processing job (foundation for Step 8)
    - Records an authoritative DOCUMENT_UPLOAD audit event
    """
    # 1. Server-Side Patient Access Authorization
    has_access = can_user_access_patient(current_user.id, patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_RECORD",
            resource_id=patient_id,
            metadata={"reason": "Unauthorized document upload attempt"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to upload documents for this patient.",
        )

    # 2. Verify Patient Existence
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target patient record not found in system.",
        )

    # 3. Filename & Format Validation
    orig_name = file.filename or "medical_record.pdf"
    if not orig_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: Only PDF medical records (.pdf) are supported in this release.",
        )

    clean_filename = sanitize_filename(orig_name)
    norm_doc_type = document_type.strip().upper()
    if norm_doc_type not in ALLOWED_DOC_TYPES:
        norm_doc_type = "OTHER"

    # 4. Read Content & Size Validation
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read the uploaded file stream.",
        )

    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes). Please select a valid medical document.",
        )

    max_mb = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "25"))
    max_bytes = max_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"This file is larger than the allowed limit ({max_mb} MB).",
        )

    # 5. Magic Bytes Header Check
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid medical record: File header is not a valid PDF document.",
        )

    # 6. Checksum & Duplicate Detection
    sha256_hash = hashlib.sha256(content).hexdigest()

    duplicate = (
        db.query(Document)
        .filter(
            Document.patient_id == patient_id,
            or_(
                Document.checksum_sha256 == sha256_hash,
                and_(Document.file_name == clean_filename, Document.file_size == file_size)
            )
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate detected: An identical document ('{clean_filename}') is already on file for this patient.",
        )

    # 7. Extract Page Count Safely
    page_count = 1
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        page_count = max(len(reader.pages), 1)
    except Exception as e:
        # Non-fatal page count fallback
        print(f"[WARN] Failed to parse PDF page count with pypdf: {e}")
        page_count = 1

    # 8. Persist to Secure Storage
    doc_id = generate_uuid()
    try:
        rel_storage_path = store_document_bytes(patient_id, doc_id, content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document in secure filesystem storage.",
        )

    # 9. Database Transaction
    try:
        document = Document(
            id=doc_id,
            patient_id=patient_id,
            uploaded_by=current_user.id,
            file_name=clean_filename,
            file_type="application/pdf",
            storage_path=rel_storage_path,
            document_type=norm_doc_type,
            file_size=file_size,
            page_count=page_count,
            checksum_sha256=sha256_hash,
            status="UPLOADED",
            uploaded_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(document)
        db.flush()

        # Step 7 Ingestion Job Foundation (Queued for Step 8 AI Pipeline)
        job = ProcessingJob(
            id=generate_uuid(),
            document_id=document.id,
            job_type="FULL_DOCUMENT_PROCESSING",
            status="QUEUED",
            progress=0,
            total_pages=page_count,
            processed_pages=0,
            retry_count=0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(job)

        # Audit Event Logging (NO PHI or content logged)
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="DOCUMENT_UPLOAD",
            resource_type="DOCUMENT",
            resource_id=document.id,
            metadata={
                "patient_id": patient_id,
                "file_name": document.file_name,
                "file_size": document.file_size,
                "page_count": document.page_count,
                "document_type": document.document_type,
            },
        )

        db.commit()
        db.refresh(document)
    except Exception as e:
        db.rollback()
        # Clean up stored file to prevent orphaned files
        delete_stored_document(rel_storage_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed while registering document metadata.",
        )

    return _enrich_document_response(document, db)


@router.get("/api/v1/patients/{patient_id}/documents", response_model=List[DocumentResponse])
def list_patient_documents(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all medical documents uploaded for a specific patient.
    Enforces server-side clinician patient authorization.
    """
    has_access = can_user_access_patient(current_user.id, patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_RECORD",
            resource_id=patient_id,
            metadata={"reason": "Unauthorized document list request"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to view documents for this patient.",
        )

    docs = (
        db.query(Document)
        .filter(Document.patient_id == patient_id)
        .order_by(desc(Document.uploaded_at))
        .all()
    )

    return [_enrich_document_response(d, db) for d in docs]


@router.get("/api/v1/documents", response_model=DocumentListResponse)
def list_all_documents(
    patient_id: Optional[str] = Query(None, description="Optional patient filter"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by filename or patient MRN"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Global documents directory filtered to authorized patient records.
    - Clinicians only view documents for patients they are assigned to.
    - Administrators can view all documents across the facility.
    """
    user_roles = getattr(current_user, "roles_list", [])
    is_admin = "admin" in user_roles

    if is_admin:
        query = db.query(Document)
    else:
        query = (
            db.query(Document)
            .join(PatientUserAccess, Document.patient_id == PatientUserAccess.patient_id)
            .filter(PatientUserAccess.user_id == current_user.id)
        )

    if patient_id:
        query = query.filter(Document.patient_id == patient_id)

    if document_type:
        query = query.filter(Document.document_type == document_type.strip().upper())

    if status_filter:
        query = query.filter(Document.status == status_filter.strip().upper())

    if search:
        s = f"%{search.strip().lower()}%"
        # Search filename or join patient for MRN/name
        query = query.join(Patient, Document.patient_id == Patient.id).filter(
            or_(
                func.lower(Document.file_name).like(s),
                func.lower(Patient.mrn).like(s),
                func.lower(Patient.first_name).like(s),
                func.lower(Patient.last_name).like(s),
            )
        )

    total_count = query.count()
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    docs = (
        query.order_by(desc(Document.uploaded_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return DocumentListResponse(
        items=[_enrich_document_response(d, db) for d in docs],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/api/v1/documents/{document_id}", response_model=DocumentResponse)
def get_document_details(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve document metadata, file statistics, and ingestion job status.
    Enforces server-side clinician patient authorization.
    Logs DOCUMENT_VIEW audit event.
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
            metadata={"patient_id": doc.patient_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to view this document.",
        )

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="DOCUMENT_VIEW",
        resource_type="DOCUMENT",
        resource_id=doc.id,
        metadata={"patient_id": doc.patient_id, "file_name": doc.file_name},
    )

    return _enrich_document_response(doc, db)


@router.get("/api/v1/documents/{document_id}/file")
def stream_document_file(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Controlled, authenticated PDF file streaming for browser preview and download.
    Strictly verifies user access and serves file inline without exposing internal storage paths.
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
            resource_type="DOCUMENT_FILE",
            resource_id=document_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to stream this document.",
        )

    try:
        abs_path = get_safe_absolute_path(doc.storage_path)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal violation.")

    if not abs_path.exists() or not abs_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file binary is not found on secure storage volume.",
        )

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="DOCUMENT_STREAM",
        resource_type="DOCUMENT",
        resource_id=doc.id,
        metadata={"file_name": doc.file_name, "size": doc.file_size},
    )

    return FileResponse(
        path=abs_path,
        media_type="application/pdf",
        filename=doc.file_name,
        headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'},
    )


@router.post("/api/v1/documents/{document_id}/retry", response_model=DocumentRetryResponse)
def retry_document_processing(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retry ingestion or processing for a medical record document.
    Re-queues the existing processing job without creating duplicate document records.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical document not found.",
        )

    has_access = can_user_access_patient(current_user.id, doc.patient_id, db)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to retry this document.",
        )

    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == doc.id)
        .order_by(desc(ProcessingJob.created_at))
        .first()
    )

    if not job:
        job = ProcessingJob(
            id=generate_uuid(),
            document_id=doc.id,
            job_type="FULL_DOCUMENT_PROCESSING",
            status="QUEUED",
            progress=0,
            total_pages=doc.page_count or 1,
            processed_pages=0,
            retry_count=1,
            started_at=None,
            completed_at=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(job)
    else:
        job.status = "QUEUED"
        job.progress = 0
        job.error_message = None
        job.retry_count = (job.retry_count or 0) + 1
        job.started_at = None
        job.completed_at = None
        job.updated_at = utc_now()

    doc.status = "UPLOADED"
    doc.updated_at = utc_now()

    # Reset any cached document pages so extraction will re-read PDF fresh
    db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PROCESSING_RETRY",
        resource_type="DOCUMENT",
        resource_id=doc.id,
        metadata={"retry_count": job.retry_count, "status": job.status},
    )

    db.commit()
    db.refresh(doc)

    return DocumentRetryResponse(
        status="ok",
        message="Document processing re-queued successfully.",
        document=_enrich_document_response(doc, db),
    )

