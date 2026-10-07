"""
MedBrief AI — Database ORM Models
Step 3: Database Foundation

Defines SQLAlchemy ORM models for all 17 core relational entities.
Compatible with PostgreSQL / Supabase and SQLite.
"""

import uuid
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    BigInteger,
    Float,
    DateTime,
    Date,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from src.backend.db.connection import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── 1. ROLES ─────────────────────────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


# ── 2. USERS ─────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    role_title = Column(String(100), nullable=True)
    medical_license_id = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    patient_access = relationship("PatientUserAccess", back_populates="user", cascade="all, delete-orphan")


# ── 3. USER_ROLES ────────────────────────────────────────────────────────────
class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )


# ── 4. PATIENTS ──────────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    mrn = Column(String(100), unique=True, index=True, nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    archived_at = Column(DateTime, nullable=True)

    user_access = relationship("PatientUserAccess", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="patient")
    clinical_events = relationship("ClinicalEvent", back_populates="patient")
    medications = relationship("Medication", back_populates="patient")
    investigations = relationship("Investigation", back_populates="patient")
    outstanding_items = relationship("OutstandingItem", back_populates="patient")
    summaries = relationship("Summary", back_populates="patient")
    drafts = relationship("Draft", back_populates="patient")
    evidence_references = relationship("EvidenceReference", back_populates="patient")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED', 'DECEASED')", name="chk_patient_status"),
    )


# ── 5. PATIENT_USER_ACCESS ───────────────────────────────────────────────────
class PatientUserAccess(Base):
    __tablename__ = "patient_user_access"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_role = Column(String(50), default="PRIMARY_PHYSICIAN", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="user_access")
    user = relationship("User", back_populates="patient_access")

    __table_args__ = (
        UniqueConstraint("patient_id", "user_id", name="uq_patient_user"),
        CheckConstraint("access_role IN ('PRIMARY_PHYSICIAN', 'CONSULTANT', 'CARE_TEAM', 'READ_ONLY', 'ADMIN')", name="chk_access_role"),
        Index("idx_patient_user_lookup", "patient_id", "user_id"),
    )


# ── 6. DOCUMENTS ─────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), default="application/pdf", nullable=False)
    storage_path = Column(Text, nullable=False)
    document_type = Column(String(50), default="OTHER", nullable=False)
    file_size = Column(BigInteger, nullable=False)
    page_count = Column(Integer, default=0, nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    status = Column(String(50), default="UPLOADED", nullable=False, index=True)
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    archived_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")
    evidence_references = relationship("EvidenceReference", back_populates="document")

    __table_args__ = (
        CheckConstraint("file_size >= 0", name="chk_doc_size"),
        CheckConstraint("page_count >= 0", name="chk_doc_pages"),
        CheckConstraint("status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED', 'PARTIAL', 'REQUIRES_REVIEW', 'ARCHIVED')", name="chk_doc_status"),
    )


# ── 7. DOCUMENT_PAGES ────────────────────────────────────────────────────────
class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    extracted_text = Column(Text, nullable=True)
    ocr_applied = Column(Boolean, default=False, nullable=False)
    processing_status = Column(String(50), default="PENDING", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    document = relationship("Document", back_populates="pages")

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_doc_page"),
        CheckConstraint("page_number >= 1", name="chk_page_num"),
        CheckConstraint("processing_status IN ('PENDING', 'EXTRACTED', 'FAILED')", name="chk_page_status"),
        Index("idx_doc_page_lookup", "document_id", "page_number"),
    )


# ── 8. PROCESSING_JOBS ───────────────────────────────────────────────────────
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(50), default="FULL_DOCUMENT_PROCESSING", nullable=False)
    status = Column(String(50), default="QUEUED", nullable=False, index=True)
    progress = Column(Integer, default=0, nullable=False)
    total_pages = Column(Integer, default=0, nullable=False)
    processed_pages = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    document = relationship("Document", back_populates="jobs")

    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="chk_job_progress"),
        CheckConstraint("retry_count >= 0", name="chk_job_retries"),
        CheckConstraint("status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'PARTIAL', 'REQUIRES_REVIEW')", name="chk_job_status"),
    )


