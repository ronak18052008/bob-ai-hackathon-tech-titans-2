"""
MedBrief AI — Patient Management API Router
Step 6: Patient Management

Provides REST endpoints for:
- Patient directory listing with search, status filtering, and pagination
- Patient record resolution by ID with server-side authorization check
- Patient creation with automatic primary physician assignment and audit logging
- Patient updating with field-level validation and audit logging
- Server-side RBAC enforcement ensuring clinicians only access authorized patients
"""

import math
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from src.backend.db.connection import get_db
from src.backend.db.models import (
    Patient,
    PatientUserAccess,
    Document,
    User,
    generate_uuid,
    utc_now,
)
from src.backend.auth.dependencies import (
    get_current_user,
    can_user_access_patient,
)
from src.backend.auth.security import log_auth_audit_event

router = APIRouter(prefix="/api/v1/patients", tags=["Patient Management"])

ALLOWED_STATUSES = {"ACTIVE", "INACTIVE", "ARCHIVED", "DECEASED"}
ALLOWED_GENDERS = {"Male", "Female", "Other", "Unknown", "Non-binary"}


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, description="Patient legal first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Patient legal last name")
    mrn: Optional[str] = Field(None, max_length=100, description="Medical Record Number (unique)")
    date_of_birth: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, max_length=20, description="Patient gender")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact telephone number")
    status: Optional[str] = Field("ACTIVE", description="Patient status: ACTIVE, INACTIVE, ARCHIVED, DECEASED")

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Name cannot be empty or whitespace only")
        return s

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "ACTIVE"
        val = v.strip().upper()
        if val not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of {sorted(ALLOWED_STATUSES)}")
        return val


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    mrn: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    contact_phone: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Name cannot be empty or whitespace only")
            return s
        return v

    @field_validator("status")
    @classmethod
    def validate_status_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            val = v.strip().upper()
            if val not in ALLOWED_STATUSES:
                raise ValueError(f"Status must be one of {sorted(ALLOWED_STATUSES)}")
            return val
        return v


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mrn: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    access_role: Optional[str] = None
    document_count: int = 0
    last_document_date: Optional[datetime] = None


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Helper Functions ─────────────────────────────────────────────────────────

def _generate_mrn(db: Session) -> str:
    """Generate a clean synthetic MRN formatted as MRN-YYYY-XXXX."""
    current_year = datetime.now().year
    suffix = generate_uuid()[:6].upper()
    generated = f"MRN-{current_year}-{suffix}"
    # Verify collision absence
    while db.query(Patient).filter(Patient.mrn == generated).first() is not None:
        suffix = generate_uuid()[:6].upper()
        generated = f"MRN-{current_year}-{suffix}"
    return generated


def _enrich_patient_response(patient: Patient, user_id: str, db: Session) -> PatientResponse:
    """Helper to attach document count, last document date, and user access role."""
    # 1. Document metrics
    doc_query = (
        db.query(
            func.count(Document.id),
            func.max(Document.created_at)
        )
        .filter(Document.patient_id == patient.id)
        .first()
    )
    doc_count = doc_query[0] if doc_query and doc_query[0] is not None else 0
    last_doc_date = doc_query[1] if doc_query and doc_query[1] is not None else None

    # 2. Access role for current user
    access_rec = (
        db.query(PatientUserAccess.access_role)
        .filter(
            PatientUserAccess.patient_id == patient.id,
            PatientUserAccess.user_id == user_id
        )
        .first()
    )
    access_role = access_rec[0] if access_rec else "ASSIGNED_CLINICIAN"

    return PatientResponse(
        id=patient.id,
        mrn=patient.mrn,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        contact_phone=patient.contact_phone,
        status=patient.status,
        created_by=patient.created_by,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        access_role=access_role,
        document_count=doc_count,
        last_document_date=last_doc_date,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=PatientListResponse)
