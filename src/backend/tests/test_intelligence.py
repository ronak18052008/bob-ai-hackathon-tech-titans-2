"""
MedBrief AI — Clinical Intelligence Automated Test Suite
Step 11: Medication + Investigation Intelligence

Comprehensive tests verifying:
1. Medication change intelligence:
   - Medication started
   - Medication stopped
   - Medication dose change (previous_value -> new_value)
   - Medication frequency change
   - Medication route change
   - No false change when previous dose is missing
   - Disappearing medication not assumed stopped
   - Conflicting medication records preserved
2. Investigation intelligence:
   - Investigation ordered
   - Investigation pending
   - Investigation completed
   - Investigation cancelled
   - Investigation unknown status
   - Missing investigation result NOT inferred as pending
   - Conflicting investigation records preserved
3. Outstanding clinical items:
   - PENDING_INVESTIGATION
   - FOLLOW_UP
   - MEDICATION_REVIEW
   - SPECIALIST_FOLLOW_UP
   - MONITORING
   - DOCUMENTATION
   - OTHER
4. Source traceability:
   - Document name, page number, verbatim snippet
5. API endpoints:
   - 401 Unauthenticated
   - 403 Unauthorized patient access
   - 404 Patient not found
   - Audit logging verification (Zero PHI)
"""

import pytest
from datetime import datetime, timezone, date
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.main import app
from src.backend.db.connection import SessionLocal
from src.backend.db.models import (
    User,
    Patient,
    Document,
    DocumentPage,
    Medication,
    MedicationChange,
    Investigation,
    OutstandingItem,
    EvidenceReference,
    AuditEvent,
)
from src.backend.auth.security import create_access_token
from src.backend.intelligence.intelligence_service import (
    is_explicitly_pending,
    ClinicalIntelligenceService,
)

client = TestClient(app)

DEMO_PATIENT_ID = "22222222-2222-4000-8000-222222222222"
UNAUTHORIZED_PATIENT_ID = "22222222-2222-4000-8000-222222222299"