# ── 9. CLINICAL_EVENTS ───────────────────────────────────────────────────────
class ClinicalEvent(Base):
    __tablename__ = "clinical_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_date = Column(DateTime, nullable=True, index=True)
    event_date_precision = Column(String(50), default="EXACT", nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Float, nullable=True)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    is_conflict = Column(Boolean, default=False, nullable=False)
    conflict_details = Column(Text, nullable=True)
    review_status = Column(String(50), default="UNREVIEWED", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="clinical_events")

    __table_args__ = (
        CheckConstraint("event_date_precision IN ('EXACT', 'APPROXIMATE', 'MONTH_YEAR', 'YEAR_ONLY', 'UNKNOWN')", name="chk_event_precision"),
        CheckConstraint("review_status IN ('UNREVIEWED', 'VERIFIED', 'REJECTED')", name="chk_event_review"),
    )


# ── 10. MEDICATIONS ──────────────────────────────────────────────────────────
class Medication(Base):
    __tablename__ = "medications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    medication_name = Column(String(255), nullable=False)
    generic_name = Column(String(255), nullable=True)
    dosage = Column(String(100), nullable=True)
    dose_unit = Column(String(50), nullable=True)
    route = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="medications")
    changes = relationship("MedicationChange", back_populates="medication")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'STOPPED', 'HISTORICAL', 'UNKNOWN')", name="chk_med_status"),
    )


# ── 11. MEDICATION_CHANGES ───────────────────────────────────────────────────
class MedicationChange(Base):
    __tablename__ = "medication_changes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    medication_id = Column(String(36), ForeignKey("medications.id", ondelete="RESTRICT"), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)
    previous_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    change_date = Column(Date, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    review_status = Column(String(50), default="UNREVIEWED", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    medication = relationship("Medication", back_populates="changes")

    __table_args__ = (
        CheckConstraint("change_type IN ('STARTED', 'STOPPED', 'DOSE_CHANGED', 'FREQUENCY_CHANGED', 'ROUTE_CHANGED', 'OTHER')", name="chk_change_type"),
        CheckConstraint("review_status IN ('UNREVIEWED', 'VERIFIED', 'REJECTED')", name="chk_change_review"),
    )


# ── 12. INVESTIGATIONS ───────────────────────────────────────────────────────
class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    investigation_name = Column(String(255), nullable=False)
    investigation_type = Column(String(50), default="LAB", nullable=False)
    ordered_date = Column(Date, nullable=True, index=True)
    completed_date = Column(Date, nullable=True)
    status = Column(String(50), default="ORDERED", nullable=False, index=True)
    result_summary = Column(Text, nullable=True)
    reference_range = Column(String(100), nullable=True)
    is_abnormal = Column(Boolean, nullable=True)
    clinical_urgency = Column(String(50), default="NORMAL", nullable=False)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="investigations")

    __table_args__ = (
        CheckConstraint("status IN ('ORDERED', 'PENDING', 'COMPLETED', 'CANCELLED', 'UNKNOWN')", name="chk_inv_status"),
        CheckConstraint("clinical_urgency IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')", name="chk_inv_urgency"),
    )


# ── 13. OUTSTANDING_ITEMS ────────────────────────────────────────────────────
class OutstandingItem(Base):
    __tablename__ = "outstanding_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default="NORMAL", nullable=False, index=True)
    status = Column(String(50), default="OPEN", nullable=False, index=True)
    due_date = Column(Date, nullable=True)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True)
    is_ai_generated = Column(Boolean, default=True, nullable=False)
    review_status = Column(String(50), default="UNREVIEWED", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="outstanding_items")

    __table_args__ = (
        CheckConstraint("item_type IN ('PENDING_INVESTIGATION', 'FOLLOW_UP', 'MEDICATION_REVIEW', 'SPECIALIST_FOLLOW_UP', 'MONITORING', 'DOCUMENTATION', 'OTHER')", name="chk_item_type"),
        CheckConstraint("priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')", name="chk_item_priority"),
        CheckConstraint("status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED')", name="chk_item_status"),
        CheckConstraint("review_status IN ('UNREVIEWED', 'VERIFIED', 'REJECTED')", name="chk_item_review"),
    )


