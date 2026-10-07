"""
MedBrief AI — Database Foundation Test Suite
Step 3: Database Foundation

Validates relational integrity, constraints, indexes, 17 core entities,
and soft-delete functionality using the SQLAlchemy session.
"""

import pytest
from datetime import datetime, date, timezone
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from src.backend.db.connection import engine, SessionLocal
from src.backend.db.init_db import init_database
from src.backend.db.models import (
    Role,
    User,
    UserRole,
    Patient,
    PatientUserAccess,
    Document,
    DocumentPage,
    ProcessingJob,
    ClinicalEvent,
    Medication,
    MedicationChange,
    Investigation,
    OutstandingItem,
    Summary,
    EvidenceReference,
    Draft,
    AuditEvent,
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database schema is created before tests execute."""
    init_database()


@pytest.fixture
def db():
    """Yields a database session that rolls back changes after each test."""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def test_all_17_tables_exist():
    """Verify that all 17 core tables exist in the database metadata."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "roles",
        "users",
        "user_roles",
        "patients",
        "patient_user_access",
        "documents",
        "document_pages",
        "processing_jobs",
        "clinical_events",
        "medications",
        "medication_changes",
        "investigations",
        "outstanding_items",
        "summaries",
        "evidence_references",
        "drafts",
        "audit_events",
    }

    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_user_and_role_relationship(db):
    """Test user creation, role assignment, and relational query."""
    role = Role(name="test_specialist", description="Specialist Physician")
    db.add(role)
    db.flush()

    user = User(
        email="specialist@demo.test",
        display_name="Dr. Test Specialist",
        role_title="Cardiologist",
    )
    db.add(user)
    db.flush()

    user_role = UserRole(user_id=user.id, role_id=role.id)
    db.add(user_role)
    db.flush()

    # Query back
    queried_user = db.query(User).filter_by(email="specialist@demo.test").first()
    assert queried_user is not None
    assert len(queried_user.roles) == 1
    assert queried_user.roles[0].role.name == "test_specialist"


def test_unique_user_role_constraint(db):
    """Verify that assigning the duplicate role to the same user raises IntegrityError."""
    role = Role(name="unique_role_test", description="Test")
    user = User(email="unique_role_user@demo.test", display_name="Test User")
    db.add_all([role, user])
    db.flush()

    ur1 = UserRole(user_id=user.id, role_id=role.id)
    db.add(ur1)
    db.flush()

    ur2 = UserRole(user_id=user.id, role_id=role.id)
    db.add(ur2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_patient_and_documents_relationship(db):
    """Test that a patient can have multiple documents."""
    patient = Patient(
        first_name="Jane",
        last_name="Doe",
        mrn="MRN-TEST-1001",
        status="ACTIVE",
    )
    db.add(patient)
    db.flush()

    doc1 = Document(
        patient_id=patient.id,
        file_name="Consult_Note_1.pdf",
        storage_path="/docs/c1.pdf",
        file_size=50000,
        page_count=3,
        document_type="CLINIC_CONSULTATION",
    )
    doc2 = Document(
        patient_id=patient.id,
        file_name="Lab_Report_1.pdf",
        storage_path="/docs/l1.pdf",
        file_size=25000,
        page_count=1,
        document_type="LAB_PATHOLOGY",
    )
    db.add_all([doc1, doc2])
    db.flush()

    queried_patient = db.query(Patient).filter_by(mrn="MRN-TEST-1001").first()
    assert queried_patient is not None
    assert len(queried_patient.documents) == 2


def test_document_page_unique_constraint(db):
    """Verify (document_id, page_number) must be unique."""
    patient = Patient(first_name="DocPage", last_name="Test", status="ACTIVE")
    db.add(patient)
    db.flush()

    doc = Document(
        patient_id=patient.id,
        file_name="test.pdf",
        storage_path="/test.pdf",
        file_size=100,
    )
    db.add(doc)
    db.flush()

    page1_a = DocumentPage(document_id=doc.id, page_number=1, extracted_text="Page 1 Content")
    db.add(page1_a)
    db.flush()

    page1_b = DocumentPage(document_id=doc.id, page_number=1, extracted_text="Duplicate Page 1")
    db.add(page1_b)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_medication_and_change_history(db):
    """Verify that medication changes track history without overwriting the medication."""
    patient = Patient(first_name="Med", last_name="History", status="ACTIVE")
    db.add(patient)
    db.flush()

    med = Medication(
        patient_id=patient.id,
        medication_name="Amlodipine",
        dosage="5",
        dose_unit="mg",
        frequency="OD",
        status="ACTIVE",
    )
    db.add(med)
    db.flush()

    # Record dose escalation
    change = MedicationChange(
        medication_id=med.id,
        change_type="DOSE_CHANGED",
        previous_value="5mg OD",
        new_value="10mg OD",
        reason="Sub-optimal blood pressure control",
        change_date=date(2026, 3, 1),
    )
    db.add(change)
    db.flush()

    queried_med = db.query(Medication).filter_by(id=med.id).first()
    assert queried_med is not None
    assert len(queried_med.changes) == 1
    assert queried_med.changes[0].new_value == "10mg OD"


def test_evidence_reference_linkage(db):
    """Verify evidence references link to document and page."""
    patient = Patient(first_name="Evidence", last_name="Test", status="ACTIVE")
    db.add(patient)
    db.flush()

    doc = Document(patient_id=patient.id, file_name="ev.pdf", storage_path="/ev.pdf", file_size=100)
    db.add(doc)
    db.flush()

    page = DocumentPage(document_id=doc.id, page_number=3, extracted_text="Evidence text")
    db.add(page)
    db.flush()

    event = ClinicalEvent(
        patient_id=patient.id,
        event_type="DIAGNOSIS",
        title="Hypertension",
        description="Newly noted essential hypertension",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db.add(event)
    db.flush()

    evidence = EvidenceReference(
        patient_id=patient.id,
        document_id=doc.id,
        document_page_id=page.id,
        parent_entity_type="CLINICAL_EVENT",
        parent_entity_id=event.id,
        source_section="Assessment & Plan",
        source_text="BP 154/96 mmHg. Commenced anti-hypertensive therapy.",
        confidence=0.97,
    )
    db.add(evidence)
    db.flush()

    queried_ev = db.query(EvidenceReference).filter_by(parent_entity_id=event.id).first()
    assert queried_ev is not None
    assert queried_ev.source_section == "Assessment & Plan"
    assert queried_ev.confidence == 0.97


def test_patient_soft_delete_preservation(db):
    """Verify soft-delete archiving preserves the record without cascading destruction."""
    patient = Patient(first_name="Archive", last_name="Patient", status="ACTIVE")
    db.add(patient)
    db.flush()

    event = ClinicalEvent(
        patient_id=patient.id,
        event_type="CONSULTATION",
        title="Initial Consult",
        description="Preserved history",
    )
    db.add(event)
    db.flush()

    # Soft-delete the patient
    patient.status = "ARCHIVED"
    patient.archived_at = datetime.now(timezone.utc)
    db.flush()

    # Verify event still exists
    queried_event = db.query(ClinicalEvent).filter_by(patient_id=patient.id).first()
    assert queried_event is not None
    assert queried_event.description == "Preserved history"