# ── Fixtures & Setup ──────────────────────────────────────────────────────────

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_headers_doctor(db_session: Session):
    """Token for Dr. Sarah Chen (authorized for Demo Patient Johnathan Doe)."""
    doctor = db_session.query(User).filter(User.email == "dr.sarah.chen@demo-clinic.test").first()
    token = create_access_token(data={"sub": doctor.id, "email": doctor.email, "roles": ["doctor"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_doc_and_page(db_session: Session):
    """Ensure a document and page exist for linking evidence."""
    doc = db_session.query(Document).filter(Document.patient_id == DEMO_PATIENT_ID).first()
    if not doc:
        doc = Document(
            patient_id=DEMO_PATIENT_ID,
            file_name="discharge_summary.pdf",
            file_type="application/pdf",
            storage_path="uploads/discharge_summary.pdf",
            file_size=1024,
            document_type="DISCHARGE_SUMMARY",
            status="PROCESSED",
            page_count=3,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

    page = db_session.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()
    if not page:
        page = DocumentPage(
            document_id=doc.id,
            page_number=1,
            page_text_extracted="Discharge Medications: Atorvastatin 40mg PO QHS. Metformin 500mg BID. Awaiting echocardiogram results.",
        )
        db_session.add(page)
        db_session.commit()
        db_session.refresh(page)

    return doc, page


# ── 1. Unit Tests: Strict Pending Helper ───────────────────────────────────────

def test_is_explicitly_pending_rule():
    """Verify strict rule: only explicit terms trigger pending; missing result does not."""
    # Explicit status
    assert is_explicitly_pending("PENDING") is True
    assert is_explicitly_pending("pending") is True

    # Explicit text in result
    assert is_explicitly_pending("ORDERED", result_text="Awaiting result from pathology") is True
    assert is_explicitly_pending("ORDERED", result_text="Results awaited") is True
    assert is_explicitly_pending("ORDERED", source_snippet="Echo scheduled for follow up after discharge") is True
    assert is_explicitly_pending("ORDERED", source_snippet="Specimen sent to microbiology") is True

    # Missing result without explicit keywords must NOT be pending
    assert is_explicitly_pending("ORDERED", result_text=None, source_snippet=None) is False
    assert is_explicitly_pending("ORDERED", result_text="", source_snippet="") is False
    assert is_explicitly_pending(None, result_text=None, source_snippet=None) is False

    # Completed test
    assert is_explicitly_pending("COMPLETED", result_text="Hemoglobin 14.2 g/dL", source_snippet="CBC normal") is False


# ── 2. Medication Change Intelligence ─────────────────────────────────────────

def test_medication_started(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Aspirin",
        generic_name="Acetylsalicylic acid",
        dosage="81",
        dose_unit="mg",
        route="Oral",
        frequency="Once daily",
        status="ACTIVE",
        start_date=date(2026, 2, 5),
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    change = MedicationChange(
        medication_id=med.id,
        change_type="STARTED",
        new_value="81 mg",
        change_date=date(2026, 2, 5),
        reason="Acute coronary syndrome secondary prevention",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(change)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medication_changes(db_session, DEMO_PATIENT_ID)
    items = [c for c in res["items"] if c["medication_id"] == med.id]
    assert len(items) >= 1
    assert items[0]["change_type"] == "STARTED"
    assert items[0]["new_value"] == "81 mg"
    assert items[0]["reason"] == "Acute coronary syndrome secondary prevention"


def test_medication_stopped(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Warfarin",
        dosage="5",
        dose_unit="mg",
        status="STOPPED",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 2, 5),
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    change = MedicationChange(
        medication_id=med.id,
        change_type="STOPPED",
        previous_value="5 mg",
        new_value=None,
        change_date=date(2026, 2, 5),
        reason="Discontinued prior to cardiac catheterization",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(change)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medication_changes(db_session, DEMO_PATIENT_ID)
    items = [c for c in res["items"] if c["medication_id"] == med.id]
    assert len(items) >= 1
    assert items[0]["change_type"] == "STOPPED"
    assert items[0]["previous_value"] == "5 mg"
    assert items[0]["reason"] == "Discontinued prior to cardiac catheterization"


def test_medication_dose_change(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Atorvastatin",
        dosage="40",
        dose_unit="mg",
        status="ACTIVE",
        start_date=date(2026, 2, 5),
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    change = MedicationChange(
        medication_id=med.id,
        change_type="DOSE_CHANGED",
        previous_value="20 mg",
        new_value="40 mg",
        change_date=date(2026, 2, 5),
        reason="Up-titrated for high-intensity statin therapy post-NSTEMI",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(change)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medication_changes(db_session, DEMO_PATIENT_ID)
    items = [c for c in res["items"] if c["medication_id"] == med.id and c["change_type"] == "DOSE_CHANGED"]
    assert len(items) >= 1
    assert items[0]["previous_value"] == "20 mg"
    assert items[0]["new_value"] == "40 mg"
    assert items[0]["change_type_label"] == "Dose Changed"


def test_medication_frequency_change(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Metformin",
        dosage="500",
        dose_unit="mg",
        frequency="Twice daily",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    change = MedicationChange(
        medication_id=med.id,
        change_type="FREQUENCY_CHANGED",
        previous_value="Once daily",
        new_value="Twice daily",
        change_date=date(2026, 2, 6),
        reason="Glycemic control titration",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(change)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medication_changes(db_session, DEMO_PATIENT_ID)
    items = [c for c in res["items"] if c["medication_id"] == med.id and c["change_type"] == "FREQUENCY_CHANGED"]
    assert len(items) >= 1
    assert items[0]["previous_value"] == "Once daily"
    assert items[0]["new_value"] == "Twice daily"


def test_medication_route_change(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Furosemide",
        dosage="40",
        dose_unit="mg",
        route="Oral",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    change = MedicationChange(
        medication_id=med.id,
        change_type="ROUTE_CHANGED",
        previous_value="Intravenous",
        new_value="Oral",
        change_date=date(2026, 2, 7),
        reason="Transition to oral regimen upon clinical stabilization",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(change)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medication_changes(db_session, DEMO_PATIENT_ID)
    items = [c for c in res["items"] if c["medication_id"] == med.id and c["change_type"] == "ROUTE_CHANGED"]
    assert len(items) >= 1
    assert items[0]["previous_value"] == "Intravenous"
    assert items[0]["new_value"] == "Oral"


def test_no_false_change_when_previous_dose_missing(db_session: Session, test_doc_and_page):
    """When a medication is recorded with 10 mg for the first time without prior recorded dose, no false dose change is generated."""
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Lisinopril",
        dosage="10",
        dose_unit="mg",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()

    # Query changes for Lisinopril
    res = ClinicalIntelligenceService.get_patient_medication_changes(db_session, DEMO_PATIENT_ID)
    changes = [c for c in res["items"] if c["medication_name"] == "Lisinopril"]
    # No false DOSE_CHANGED change must exist
    dose_changes = [c for c in changes if c["change_type"] == "DOSE_CHANGED"]
    assert len(dose_changes) == 0


def test_disappearing_medication_not_marked_stopped(db_session: Session, test_doc_and_page):
    """A medication documented in doc 1 but omitted from doc 2 must NOT be marked as STOPPED."""
    doc, page = test_doc_and_page
    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Levothyroxine",
        dosage="50",
        dose_unit="mcg",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    # Verify status remains ACTIVE
    med_list = ClinicalIntelligenceService.get_patient_medications(db_session, DEMO_PATIENT_ID, search="Levothyroxine")
    levo = next((m for m in med_list["items"] if m["id"] == med.id), None)
    assert levo is not None
    assert levo["status"] == "ACTIVE"


def test_conflicting_medication_records_preserved(db_session: Session, test_doc_and_page):
    """When multiple records give discordant concurrent dosages for the same medication, both are retained and conflict is flagged."""
    doc, page = test_doc_and_page
    med1 = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Metoprolol Succinate",
        dosage="25",
        dose_unit="mg",
        frequency="Once daily",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    med2 = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Metoprolol Succinate",
        dosage="50",
        dose_unit="mg",
        frequency="Once daily",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add_all([med1, med2])
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medications(db_session, DEMO_PATIENT_ID, search="Metoprolol")
    items = [m for m in res["items"] if "Metoprolol" in m["medication_name"]]
    assert len(items) >= 2
    # Verify conflict detection
    conflicting = [m for m in items if m["is_conflict"]]
    assert len(conflicting) >= 2


# ── 3. Investigation Intelligence ─────────────────────────────────────────────

def test_investigation_ordered(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    inv = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Lipid Panel",
        investigation_type="LAB",
        ordered_date=date(2026, 2, 5),
        status="ORDERED",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(inv)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(db_session, DEMO_PATIENT_ID)
    match = next((i for i in res["items"] if i["id"] == inv.id), None)
    assert match is not None
    assert match["status"] == "ORDERED"
    assert match["investigation_name"] == "Lipid Panel"


def test_investigation_pending(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    inv = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Transthoracic Echocardiogram",
        investigation_type="IMAGING",
        ordered_date=date(2026, 2, 5),
        status="PENDING",
        result_summary="Awaiting outpatient procedure",
        clinical_urgency="HIGH",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(inv)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(db_session, DEMO_PATIENT_ID)
    match = next((i for i in res["items"] if i["id"] == inv.id), None)
    assert match is not None
    assert match["status"] == "PENDING"
    assert match["clinical_urgency"] == "HIGH"


def test_investigation_completed(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    inv = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Serum Potassium",
        investigation_type="LAB",
        ordered_date=date(2026, 2, 5),
        completed_date=date(2026, 2, 5),
        status="COMPLETED",
        result_summary="4.1 mmol/L",
        reference_range="3.5 - 5.0 mmol/L",
        is_abnormal=False,
        clinical_urgency="NORMAL",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(inv)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(db_session, DEMO_PATIENT_ID)
    match = next((i for i in res["items"] if i["id"] == inv.id), None)
    assert match is not None
    assert match["status"] == "COMPLETED"
    assert match["result_summary"] == "4.1 mmol/L"
    assert match["is_abnormal"] is False


def test_investigation_cancelled(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    inv = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Routine Chest X-Ray",
        investigation_type="IMAGING",
        ordered_date=date(2026, 2, 5),
        status="CANCELLED",
        result_summary="Cancelled by ordering clinician",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(inv)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(db_session, DEMO_PATIENT_ID)
    match = next((i for i in res["items"] if i["id"] == inv.id), None)
    assert match is not None
    assert match["status"] == "CANCELLED"


def test_investigation_unknown_status(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    inv = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Historical Colonoscopy",
        investigation_type="PROCEDURE",
        status="UNKNOWN",
        result_summary="Mentioned in past history without formal report attached",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(inv)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(
        db_session, DEMO_PATIENT_ID, search="Historical Colonoscopy"
    )
    match = next((i for i in res["items"] if i["id"] == inv.id), None)
    assert match is not None
    assert match["status"] == "UNKNOWN"


def test_missing_investigation_result_not_inferred_as_pending(db_session: Session, test_doc_and_page):
    """Strict rule: An investigation ordered without a documented result must NOT default to pending unless explicit wording exists."""
    doc, page = test_doc_and_page
    inv = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Serum Magnesium",
        investigation_type="LAB",
        ordered_date=date(2026, 2, 5),
        status="ORDERED",
        result_summary=None,
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(inv)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(db_session, DEMO_PATIENT_ID)
    match = next((i for i in res["items"] if i["id"] == inv.id), None)
    assert match is not None
    # Must remain ORDERED, never mutated to PENDING
    assert match["status"] == "ORDERED"


def test_conflicting_investigation_statuses_preserved(db_session: Session, test_doc_and_page):
    """Multiple documented records for an investigation across different visits/notes retain both records and conflict is flagged."""
    doc, page = test_doc_and_page
    inv1 = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Troponin I",
        investigation_type="LAB",
        ordered_date=date(2026, 2, 5),
        status="COMPLETED",
        result_summary="0.02 ng/mL (Normal)",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    inv2 = Investigation(
        patient_id=DEMO_PATIENT_ID,
        investigation_name="Troponin I",
        investigation_type="LAB",
        ordered_date=date(2026, 2, 5),
        status="COMPLETED",
        result_summary="0.45 ng/mL (Elevated)",
        is_abnormal=True,
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add_all([inv1, inv2])
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_investigations(db_session, DEMO_PATIENT_ID)
    matches = [i for i in res["items"] if i["investigation_name"] == "Troponin I"]
    assert len(matches) >= 2
    # Verify conflict flag
    conflicting = [i for i in matches if i["is_conflict"]]
    assert len(conflicting) >= 2


# ── 4. Outstanding Items Intelligence ─────────────────────────────────────────

def test_outstanding_all_types(db_session: Session, test_doc_and_page):
    """Verify cataloging of all 7 outstanding item types."""
    doc, page = test_doc_and_page
    types = [
        ("PENDING_INVESTIGATION", "Awaiting formal Holter monitor report", "HIGH"),
        ("FOLLOW_UP", "Follow up with primary care physician in 2 weeks", "NORMAL"),
        ("MEDICATION_REVIEW", "Review dual antiplatelet duration at 6 months", "NORMAL"),
        ("SPECIALIST_FOLLOW_UP", "Cardiology clinic follow-up appointment", "HIGH"),
        ("MONITORING", "Serial blood pressure monitoring twice weekly", "NORMAL"),
        ("DOCUMENTATION", "Request outside hospital records from transferring facility", "LOW"),
        ("OTHER", "Dietary consultation referral", "LOW"),
    ]

    for item_type, title, priority in types:
        item = OutstandingItem(
            patient_id=DEMO_PATIENT_ID,
            item_type=item_type,
            title=title,
            priority=priority,
            status="OPEN",
            due_date=date(2026, 3, 1),
            source_document_id=doc.id,
            source_page_id=page.id,
        )
        db_session.add(item)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_outstanding_items(db_session, DEMO_PATIENT_ID, page_size=200)
    retrieved_types = {i["item_type"] for i in res["items"]}
    for item_type, _, _ in types:
        assert item_type in retrieved_types


# ── 5. Source Traceability ────────────────────────────────────────────────────

def test_source_traceability_on_medications_and_investigations(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page

    med = Medication(
        patient_id=DEMO_PATIENT_ID,
        medication_name="Traceable Drug",
        dosage="10",
        dose_unit="mg",
        status="ACTIVE",
        source_document_id=doc.id,
        source_page_id=page.id,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    # Add evidence reference
    ev = EvidenceReference(
        patient_id=DEMO_PATIENT_ID,
        document_id=doc.id,
        document_page_id=page.id,
        parent_entity_type="MEDICATION",
        parent_entity_id=med.id,
        source_section="Discharge Medications",
        source_text="Atorvastatin 40mg PO QHS verified at discharge.",
    )
    db_session.add(ev)
    db_session.commit()

    res = ClinicalIntelligenceService.get_patient_medications(db_session, DEMO_PATIENT_ID, search="Traceable Drug")
    match = next((m for m in res["items"] if m["id"] == med.id), None)
    assert match is not None
    assert match["source"]["document_name"] == doc.file_name
    assert match["source"]["page_number"] == page.page_number
    assert match["source"]["document_id"] == doc.id


# ── 6. Aggregate Summary ──────────────────────────────────────────────────────

def test_patient_intelligence_summary_aggregation(db_session: Session):
    res = ClinicalIntelligenceService.get_patient_intelligence_summary(db_session, DEMO_PATIENT_ID)
    assert "medications" in res
    assert "investigations" in res
    assert "outstanding_items" in res
    assert res["medications"]["total_count"] >= 0
    assert res["investigations"]["total_count"] >= 0
    assert res["outstanding_items"]["open_count"] >= 0


# ── 7. API Authorization & Error Handling ─────────────────────────────────────

def test_api_medications_unauthenticated_401():
    response = client.get(f"/api/v1/patients/{DEMO_PATIENT_ID}/medications")
    assert response.status_code == 401


def test_api_medications_unauthorized_403(auth_headers_doctor):
    """Doctor without assignment to unauthorized patient gets 403."""
    response = client.get(
        f"/api/v1/patients/{UNAUTHORIZED_PATIENT_ID}/medications",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 403


def test_api_medications_not_found_404(auth_headers_doctor):
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(
        f"/api/v1/patients/{non_existent_id}/medications",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 404


def test_api_medication_changes_success(auth_headers_doctor):
    response = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/medication-changes",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary" in data


def test_api_investigations_success(auth_headers_doctor):
    response = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/investigations",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary" in data


def test_api_outstanding_items_success(auth_headers_doctor):
    response = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/outstanding-items",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary" in data


def test_api_intelligence_summary_success(auth_headers_doctor):
    response = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/intelligence/summary",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 200
    data = response.json()
    assert "medications" in data
    assert "investigations" in data
    assert "outstanding_items" in data


def test_api_audit_logging_zero_phi(auth_headers_doctor, db_session: Session):
    """Calling intelligence API logs audit event with ZERO PHI."""
    response = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/medications",
        headers=auth_headers_doctor,
    )
    assert response.status_code == 200

    # Query latest audit event
    audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "VIEW_PATIENT_MEDICATIONS")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert audit is not None
    assert audit.resource_type == "PATIENT_MEDICATIONS"
    assert audit.resource_id == DEMO_PATIENT_ID

    # Ensure zero PHI in metadata
    if audit.metadata_json:
        meta = json.loads(audit.metadata_json)
        assert "patient_name" not in meta
        assert "patient_mrn" not in meta
        assert "ssn" not in meta
        assert "drug_name" not in meta
        assert "dosage" not in meta
