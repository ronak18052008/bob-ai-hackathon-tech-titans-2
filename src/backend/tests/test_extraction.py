"""
MedBrief AI — Medical Information Extraction Tests
Step 9: Medical Information Extraction

Comprehensive test suite verifying all 25 clinical extraction requirements:
1. Safe date parsing across precisions (EXACT, MONTH_YEAR, YEAR_ONLY, APPROXIMATE, UNKNOWN)
2. Schema validation for ExtractedClinicalDossier
3. Prompt template rendering and rule adherence
4. Page text extraction from stored PDF via pypdf
5. Non-text pages handled safely without faking OCR
6. Clinical events persistence and precision
7. Conditions extraction with negation handling ([Ruled Out / Denied])
8. Conditions extraction with uncertainty preservation ([Suspected], conflict details)
9. Medications persistence with dosage, frequency, and route
10. Investigations persistence with abnormal flags and reference ranges
11. Procedures persistence as clinical events
12. Follow-up instructions persistence as OutstandingItems
13. EvidenceReference creation with source page and authentic snippet
14. Original wording preservation
15. Processing job progress and status transitions
16. Partial failure handling (PARTIAL status, failed_pages list, successful entities retained)
17. Total failure handling (FAILED status)
18. Idempotency on re-extraction / retry (no duplicates)
19. Preservation of human-entered records during idempotency cleanup
20. REST endpoint POST /api/v1/documents/{id}/extract unauthenticated rejection (HTTP 401)
21. REST endpoint POST /api/v1/documents/{id}/extract unauthorized patient rejection (HTTP 403)
22. REST endpoint POST /api/v1/documents/{id}/extract nonexistent document (HTTP 404)
23. REST endpoint GET /api/v1/documents/{id}/extraction unauthenticated rejection (HTTP 401)
24. REST endpoint GET /api/v1/documents/{id}/extraction unauthorized patient rejection (HTTP 403)
25. End-to-end extraction via API with job updates and audit event logging
"""

import io
from datetime import datetime, date, timezone
from unittest.mock import MagicMock, patch
import pytest
from pypdf import PdfWriter
from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.db.connection import SessionLocal
from src.backend.db.models import (
    Document,
    DocumentPage,
    ProcessingJob,
    ClinicalEvent,
    Medication,
    Investigation,
    OutstandingItem,
    EvidenceReference,
    AuditEvent,
    generate_uuid,
    utc_now,
)
from src.backend.storage.document_storage import store_document_bytes
from src.backend.ai.extraction_service import (
    ExtractionService,
    get_extraction_service,
    parse_date_safely,
)
from src.backend.ai.extraction_schemas import (
    ExtractedClinicalDossier,
    ExtractedClinicalEvent,
    ExtractedCondition,
    ExtractedMedication,
    ExtractedInvestigation,
    ExtractedProcedure,
    ExtractedFollowUp,
)
from src.backend.ai.extraction_prompts import get_medical_extraction_template
from src.backend.ai.metadata import AIGenerationMetadata
from src.backend.ai.errors import AIInvalidResponseError

client = TestClient(app)

DOCTOR_CREDENTIALS = {
    "email": "dr.sarah.chen@demo-clinic.test",
    "password": "MedBrief2026!",
}

ASSIGNED_PATIENT_ID = "22222222-2222-4000-8000-222222222222"  # Johnathan Doe
UNASSIGNED_PATIENT_ID = "22222222-2222-4000-8000-222222222299"  # Arthur Pendelton


def create_minimal_pdf_bytes_with_text(text: str = "Synthetic Clinical Progress Note") -> bytes:
    """Generate in-memory PDF with latin-1 encoded text stream."""
    safe_text = text.replace("(", "").replace(")", "")
    raw = f"""%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj
4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
5 0 obj <</Length {len(safe_text) + 40}>>
stream
BT
/F1 12 Tf
72 712 Td
({safe_text}) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000222 00000 n 
0000000295 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
400
%%EOF"""
    return raw.encode("latin-1")


