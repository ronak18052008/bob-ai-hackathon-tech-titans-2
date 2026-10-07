"""
MedBrief AI — AI Clinical Summary Automated Test Suite
Step 12: AI Clinical Summary + Evidence/Source Reference Layer

Comprehensive tests verifying:
1. Summary generation across all modes:
   - QUICK_CLINICAL
   - DETAILED_CLINICAL
   - MEDICATION
   - INVESTIGATION
2. Insufficient information handling:
   - Returns "Insufficient information in the uploaded record." when patient has no records
3. Hallucination guard:
   - Rejects or flags citations referencing non-existent or foreign document IDs
   - Neutralizes unsolicited treatment recommendation language
4. Evidence persistence & traceability:
   - Creates EvidenceReference rows with parent_entity_type="SUMMARY"
   - Preloads document name and page number on detail retrieval
5. Version history & non-destructive generation:
   - Multiple summaries for the same patient without overwriting
6. REST API Endpoints:
   - POST /api/v1/patients/{id}/summaries
   - GET /api/v1/patients/{id}/summaries
   - GET /api/v1/summaries/{id}
7. Security & Compliance:
   - 401 Unauthenticated
   - 403 Unauthorized clinician access
   - 404 Patient / Summary not found
   - Zero-PHI audit logging
8. Error resilience:
   - Rate limit (429), Timeout (504), Gateway error (502)
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.main import app
from src.backend.db.connection import SessionLocal
from src.backend.db.models import (
    User,
    Patient,
    Document,
    DocumentPage,
    ClinicalEvent,
    Medication,
    MedicationChange,
    Investigation,
    OutstandingItem,
    Summary,
    EvidenceReference,
    AuditEvent,
    generate_uuid,
)
from src.backend.auth.security import create_access_token
from src.backend.ai.gateway import AIGateway
from src.backend.ai.metadata import AIGenerationMetadata
from src.backend.ai.errors import (
    AIRateLimitError,
    AITimeoutError,
    AIProviderError,
)
from src.backend.ai.summary_schemas import (
    SummaryType,
    StructuredClinicalSummaryOutput,
    StructuredSummarySection,
    SummaryStatement,
    SummaryEvidenceCitation,
)
from src.backend.ai.summary_service import (
    ClinicalSummaryService,
    get_summary_service,
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
            extracted_text="Discharge Medications: Atorvastatin 40mg PO QHS. Metformin 500mg BID. Awaiting echocardiogram results.",
        )
        db_session.add(page)
        db_session.commit()
        db_session.refresh(page)

    return doc, page


def create_mock_structured_summary(patient_id: str, doc_id: str, summary_type: str = "QUICK_CLINICAL"):
    """Helper creating mock AI response conforming to StructuredClinicalSummaryOutput."""
    return StructuredClinicalSummaryOutput(
        patient_id=patient_id,
        patient_name="Johnathan Doe",
        summary_type=summary_type,
        title=f"Clinical Summary ({summary_type})",
        overview="57-year-old male with acute NSTEMI successfully managed with medical therapy and catheterization.",
        sections=[
            StructuredSummarySection(
                section_key="current_medications",
                title="Active Medications",
                summary_text="Patient is maintained on guideline-directed medical therapy.",
                bullet_points=[
                    SummaryStatement(
                        statement="Atorvastatin 40mg daily prescribed for secondary prevention.",
                        citations=[
                            SummaryEvidenceCitation(
                                document_id=doc_id,
                                page_number=1,
                                source_snippet="Atorvastatin 40mg PO QHS",
                                source_section="Discharge Medications",
                            )
                        ],
                        is_uncertain=False,
                    )
                ],
            ),
            StructuredSummarySection(
                section_key="outstanding_items",
                title="Outstanding Diagnostics & Follow-Up",
                bullet_points=[
                    SummaryStatement(
                        statement="Outpatient transthoracic echocardiogram is pending review.",
                        citations=[
                            SummaryEvidenceCitation(
                                document_id=doc_id,
                                page_number=1,
                                source_snippet="Awaiting echocardiogram results",
                                source_section="Follow-up Plan",
                            )
                        ],
                        is_uncertain=False,
                    )
                ],
            ),
        ],
        overall_evidence_count=2,
        has_insufficient_data=False,
    )


# ── 1. Service Layer Tests ────────────────────────────────────────────────────

def test_generate_quick_clinical_summary(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "QUICK_CLINICAL")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-123",
        operation="generate_summary_quick_clinical",
        latency_ms=150.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary = service.generate_summary(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
    )

    assert summary is not None
    assert summary.summary_type == "QUICK_CLINICAL"
    assert summary.patient_id == DEMO_PATIENT_ID
    assert summary.status == "GENERATED"
    assert summary.is_ai_generated is True
    assert summary.model_name == "gemini-2.5-flash"

    # Verify evidence references created
    evidence = service.get_summary_evidence(db_session, summary.id)
    assert len(evidence) >= 1
    assert evidence[0].parent_entity_type == "SUMMARY"
    assert evidence[0].parent_entity_id == summary.id
    assert evidence[0].document_id == doc.id


def test_generate_detailed_clinical_summary(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "DETAILED_CLINICAL")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-det-123",
        operation="generate_summary_detailed_clinical",
        latency_ms=210.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary = service.generate_summary(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        summary_type="DETAILED_CLINICAL",
    )

    assert summary.summary_type == "DETAILED_CLINICAL"
    content = json.loads(summary.content)
    assert content["summary_type"] == "DETAILED_CLINICAL"


def test_generate_medication_summary(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "MEDICATION")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-med-123",
        operation="generate_summary_medication",
        latency_ms=180.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary = service.generate_summary(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        summary_type="MEDICATION",
    )

    assert summary.summary_type == "MEDICATION"


def test_generate_investigation_summary(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "INVESTIGATION")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-inv-123",
        operation="generate_summary_investigation",
        latency_ms=195.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary = service.generate_summary(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        summary_type="INVESTIGATION",
    )

    assert summary.summary_type == "INVESTIGATION"


def test_generate_summary_empty_patient_records(db_session: Session):
    """Test generating a summary when the patient has zero documents and zero clinical records."""
    # Create empty patient
    empty_patient = Patient(
        id=generate_uuid(),
        first_name="Empty",
        last_name="RecordPatient",
        mrn=f"MRN-EMPTY-{generate_uuid()[:6]}",
        gender="Other",
    )
    db_session.add(empty_patient)
    db_session.commit()

    mock_gateway = MagicMock(spec=AIGateway)
    service = ClinicalSummaryService(gateway=mock_gateway)

    summary = service.generate_summary(
        db=db_session,
        patient_id=empty_patient.id,
        summary_type="QUICK_CLINICAL",
    )

    # LLM should not even be called when there's no data
    mock_gateway.generate_structured.assert_not_called()

    assert summary is not None
    assert summary.patient_id == empty_patient.id
    content = json.loads(summary.content)
    assert content["has_insufficient_data"] is True
    assert "Insufficient information in the uploaded record." in content["overview"]


def test_hallucination_guard_rejects_foreign_doc_id(db_session: Session, test_doc_and_page):
    """Verify that hallucinated or non-existent document IDs are stripped and flagged uncertain."""
    doc, page = test_doc_and_page
    fake_doc_id = "00000000-0000-0000-0000-000000000000"

    mock_output = StructuredClinicalSummaryOutput(
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
        title="Hallucination Test",
        overview="Testing hallucination filter.",
        sections=[
            StructuredSummarySection(
                section_key="test",
                title="Test Section",
                bullet_points=[
                    SummaryStatement(
                        statement="Patient was prescribed hypothetical medication.",
                        citations=[
                            SummaryEvidenceCitation(
                                document_id=fake_doc_id,
                                page_number=99,
                                source_snippet="Invented quote not in DB",
                            )
                        ],
                        is_uncertain=False,
                    )
                ],
            )
        ],
    )
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-hal-1",
        operation="generate_summary_quick_clinical",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary = service.generate_summary(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
    )

    content = json.loads(summary.content)
    bullet = content["sections"][0]["bullet_points"][0]
    # The hallucinated citation should be filtered out
    assert len(bullet["citations"]) == 0
    # The statement must be flagged as uncertain
    assert bullet["is_uncertain"] is True
    assert "Citation unverified" in bullet["uncertainty_note"]


def test_recommendation_language_neutralization(db_session: Session, test_doc_and_page):
    """Verify that unsolicited treatment recommendation language is neutralized in overview."""
    doc, page = test_doc_and_page

    mock_output = StructuredClinicalSummaryOutput(
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
        title="Recommendation Test",
        overview="We recommend starting high-dose atorvastatin immediately.",
        sections=[],
    )
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-rec-1",
        operation="generate_summary_quick_clinical",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary = service.generate_summary(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
    )

    content = json.loads(summary.content)
    assert "We recommend starting" not in content["overview"]
    assert "Documented consideration:" in content["overview"]


def test_multiple_summaries_version_history(db_session: Session, test_doc_and_page):
    """Verify multiple summaries can be created for the same patient without overwrite."""
    doc, page = test_doc_and_page
    mock_output_1 = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "QUICK_CLINICAL")
    mock_output_2 = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "DETAILED_CLINICAL")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-hist-1",
        operation="generate_summary_quick_clinical",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.side_effect = [
        (mock_output_1, mock_metadata),
        (mock_output_2, mock_metadata),
    ]

    service = ClinicalSummaryService(gateway=mock_gateway)
    summary_1 = service.generate_summary(db=db_session, patient_id=DEMO_PATIENT_ID, summary_type="QUICK_CLINICAL")
    summary_2 = service.generate_summary(db=db_session, patient_id=DEMO_PATIENT_ID, summary_type="DETAILED_CLINICAL")

    assert summary_1.id != summary_2.id

    result = service.list_patient_summaries(db=db_session, patient_id=DEMO_PATIENT_ID)
    summary_ids = [s["id"] for s in result["items"]]
    assert summary_1.id in summary_ids
    assert summary_2.id in summary_ids


# ── 2. REST API Endpoints Tests ───────────────────────────────────────────────

def test_api_generate_summary_success(auth_headers_doctor, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "QUICK_CLINICAL")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="api-req-1",
        operation="generate_summary_quick_clinical",
        latency_ms=120.0,
        success=True,
    )

    with patch.object(ClinicalSummaryService, "generate_summary") as mock_gen:
        # Construct summary model
        db = SessionLocal()
        created_summary = Summary(
            id=generate_uuid(),
            patient_id=DEMO_PATIENT_ID,
            summary_type="QUICK_CLINICAL",
            title="Clinical Summary (Quick)",
            content=json.dumps(mock_output.model_dump()),
            status="GENERATED",
            is_ai_generated=True,
            model_name="gemini-2.5-flash",
        )
        db.add(created_summary)
        db.commit()
        db.refresh(created_summary)
        mock_gen.return_value = created_summary

        res = client.post(
            f"/api/v1/patients/{DEMO_PATIENT_ID}/summaries",
            headers=auth_headers_doctor,
            json={"summary_type": "QUICK_CLINICAL", "custom_instructions": "Focus on discharge meds"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == created_summary.id
        assert data["summary_type"] == "QUICK_CLINICAL"
        assert "structured_content" in data
        assert data["patient_id"] == DEMO_PATIENT_ID
        db.close()


def test_api_list_patient_summaries(auth_headers_doctor):
    res = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/summaries?page=1&page_size=10",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["patient_id"] == DEMO_PATIENT_ID


def test_api_get_summary_detail(auth_headers_doctor, db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "QUICK_CLINICAL")

    summary = Summary(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
        title="Detail Test Summary",
        content=json.dumps(mock_output.model_dump()),
        status="GENERATED",
        is_ai_generated=True,
        model_name="gemini-2.5-flash",
    )
    db_session.add(summary)

    ev_ref = EvidenceReference(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        document_id=doc.id,
        document_page_id=page.id,
        parent_entity_type="SUMMARY",
        parent_entity_id=summary.id,
        source_section="Discharge Plan",
        source_text="Follow-up with cardiology in 2 weeks",
        source_type="PDF_TEXT",
    )
    db_session.add(ev_ref)
    db_session.commit()

    res = client.get(
        f"/api/v1/summaries/{summary.id}",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == summary.id
    assert data["title"] == "Detail Test Summary"
    assert len(data["evidence_references"]) >= 1
    assert data["evidence_references"][0]["document_name"] == doc.file_name


# ── 3. Authorization & Security Tests ─────────────────────────────────────────

def test_endpoints_unauthenticated_401():
    res1 = client.post(f"/api/v1/patients/{DEMO_PATIENT_ID}/summaries", json={"summary_type": "QUICK_CLINICAL"})
    assert res1.status_code == 401

    res2 = client.get(f"/api/v1/patients/{DEMO_PATIENT_ID}/summaries")
    assert res2.status_code == 401

    res3 = client.get("/api/v1/summaries/some-id")
    assert res3.status_code == 401


def test_endpoints_unauthorized_patient_403(auth_headers_doctor, db_session: Session):
    # Ensure unauthorized patient exists
    unauth = db_session.query(Patient).filter(Patient.id == UNAUTHORIZED_PATIENT_ID).first()
    if not unauth:
        unauth = Patient(
            id=UNAUTHORIZED_PATIENT_ID,
            first_name="Jane",
            last_name="Private",
            mrn="MRN-PRIV-9999",
        )
        db_session.add(unauth)
        db_session.commit()

    res1 = client.post(
        f"/api/v1/patients/{UNAUTHORIZED_PATIENT_ID}/summaries",
        headers=auth_headers_doctor,
        json={"summary_type": "QUICK_CLINICAL"},
    )
    assert res1.status_code == 403

    res2 = client.get(
        f"/api/v1/patients/{UNAUTHORIZED_PATIENT_ID}/summaries",
        headers=auth_headers_doctor,
    )
    assert res2.status_code == 403


def test_patient_not_found_404(auth_headers_doctor):
    non_existent = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    res = client.get(
        f"/api/v1/patients/{non_existent}/summaries",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 404


def test_summary_not_found_404(auth_headers_doctor):
    non_existent = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    res = client.get(
        f"/api/v1/summaries/{non_existent}",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 404


def test_audit_event_logged_zero_phi(auth_headers_doctor, db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_summary(DEMO_PATIENT_ID, doc.id, "QUICK_CLINICAL")

    summary = Summary(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        summary_type="QUICK_CLINICAL",
        title="Audit Test Summary",
        content=json.dumps(mock_output.model_dump()),
        status="GENERATED",
        is_ai_generated=True,
    )
    db_session.add(summary)
    db_session.commit()

    # Trigger GET summary
    res = client.get(f"/api/v1/summaries/{summary.id}", headers=auth_headers_doctor)
    assert res.status_code == 200

    # Query latest audit event for this resource
    audit = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.resource_type == "PATIENT_SUMMARY",
            AuditEvent.resource_id == summary.id,
            AuditEvent.action == "VIEW_SUMMARY_DETAIL",
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert audit is not None
    # Verify zero PHI in metadata
    if audit.metadata_json:
        assert "Johnathan" not in audit.metadata_json
        assert "Doe" not in audit.metadata_json


def test_gateway_rate_limit_maps_to_429(auth_headers_doctor):
    with patch.object(ClinicalSummaryService, "generate_summary") as mock_gen:
        mock_gen.side_effect = AIRateLimitError("Rate limit hit")

        res = client.post(
            f"/api/v1/patients/{DEMO_PATIENT_ID}/summaries",
            headers=auth_headers_doctor,
            json={"summary_type": "QUICK_CLINICAL"},
        )
        assert res.status_code == 429
        assert "rate limit exceeded" in res.json()["detail"].lower()


def test_gateway_timeout_maps_to_504(auth_headers_doctor):
    with patch.object(ClinicalSummaryService, "generate_summary") as mock_gen:
        mock_gen.side_effect = AITimeoutError()

        res = client.post(
            f"/api/v1/patients/{DEMO_PATIENT_ID}/summaries",
            headers=auth_headers_doctor,
            json={"summary_type": "QUICK_CLINICAL"},
        )
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()