# ── 14. SUMMARIES ────────────────────────────────────────────────────────────
class Summary(Base):
    __tablename__ = "summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    summary_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="DRAFT", nullable=False)
    generated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_ai_generated = Column(Boolean, default=True, nullable=False)
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="summaries")

    __table_args__ = (
        CheckConstraint("summary_type IN ('QUICK_CLINICAL', 'DETAILED_CLINICAL', 'MEDICATION', 'INVESTIGATION', 'REFERRAL', 'DISCHARGE', 'HANDOFF')", name="chk_summary_type"),
        CheckConstraint("status IN ('DRAFT', 'GENERATED', 'REVIEWED', 'APPROVED', 'ARCHIVED')", name="chk_summary_status"),
    )


# ── 15. EVIDENCE_REFERENCES ──────────────────────────────────────────────────
class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True)
    parent_entity_type = Column(String(50), nullable=False)
    parent_entity_id = Column(String(36), nullable=False)
    source_section = Column(String(255), nullable=True)
    source_text = Column(Text, nullable=False)
    source_type = Column(String(50), default="PDF_TEXT", nullable=False)
    confidence = Column(Float, default=1.0, nullable=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="evidence_references")
    document = relationship("Document", back_populates="evidence_references")

    __table_args__ = (
        CheckConstraint("parent_entity_type IN ('CLINICAL_EVENT', 'MEDICATION', 'MEDICATION_CHANGE', 'INVESTIGATION', 'OUTSTANDING_ITEM', 'SUMMARY', 'DRAFT')", name="chk_evidence_parent"),
        Index("idx_evidence_parent_lookup", "parent_entity_type", "parent_entity_id"),
    )


# ── 16. DRAFTS ───────────────────────────────────────────────────────────────
class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    draft_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="DRAFT", nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_by_ai = Column(Boolean, default=True, nullable=False)
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="drafts")

    @property
    def is_ai_generated(self) -> bool:
        return self.generated_by_ai

    @is_ai_generated.setter
    def is_ai_generated(self, value: bool) -> None:
        self.generated_by_ai = value


    __table_args__ = (
        CheckConstraint("draft_type IN ('REFERRAL', 'DISCHARGE', 'HANDOFF', 'CONSULTATION_NOTE')", name="chk_draft_type"),
        CheckConstraint("status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'ARCHIVED')", name="chk_draft_status"),
    )


# ── 17. AUDIT_EVENTS ─────────────────────────────────────────────────────────
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_resource_lookup", "resource_type", "resource_id"),
    )


# ── 18. USER_PREFERENCES ────────────────────────────────────────────────────
class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    theme = Column(String(50), default="light", nullable=False)
    reduced_motion = Column(Boolean, default=False, nullable=False)
    density = Column(String(50), default="comfortable", nullable=False)
    notify_in_app = Column(Boolean, default=True, nullable=False)
    notify_doc_processing = Column(Boolean, default=True, nullable=False)
    notify_ai_completion = Column(Boolean, default=True, nullable=False)
    notify_follow_up_alerts = Column(Boolean, default=True, nullable=False)
    default_dashboard_view = Column(String(50), default="dashboard", nullable=False)
    default_summary_type = Column(String(50), default="CLINICAL_BRIEF", nullable=False)
    results_per_page = Column(Integer, default=10, nullable=False)
    date_format = Column(String(50), default="YYYY-MM-DD", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", backref="preferences")

