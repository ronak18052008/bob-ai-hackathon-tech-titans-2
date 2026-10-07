-- =============================================================================
-- MedBrief AI — Database Initial Schema Migration
-- Version: 001
-- Phase: Step 3 — Database Foundation
-- Target: PostgreSQL / Supabase
-- Description: Core schema containing 17 relational entities for multi-user,
--              multi-patient, multi-document clinical report summarization.
-- =============================================================================

-- Enable UUID extension if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 1. ROLES ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ── 2. USERS ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    role_title VARCHAR(100),
    medical_license_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ── 3. USER_ROLES ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_user_role UNIQUE (user_id, role_id)
);

-- ── 4. PATIENTS ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mrn VARCHAR(100) UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    contact_phone VARCHAR(50),
    status VARCHAR(50) DEFAULT 'ACTIVE' NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_patient_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED', 'DECEASED'))
);

-- ── 5. PATIENT_USER_ACCESS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patient_user_access (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_role VARCHAR(50) DEFAULT 'PRIMARY_PHYSICIAN' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_patient_user UNIQUE (patient_id, user_id),
    CONSTRAINT chk_access_role CHECK (access_role IN ('PRIMARY_PHYSICIAN', 'CONSULTANT', 'CARE_TEAM', 'READ_ONLY', 'ADMIN'))
);

-- ── 6. DOCUMENTS ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) DEFAULT 'application/pdf' NOT NULL,
    storage_path TEXT NOT NULL,
    document_type VARCHAR(50) DEFAULT 'OTHER' NOT NULL,
    file_size BIGINT NOT NULL,
    page_count INTEGER DEFAULT 0 NOT NULL,
    checksum_sha256 VARCHAR(64),
    status VARCHAR(50) DEFAULT 'UPLOADED' NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_doc_size CHECK (file_size >= 0),
    CONSTRAINT chk_doc_pages CHECK (page_count >= 0),
    CONSTRAINT chk_doc_status CHECK (status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED', 'PARTIAL', 'REQUIRES_REVIEW', 'ARCHIVED'))
);

-- ── 7. DOCUMENT_PAGES ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    extracted_text TEXT,
    ocr_applied BOOLEAN DEFAULT FALSE NOT NULL,
    processing_status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_doc_page UNIQUE (document_id, page_number),
    CONSTRAINT chk_page_num CHECK (page_number >= 1),
    CONSTRAINT chk_page_status CHECK (processing_status IN ('PENDING', 'EXTRACTED', 'FAILED'))
);

-- ── 8. PROCESSING_JOBS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    job_type VARCHAR(50) DEFAULT 'FULL_DOCUMENT_PROCESSING' NOT NULL,
    status VARCHAR(50) DEFAULT 'QUEUED' NOT NULL,
    progress INTEGER DEFAULT 0 NOT NULL,
    total_pages INTEGER DEFAULT 0 NOT NULL,
    processed_pages INTEGER DEFAULT 0 NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_job_progress CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT chk_job_retries CHECK (retry_count >= 0),
    CONSTRAINT chk_job_status CHECK (status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'PARTIAL', 'REQUIRES_REVIEW'))
);

-- ── 9. CLINICAL_EVENTS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clinical_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    event_type VARCHAR(50) NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE,
    event_date_precision VARCHAR(50) DEFAULT 'EXACT' NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page_id UUID REFERENCES document_pages(id) ON DELETE SET NULL,
    confidence FLOAT,
    is_ai_generated BOOLEAN DEFAULT FALSE NOT NULL,
    is_conflict BOOLEAN DEFAULT FALSE NOT NULL,
    conflict_details TEXT,
    review_status VARCHAR(50) DEFAULT 'UNREVIEWED' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_event_precision CHECK (event_date_precision IN ('EXACT', 'APPROXIMATE', 'MONTH_YEAR', 'YEAR_ONLY', 'UNKNOWN')),
    CONSTRAINT chk_event_review CHECK (review_status IN ('UNREVIEWED', 'VERIFIED', 'REJECTED'))
);

-- ── 10. MEDICATIONS ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    medication_name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    dosage VARCHAR(100),
    dose_unit VARCHAR(50),
    route VARCHAR(100),
    frequency VARCHAR(100),
    status VARCHAR(50) DEFAULT 'ACTIVE' NOT NULL,
    start_date DATE,
    end_date DATE,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page_id UUID REFERENCES document_pages(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_med_status CHECK (status IN ('ACTIVE', 'STOPPED', 'HISTORICAL', 'UNKNOWN'))
);

-- ── 11. MEDICATION_CHANGES ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medication_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medication_id UUID NOT NULL REFERENCES medications(id) ON DELETE RESTRICT,
    change_type VARCHAR(50) NOT NULL,
    previous_value VARCHAR(255),
    new_value VARCHAR(255),
    change_date DATE,
    reason TEXT,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page_id UUID REFERENCES document_pages(id) ON DELETE SET NULL,
    is_ai_generated BOOLEAN DEFAULT FALSE NOT NULL,
    review_status VARCHAR(50) DEFAULT 'UNREVIEWED' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_change_type CHECK (change_type IN ('STARTED', 'STOPPED', 'DOSE_CHANGED', 'FREQUENCY_CHANGED', 'ROUTE_CHANGED', 'OTHER')),
    CONSTRAINT chk_change_review CHECK (review_status IN ('UNREVIEWED', 'VERIFIED', 'REJECTED'))
);