def list_patients(
    search: Optional[str] = Query(None, description="Search term across MRN, first name, and last name"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE, ARCHIVED, DECEASED)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List patients accessible by the authenticated user with search, status filtering, and pagination.
    - Administrators can view all patients across the clinic.
    - Physicians only see patients where patient_user_access grants them permission.
    """
    user_roles = getattr(current_user, "roles_list", [])
    is_admin = "admin" in user_roles

    # Base query
    if is_admin:
        query = db.query(Patient)
    else:
        # Clinicians are restricted to authorized patient relationships
        query = (
            db.query(Patient)
            .join(PatientUserAccess, Patient.id == PatientUserAccess.patient_id)
            .filter(PatientUserAccess.user_id == current_user.id)
        )

    # Status filter
    if status:
        norm_status = status.strip().upper()
        if norm_status in ALLOWED_STATUSES:
            query = query.filter(Patient.status == norm_status)

    # Search filter across first_name, last_name, and mrn
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Patient.first_name).like(s),
                func.lower(Patient.last_name).like(s),
                func.lower(Patient.mrn).like(s),
            )
        )

    total_count = query.count()
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    # Order and paginate
    patients = (
        query.order_by(desc(Patient.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_enrich_patient_response(p, current_user.id, db) for p in patients]

    return PatientListResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve full patient demographic and record metadata by ID.
    Enforces server-side authorization check against patient_user_access.
    Logs a PATIENT_VIEW audit event.
    """
    # 1. Enforce patient-level access control
    has_access = can_user_access_patient(current_user.id, patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_RECORD",
            resource_id=patient_id,
            metadata={"reason": "Unauthorized clinician access attempt"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to access this patient record.",
        )

    # 2. Query patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found in system.",
        )

    # 3. Log authoritative audit event
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PATIENT_VIEW",
        resource_type="PATIENT",
        resource_id=patient.id,
        metadata={"patient_id": patient.id},
    )

    return _enrich_patient_response(patient, current_user.id, db)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new patient record and automatically assign the current clinician as PRIMARY_PHYSICIAN.
    Validates MRN uniqueness or auto-generates if omitted.
    Logs a PATIENT_CREATED audit event.
    """
    # 1. Handle or generate MRN
    mrn = payload.mrn.strip() if payload.mrn and payload.mrn.strip() else _generate_mrn(db)

    # 2. Check for MRN collision
    existing_mrn = db.query(Patient).filter(Patient.mrn == mrn).first()
    if existing_mrn:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Medical Record Number '{mrn}' is already registered to another patient.",
        )

    # 3. Construct Patient entity
    new_patient_id = generate_uuid()
    patient = Patient(
        id=new_patient_id,
        mrn=mrn,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        contact_phone=payload.contact_phone,
        status=payload.status or "ACTIVE",
        created_by=current_user.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(patient)
    db.flush()

    # 4. Automatically grant current user PRIMARY_PHYSICIAN access
    access_mapping = PatientUserAccess(
        id=generate_uuid(),
        patient_id=patient.id,
        user_id=current_user.id,
        access_role="PRIMARY_PHYSICIAN",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(access_mapping)

    # 5. Log audit event
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PATIENT_CREATED",
        resource_type="PATIENT",
        resource_id=patient.id,
        metadata={"patient_id": patient.id},
    )

    db.commit()
    db.refresh(patient)

    return _enrich_patient_response(patient, current_user.id, db)


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update patient demographics or clinical status.
    Enforces server-side authorization check against patient_user_access.
    Validates MRN uniqueness if changed.
    Logs a PATIENT_UPDATED audit event.
    """
    # 1. Enforce patient-level authorization
    has_access = can_user_access_patient(current_user.id, patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_RECORD",
            resource_id=patient_id,
            metadata={"reason": "Unauthorized clinician update attempt"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to edit this patient record.",
        )

    # 2. Query patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found in system.",
        )

    # 3. Check MRN uniqueness if updated
    if payload.mrn is not None:
        new_mrn = payload.mrn.strip()
        if new_mrn and new_mrn != patient.mrn:
            existing = db.query(Patient).filter(Patient.mrn == new_mrn, Patient.id != patient.id).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Medical Record Number '{new_mrn}' is already in use by another patient.",
                )
            patient.mrn = new_mrn

    # 4. Update mutable fields
    updated_fields = []
    if payload.first_name is not None:
        patient.first_name = payload.first_name
        updated_fields.append("first_name")
    if payload.last_name is not None:
        patient.last_name = payload.last_name
        updated_fields.append("last_name")
    if payload.date_of_birth is not None:
        patient.date_of_birth = payload.date_of_birth
        updated_fields.append("date_of_birth")
    if payload.gender is not None:
        patient.gender = payload.gender
        updated_fields.append("gender")
    if payload.contact_phone is not None:
        patient.contact_phone = payload.contact_phone
        updated_fields.append("contact_phone")
    if payload.status is not None:
        patient.status = payload.status
        if payload.status == "ARCHIVED" and not patient.archived_at:
            patient.archived_at = utc_now()
        elif payload.status != "ARCHIVED":
            patient.archived_at = None
        updated_fields.append("status")

    patient.updated_at = utc_now()

    # 5. Log audit event
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PATIENT_UPDATED",
        resource_type="PATIENT",
        resource_id=patient.id,
        metadata={
            "patient_id": patient.id,
            "updated_fields": updated_fields,
        },
    )

    db.commit()
    db.refresh(patient)

    return _enrich_patient_response(patient, current_user.id, db)