def create_blank_pdf_bytes() -> bytes:
    """Generate in-memory blank PDF with 0 extractable characters."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.fixture(scope="module")
def doctor_token():
    res = client.post("/api/v1/auth/login", json=DOCTOR_CREDENTIALS)
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def sample_clinical_dossier():
    """Deterministic synthetic clinical dossier for extraction tests."""
    return ExtractedClinicalDossier(
        document_type_detected="Discharge Summary",
        encounter_date="2026-04-10",
        events=[
            ExtractedClinicalEvent(
                title="Emergency Admission for Acute Chest Pain",
                event_type="admission",
                event_date="2026-04-10",
                date_precision="EXACT",
                description="Patient presented with acute retrosternal chest pain.",
                source_snippet="Patient presented to the emergency department on 2026-04-10 with acute chest pain.",
                confidence=0.98,
            ),
            ExtractedClinicalEvent(
                title="Cardiac Monitoring",
                event_type="observation",
                event_date="2026-04",
                date_precision="MONTH_YEAR",
                description="Telemetry revealed sinus rhythm.",
                source_snippet="Telemetry in April 2026 revealed normal sinus rhythm.",
                confidence=0.92,
            ),
        ],
        conditions=[
            ExtractedCondition(
                condition_name="Hypertension",
                clinical_status="active",
                onset_date="2020",
                original_text="Longstanding history of primary hypertension",
                source_snippet="Past Medical History: Longstanding history of primary hypertension since 2020.",
                confidence=0.95,
            ),
            ExtractedCondition(
                condition_name="Diabetes Mellitus",
                clinical_status="ruled_out",
                is_negated=True,
                original_text="No history of diabetes mellitus",
                source_snippet="Patient denies any prior history of diabetes mellitus.",
                confidence=0.99,
            ),
            ExtractedCondition(
                condition_name="Community Acquired Pneumonia",
                clinical_status="suspected",
                is_uncertain=True,
                uncertainty_note="Possible early infiltrates on chest X-ray",
                original_text="Possible community-acquired pneumonia",
                source_snippet="Chest X-ray shows possible community-acquired pneumonia.",
                confidence=0.75,
            ),
        ],
        medications=[
            ExtractedMedication(
                medication_name="Lisinopril",
                dosage="10",
                dose_unit="mg",
                route="oral",
                frequency="daily",
                status="ACTIVE",
                start_date="2026-04-11",
                original_text="Lisinopril 10 mg PO daily",
                source_snippet="Prescribed Lisinopril 10 mg PO daily starting 2026-04-11.",
                confidence=0.98,
            ),
            ExtractedMedication(
                medication_name="Metoprolol Tartrate",
                dosage="25",
                dose_unit="mg",
                route="oral",
                frequency="twice daily",
                status="STOPPED",
                stop_date="2026-04-10",
                original_text="Metoprolol 25 mg bid",
                source_snippet="Metoprolol 25 mg bid was discontinued upon discharge.",
                confidence=0.95,
            ),
        ],
        investigations=[
            ExtractedInvestigation(
                investigation_name="Serum Troponin I",
                investigation_type="LAB",
                ordered_date="2026-04-10",
                result_date="2026-04-10",
                result_text="0.02 ng/mL",
                reference_range="< 0.04 ng/mL",
                is_abnormal=False,
                status="COMPLETED",
                clinical_urgency="NORMAL",
                source_snippet="Troponin I at 14:00 was 0.02 ng/mL (Ref: < 0.04 ng/mL).",
                confidence=0.99,
            ),
            ExtractedInvestigation(
                investigation_name="Electrocardiogram (12-Lead)",
                investigation_type="IMAGING",
                ordered_date="2026-04-10",
                result_text="Normal sinus rhythm with no ST elevation.",
                is_abnormal=False,
                status="COMPLETED",
                clinical_urgency="NORMAL",
                source_snippet="ECG showed normal sinus rhythm without acute ischemic changes.",
                confidence=0.95,
            ),
        ],
        procedures=[
            ExtractedProcedure(
                procedure_name="Diagnostic Coronary Angiogram",
                procedure_date="2026-04-11",
                outcome="Normal coronary arteries without obstructive lesions",
                source_snippet="Underwent diagnostic coronary angiogram on 2026-04-11 with normal arteries.",
                confidence=0.97,
            ),
        ],
        follow_ups=[
            ExtractedFollowUp(
                instruction="Follow up with outpatient cardiology in 2 weeks",
                specialty_or_provider="Cardiology",
                target_date="2026-04-25",
                source_snippet="Follow-up with Dr. Reynolds (Cardiology) in 2 weeks for treadmill stress testing.",
                confidence=0.94,
            ),
        ],
    )


# ── TEST 1: Safe Date Parsing ────────────────────────────────────────────────
def test_parse_date_safely():
    # Exact date
    dt, prec = parse_date_safely("2026-04-10")
    assert prec == "EXACT"
    assert dt is not None
    assert dt.year == 2026 and dt.month == 4 and dt.day == 10

    # Month and year
    dt, prec = parse_date_safely("2026-04")
    assert prec == "MONTH_YEAR"
    assert dt is not None
    assert dt.year == 2026 and dt.month == 4 and dt.day == 1

    # Year only
    dt, prec = parse_date_safely("2024")
    assert prec == "YEAR_ONLY"
    assert dt is not None
    assert dt.year == 2024 and dt.month == 1 and dt.day == 1

    # Relative or descriptive string (never invent date)
    dt, prec = parse_date_safely("three weeks ago")
    assert prec == "APPROXIMATE"
    assert dt is None

    # Blank or empty
    dt, prec = parse_date_safely("")
    assert prec == "UNKNOWN"
    assert dt is None

    dt, prec = parse_date_safely(None)
    assert prec == "UNKNOWN"
    assert dt is None


# ── TEST 2: Schema Validation ────────────────────────────────────────────────
def test_extraction_schemas_validation(sample_clinical_dossier):
    assert len(sample_clinical_dossier.events) == 2
    assert len(sample_clinical_dossier.conditions) == 3
    assert len(sample_clinical_dossier.medications) == 2
    assert len(sample_clinical_dossier.investigations) == 2
    assert len(sample_clinical_dossier.procedures) == 1
    assert len(sample_clinical_dossier.follow_ups) == 1

    # Serializes to dictionary properly
    dumped = sample_clinical_dossier.model_dump()
    assert dumped["conditions"][1]["is_negated"] is True
    assert dumped["conditions"][2]["is_uncertain"] is True


# ── TEST 3: Prompt Template Rendering ────────────────────────────────────────
def test_extraction_prompt_rendering():
    template = get_medical_extraction_template()
    prompt = template.render(context_input="Patient was discharged on Aspirin 81 mg.")

    assert "CRITICAL RULES:" in prompt
    assert "Negation:" in prompt
    assert "Uncertainty:" in prompt
    assert "Patient was discharged on Aspirin 81 mg." in prompt


# ── TEST 4: pypdf Page Text Extraction ───────────────────────────────────────
def test_ensure_document_pages_extracts_text():
    db = SessionLocal()
    try:
        doc_id = generate_uuid()
        pdf_bytes = create_minimal_pdf_bytes_with_text("Patient admitted with severe asthma exacerbation.")
        storage_rel_path = store_document_bytes(ASSIGNED_PATIENT_ID, doc_id, pdf_bytes)

        doc = Document(
            id=doc_id,
            patient_id=ASSIGNED_PATIENT_ID,
            file_name="asthma_admission.pdf",
            file_type="application/pdf",
            storage_path=storage_rel_path,
            document_type="CLINIC_CONSULTATION",
            file_size=len(pdf_bytes),
            page_count=1,
            status="UPLOADED",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(doc)
        db.commit()

        service = ExtractionService()
        pages = service.ensure_document_pages(db, doc)

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "asthma exacerbation" in pages[0].extracted_text.lower()
        assert pages[0].processing_status == "EXTRACTED"
    finally:
        db.close()


# ── TEST 5: Non-text Page Handled Without Faking OCR ─────────────────────────
def test_ensure_document_pages_handles_blank_page():
    db = SessionLocal()
    try:
        doc_id = generate_uuid()
        blank_bytes = create_blank_pdf_bytes()
        storage_rel_path = store_document_bytes(ASSIGNED_PATIENT_ID, doc_id, blank_bytes)

        doc = Document(
            id=doc_id,
            patient_id=ASSIGNED_PATIENT_ID,
            file_name="scanned_image.pdf",
            file_type="application/pdf",
            storage_path=storage_rel_path,
            document_type="OTHER",
            file_size=len(blank_bytes),
            page_count=1,
            status="UPLOADED",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(doc)
        db.commit()

        service = ExtractionService()
        pages = service.ensure_document_pages(db, doc)

        assert len(pages) == 1
        assert pages[0].extracted_text is None
        assert pages[0].processing_status == "PENDING"
    finally:
        db.close()


# ── TEST 6: Clinical Events Persistence ──────────────────────────────────────
def test_clinical_events_persistence(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()
        if not page:
            page = DocumentPage(
                id=generate_uuid(),
                document_id=doc.id,
                page_number=1,
                extracted_text="Sample text",
                processing_status="EXTRACTED",
            )
            db.add(page)
            db.flush()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        events = db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == doc.id,
            ClinicalEvent.event_type == "admission",
        ).all()
        assert len(events) >= 1
        ev = events[0]
        assert "Emergency Admission" in ev.title
        assert ev.event_date_precision == "EXACT"
        assert ev.is_ai_generated is True
        assert ev.source_page_id == page.id
    finally:
        db.close()


# ── TEST 7: Conditions Extraction with Negation Handling ─────────────────────
def test_conditions_persistence_and_negation(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        negated = db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == doc.id,
            ClinicalEvent.title.like("%Ruled Out%"),
        ).first()

        assert negated is not None
        assert "Diabetes Mellitus" in negated.title
        assert "[Ruled Out / Denied]" in negated.title
    finally:
        db.close()


# ── TEST 8: Conditions Extraction with Uncertainty Preservation ──────────────
def test_conditions_persistence_and_uncertainty(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        uncertain = db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == doc.id,
            ClinicalEvent.title.like("%Suspected%"),
        ).first()

        assert uncertain is not None
        assert "Community Acquired Pneumonia" in uncertain.title
        assert uncertain.is_conflict is True
        assert "Possible early infiltrates" in (uncertain.conflict_details or "")
    finally:
        db.close()


# ── TEST 9: Medications Persistence ──────────────────────────────────────────
def test_medications_persistence(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        lisinopril = db.query(Medication).filter(
            Medication.source_document_id == doc.id,
            Medication.medication_name == "Lisinopril",
        ).first()

        assert lisinopril is not None
        assert lisinopril.dosage == "10"
        assert lisinopril.dose_unit == "mg"
        assert lisinopril.route == "oral"
        assert lisinopril.frequency == "daily"
        assert lisinopril.status == "ACTIVE"
        assert lisinopril.start_date == date(2026, 4, 11)
    finally:
        db.close()


# ── TEST 10: Diagnostic Investigations Persistence ───────────────────────────
def test_investigations_persistence(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        troponin = db.query(Investigation).filter(
            Investigation.source_document_id == doc.id,
            Investigation.investigation_name == "Serum Troponin I",
        ).first()

        assert troponin is not None
        assert troponin.investigation_type == "LAB"
        assert troponin.result_summary == "0.02 ng/mL"
        assert troponin.reference_range == "< 0.04 ng/mL"
        assert troponin.is_abnormal is False
        assert troponin.status == "COMPLETED"
    finally:
        db.close()


# ── TEST 11: Procedures Persistence ──────────────────────────────────────────
def test_procedures_persistence(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        proc = db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == doc.id,
            ClinicalEvent.event_type == "procedure",
        ).first()

        assert proc is not None
        assert "Procedure: Diagnostic Coronary Angiogram" in proc.title
        assert proc.event_date.year == 2026 and proc.event_date.month == 4 and proc.event_date.day == 11
        assert proc.is_ai_generated is True
    finally:
        db.close()


# ── TEST 12: Follow-up Instructions Persistence ──────────────────────────────
def test_follow_ups_persistence(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        fu = db.query(OutstandingItem).filter(
            OutstandingItem.source_document_id == doc.id,
            OutstandingItem.item_type == "FOLLOW_UP",
        ).first()

        assert fu is not None
        assert "Cardiology" in fu.description
        assert fu.due_date == date(2026, 4, 25)
        assert fu.status == "OPEN"
        assert fu.is_ai_generated is True
    finally:
        db.close()


# ── TEST 13: EvidenceReference Creation Per Entity ───────────────────────────
def test_evidence_reference_creation_per_entity(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        evidence_list = db.query(EvidenceReference).filter(
            EvidenceReference.document_id == doc.id,
            EvidenceReference.document_page_id == page.id,
        ).all()

        assert len(evidence_list) >= 6
        parent_types = {e.parent_entity_type for e in evidence_list}
        assert "CLINICAL_EVENT" in parent_types
        assert "MEDICATION" in parent_types
        assert "INVESTIGATION" in parent_types
        assert "OUTSTANDING_ITEM" in parent_types
    finally:
        db.close()


# ── TEST 14: Original Wording Preserved ───────────────────────────────────────
def test_original_wording_preserved(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        cond = db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == doc.id,
            ClinicalEvent.title.like("%Hypertension%"),
        ).first()

        assert cond is not None
        assert "Longstanding history of primary hypertension" in cond.description
    finally:
        db.close()


# ── TEST 15: Idempotency Clears Prior AI Extractions ─────────────────────────
def test_idempotency_clears_prior_ai_extractions(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts1 = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts1)
        db.commit()

        initial_count = db.query(ClinicalEvent).filter(ClinicalEvent.source_document_id == doc.id).count()
        assert initial_count > 0

        # Execute idempotency clean
        service._clear_previous_extractions(db, doc.id)
        db.commit()

        after_clean = db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == doc.id,
            ClinicalEvent.is_ai_generated == True,
        ).count()
        assert after_clean == 0

        evidence_after = db.query(EvidenceReference).filter(EvidenceReference.document_id == doc.id).count()
        assert evidence_after == 0
    finally:
        db.close()


# ── TEST 16: Idempotency Preserves Human Records ─────────────────────────────
def test_idempotency_preserves_human_records():
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()

        human_event = ClinicalEvent(
            id=generate_uuid(),
            patient_id=ASSIGNED_PATIENT_ID,
            event_type="consultation",
            title="Dr. Sarah Chen In-Person Consultation",
            description="Direct manual clinician consultation note.",
            source_document_id=doc.id,
            is_ai_generated=False,  # Human entered
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(human_event)
        db.commit()

        service = ExtractionService()
        service._clear_previous_extractions(db, doc.id)
        db.commit()

        retained = db.query(ClinicalEvent).filter(ClinicalEvent.id == human_event.id).first()
        assert retained is not None
        assert retained.title == "Dr. Sarah Chen In-Person Consultation"
    finally:
        db.close()


# ── TEST 17: Partial Failure Handling ────────────────────────────────────────
def test_partial_failure_handling(sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc_id = generate_uuid()
        pdf_bytes = create_minimal_pdf_bytes_with_text("Page 1 clinical text.")
        rel_path = store_document_bytes(ASSIGNED_PATIENT_ID, doc_id, pdf_bytes)

        doc = Document(
            id=doc_id,
            patient_id=ASSIGNED_PATIENT_ID,
            file_name="multi_page_partial.pdf",
            file_type="application/pdf",
            storage_path=rel_path,
            document_type="DISCHARGE_SUMMARY",
            file_size=len(pdf_bytes),
            page_count=2,
            status="UPLOADED",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(doc)
        db.flush()

        # Seed 2 pages
        p1 = DocumentPage(id=generate_uuid(), document_id=doc.id, page_number=1, extracted_text="Page 1 text", processing_status="PENDING")
        p2 = DocumentPage(id=generate_uuid(), document_id=doc.id, page_number=2, extracted_text="Page 2 text", processing_status="PENDING")
        db.add_all([p1, p2])
        db.commit()

        # Mock gateway: Page 1 succeeds, Page 2 raises AIInvalidResponseError
        mock_gateway = MagicMock()
        mock_meta = AIGenerationMetadata(
            model="gemini-2.5-flash",
            request_id="test_req_partial",
            operation="generate_structured",
            latency_ms=150.0,
            success=True,
        )

        def mock_generate_side_effect(**kwargs):
            if "PAGE NUMBER: 1" in kwargs.get("prompt", ""):
                return sample_clinical_dossier, mock_meta
            raise AIInvalidResponseError(message="Invalid JSON response from model")

        mock_gateway.generate_structured.side_effect = mock_generate_side_effect
        mock_gateway.config.model = "gemini-2.5-flash"

        service = ExtractionService(gateway=mock_gateway)
        result = service.process_document_extraction(db, doc)

        assert result["status"] == "PARTIAL"
        assert result["job_status"] == "PARTIAL"
        assert result["processed_pages"] == 1
        assert 2 in result["failed_pages"]
        assert doc.status == "PARTIAL"
    finally:
        db.close()


# ── TEST 18: Total Failure Handling ──────────────────────────────────────────
def test_total_failure_handling():
    db = SessionLocal()
    try:
        doc_id = generate_uuid()
        pdf_bytes = create_minimal_pdf_bytes_with_text("Failing document text.")
        rel_path = store_document_bytes(ASSIGNED_PATIENT_ID, doc_id, pdf_bytes)

        doc = Document(
            id=doc_id,
            patient_id=ASSIGNED_PATIENT_ID,
            file_name="failing_doc.pdf",
            file_type="application/pdf",
            storage_path=rel_path,
            document_type="DISCHARGE_SUMMARY",
            file_size=len(pdf_bytes),
            page_count=1,
            status="UPLOADED",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(doc)
        db.flush()

        p = DocumentPage(id=generate_uuid(), document_id=doc.id, page_number=1, extracted_text="Failing page text", processing_status="PENDING")
        db.add(p)
        db.commit()

        mock_gateway = MagicMock()
        mock_gateway.generate_structured.side_effect = AIInvalidResponseError(message="Model returned invalid JSON")
        mock_gateway.config.model = "gemini-2.5-flash"

        service = ExtractionService(gateway=mock_gateway)
        result = service.process_document_extraction(db, doc)

        assert result["status"] == "FAILED"
        assert result["job_status"] == "FAILED"
        assert doc.status == "FAILED"
    finally:
        db.close()


# ── TEST 19: REST POST /extract Unauthenticated Rejection ─────────────────────
def test_extract_endpoint_unauthenticated():
    res = client.post("/api/v1/documents/some-id/extract")
    assert res.status_code == 401


# ── TEST 20: REST POST /extract Unauthorized Patient Rejection ────────────────
def test_extract_endpoint_unauthorized_patient(doctor_token):
    db = SessionLocal()
    try:
        # Document belongs to unassigned patient
        doc_id = generate_uuid()
        pdf_bytes = create_blank_pdf_bytes()
        rel_path = store_document_bytes(UNASSIGNED_PATIENT_ID, doc_id, pdf_bytes)

        doc = Document(
            id=doc_id,
            patient_id=UNASSIGNED_PATIENT_ID,
            file_name="unauth_doc.pdf",
            file_type="application/pdf",
            storage_path=rel_path,
            document_type="LAB_PATHOLOGY",
            file_size=len(pdf_bytes),
            page_count=1,
            status="UPLOADED",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(doc)
        db.commit()

        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["detail"]
    finally:
        db.close()


# ── TEST 21: REST POST /extract Nonexistent Document 404 ─────────────────────
def test_extract_endpoint_nonexistent_document(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.post(f"/api/v1/documents/{generate_uuid()}/extract", headers=headers)
    assert res.status_code == 404


# ── TEST 22: REST GET /extraction Unauthenticated Rejection ───────────────────
def test_get_extraction_unauthenticated():
    res = client.get("/api/v1/documents/some-id/extraction")
    assert res.status_code == 401


# ── TEST 23: REST GET /extraction Unauthorized Patient Rejection ──────────────
def test_get_extraction_unauthorized_patient(doctor_token):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == UNASSIGNED_PATIENT_ID).first()
        if not doc:
            doc_id = generate_uuid()
            pdf_bytes = create_blank_pdf_bytes()
            rel_path = store_document_bytes(UNASSIGNED_PATIENT_ID, doc_id, pdf_bytes)
            doc = Document(
                id=doc_id,
                patient_id=UNASSIGNED_PATIENT_ID,
                file_name="unauth_view.pdf",
                file_type="application/pdf",
                storage_path=rel_path,
                document_type="OTHER",
                file_size=len(pdf_bytes),
                page_count=1,
                status="UPLOADED",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(doc)
            db.commit()

        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/documents/{doc.id}/extraction", headers=headers)
        assert res.status_code == 403
    finally:
        db.close()


# ── TEST 24: REST GET /extraction Structured Dossier Retrieval ────────────────
def test_get_extraction_success_structure(doctor_token, sample_clinical_dossier):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.patient_id == ASSIGNED_PATIENT_ID).first()
        page = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()

        service = ExtractionService()
        counts = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        service._persist_page_dossier(db, doc, page, sample_clinical_dossier, counts)
        db.commit()

        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/documents/{doc.id}/extraction", headers=headers)
        assert res.status_code == 200

        data = res.json()
        assert data["document_id"] == doc.id
        assert data["patient_id"] == ASSIGNED_PATIENT_ID
        assert data["counts"]["total"] > 0
        assert len(data["conditions"]) > 0
        assert len(data["medications"]) > 0
        assert len(data["investigations"]) > 0

        # Check evidence reference linked
        first_cond = data["conditions"][0]
        assert first_cond.get("evidence_snippet") is not None
    finally:
        db.close()


# ── TEST 25: End-to-End Extraction API Route with Audit Log ───────────────────
def test_end_to_end_extract_endpoint_success(doctor_token, sample_clinical_dossier):
    db = SessionLocal()
    try:
        # Create fresh document for clean end-to-end extraction test
        doc_id = generate_uuid()
        pdf_bytes = create_minimal_pdf_bytes_with_text("End to end extraction verification note.")
        rel_path = store_document_bytes(ASSIGNED_PATIENT_ID, doc_id, pdf_bytes)

        doc = Document(
            id=doc_id,
            patient_id=ASSIGNED_PATIENT_ID,
            file_name="e2e_extraction_test.pdf",
            file_type="application/pdf",
            storage_path=rel_path,
            document_type="DISCHARGE_SUMMARY",
            file_size=len(pdf_bytes),
            page_count=1,
            status="UPLOADED",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(doc)
        db.commit()

        mock_meta = AIGenerationMetadata(
            model="gemini-2.5-flash",
            request_id="test_req_e2e",
            operation="generate_structured",
            latency_ms=210.0,
            success=True,
        )

        mock_gw = MagicMock()
        mock_gw.generate_structured.return_value = (sample_clinical_dossier, mock_meta)
        mock_gw.config.model = "gemini-2.5-flash"
        mock_service = ExtractionService(gateway=mock_gw)

        app.dependency_overrides[get_extraction_service] = lambda: mock_service
        try:
            headers = {"Authorization": f"Bearer {doctor_token}"}
            res = client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
            assert res.status_code == 200

            resp_json = res.json()
            assert resp_json["status"] == "PROCESSED"
            assert resp_json["job_status"] == "COMPLETED"
            assert resp_json["processed_pages"] == 1
            assert resp_json["extracted_counts"]["events"] >= 1
            assert resp_json["extracted_counts"]["medications"] >= 1

            # Verify audit event was logged without PHI
            audit = (
                db.query(AuditEvent)
                .filter(AuditEvent.resource_id == doc_id, AuditEvent.action == "CLINICAL_EXTRACTION")
                .first()
            )
            assert audit is not None
            assert "CLINICAL_EXTRACTION" in audit.action
            assert "COMPLETED" in (audit.metadata_json or "")
        finally:
            app.dependency_overrides.pop(get_extraction_service, None)
    finally:
        db.close()