-- ── 12. INVESTIGATIONS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    investigation_name VARCHAR(255) NOT NULL,
    investigation_type VARCHAR(50) DEFAULT 'LAB' NOT NULL,
    ordered_date DATE,
    completed_date DATE,
    status VARCHAR(50) DEFAULT 'ORDERED' NOT NULL,
    result_summary TEXT,
    reference_range VARCHAR(100),
    is_abnormal BOOLEAN,
    clinical_urgency VARCHAR(50) DEFAULT 'NORMAL' NOT NULL,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page_id UUID REFERENCES document_pages(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_inv_status CHECK (status IN ('ORDERED', 'PENDING', 'COMPLETED', 'CANCELLED', 'UNKNOWN')),
    CONSTRAINT chk_inv_urgency CHECK (clinical_urgency IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL'))
);

-- ── 13. OUTSTANDING_ITEMS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outstanding_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    item_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority VARCHAR(50) DEFAULT 'NORMAL' NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN' NOT NULL,
    due_date DATE,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page_id UUID REFERENCES document_pages(id) ON DELETE SET NULL,
    is_ai_generated BOOLEAN DEFAULT TRUE NOT NULL,
    review_status VARCHAR(50) DEFAULT 'UNREVIEWED' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_item_type CHECK (item_type IN ('PENDING_INVESTIGATION', 'FOLLOW_UP', 'MEDICATION_REVIEW', 'SPECIALIST_FOLLOW_UP', 'MONITORING', 'DOCUMENTATION', 'OTHER')),
    CONSTRAINT chk_item_priority CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')),
    CONSTRAINT chk_item_status CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED')),
    CONSTRAINT chk_item_review CHECK (review_status IN ('UNREVIEWED', 'VERIFIED', 'REJECTED'))
);

-- ── 14. SUMMARIES ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    summary_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'DRAFT' NOT NULL,
    generated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    is_ai_generated BOOLEAN DEFAULT TRUE NOT NULL,
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_summary_type CHECK (summary_type IN ('QUICK_CLINICAL', 'DETAILED_CLINICAL', 'MEDICATION', 'INVESTIGATION', 'REFERRAL', 'DISCHARGE', 'HANDOFF')),
    CONSTRAINT chk_summary_status CHECK (status IN ('DRAFT', 'GENERATED', 'REVIEWED', 'APPROVED', 'ARCHIVED'))
);

-- ── 15. EVIDENCE_REFERENCES ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evidence_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_page_id UUID REFERENCES document_pages(id) ON DELETE SET NULL,
    parent_entity_type VARCHAR(50) NOT NULL,
    parent_entity_id UUID NOT NULL,
    source_section VARCHAR(255),
    source_text TEXT NOT NULL,
    source_type VARCHAR(50) DEFAULT 'PDF_TEXT' NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    char_start INTEGER,
    char_end INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_evidence_parent CHECK (parent_entity_type IN ('CLINICAL_EVENT', 'MEDICATION', 'MEDICATION_CHANGE', 'INVESTIGATION', 'OUTSTANDING_ITEM', 'SUMMARY', 'DRAFT'))
);

-- ── 16. DRAFTS ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    draft_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'DRAFT' NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    generated_by_ai BOOLEAN DEFAULT TRUE NOT NULL,
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_draft_type CHECK (draft_type IN ('REFERRAL', 'DISCHARGE', 'HANDOFF', 'CONSULTATION_NOTE')),
    CONSTRAINT chk_draft_status CHECK (status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'ARCHIVED'))
);

-- ── 17. AUDIT_EVENTS ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- =============================================================================
-- INDEXES FOR HIGH-PERFORMANCE CLINICAL QUERIES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patients(created_at);
CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patients(mrn);
CREATE INDEX IF NOT EXISTS idx_patient_user_access_lookup ON patient_user_access(patient_id, user_id);

CREATE INDEX IF NOT EXISTS idx_documents_patient ON documents(patient_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

CREATE INDEX IF NOT EXISTS idx_doc_pages_lookup ON document_pages(document_id, page_number);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_doc ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at ON processing_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_clinical_events_patient ON clinical_events(patient_id);
CREATE INDEX IF NOT EXISTS idx_clinical_events_date ON clinical_events(event_date);
CREATE INDEX IF NOT EXISTS idx_clinical_events_type ON clinical_events(event_type);

CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_medications_status ON medications(status);

CREATE INDEX IF NOT EXISTS idx_med_changes_med ON medication_changes(medication_id);
CREATE INDEX IF NOT EXISTS idx_med_changes_date ON medication_changes(change_date);

CREATE INDEX IF NOT EXISTS idx_investigations_patient ON investigations(patient_id);
CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status);
CREATE INDEX IF NOT EXISTS idx_investigations_ordered_date ON investigations(ordered_date);

CREATE INDEX IF NOT EXISTS idx_outstanding_items_patient ON outstanding_items(patient_id);
CREATE INDEX IF NOT EXISTS idx_outstanding_items_status ON outstanding_items(status);
CREATE INDEX IF NOT EXISTS idx_outstanding_items_priority ON outstanding_items(priority);

CREATE INDEX IF NOT EXISTS idx_summaries_patient ON summaries(patient_id);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON summaries(summary_type);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at);

CREATE INDEX IF NOT EXISTS idx_evidence_patient ON evidence_references(patient_id);
CREATE INDEX IF NOT EXISTS idx_evidence_doc ON evidence_references(document_id);
CREATE INDEX IF NOT EXISTS idx_evidence_parent ON evidence_references(parent_entity_type, parent_entity_id);

CREATE INDEX IF NOT EXISTS idx_drafts_patient ON drafts(patient_id);
CREATE INDEX IF NOT EXISTS idx_drafts_type ON drafts(draft_type);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events(created_at);
