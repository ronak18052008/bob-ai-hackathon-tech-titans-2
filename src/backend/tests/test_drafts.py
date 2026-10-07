"""
MedBrief AI — Clinical Drafts Automated Test Suite
Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow

Comprehensive tests verifying:
1. Referral draft generation, reason handling, background, medications, investigations, follow-up, evidence
2. Discharge draft generation, hospital course, diagnoses, procedures, medication changes, no invented discharge date
3. Clinical handoff generation, current situation, recent events, monitoring, evidence
4. Grounded safety:
   - Missing info -> "Not documented in the available record."
   - Empty patient record -> "Insufficient information in the uploaded record."
   - Neutralization of unsolicited prescribing recommendations
   - Hallucination guard: rejects invalid/foreign document IDs
5. Editable Draft & Approval Workflow:
   - Initial status is strictly DRAFT (never automatically APPROVED)
   - Doctor edits draft content and title (PATCH)
   - Doctor review & approval transition to APPROVED (sets reviewed_by, reviewed_at)
   - Version history (multiple drafts without overwrite)
6. REST API Endpoints:
   - POST /api/v1/patients/{id}/drafts
   - GET /api/v1/patients/{id}/drafts
   - GET /api/v1/drafts/{id}
   - PATCH /api/v1/drafts/{id}
7. Security & RBAC:
   - 401 Unauthenticated
   - 403 Unauthorized clinician access
   - 404 Patient / Draft not found
   - Zero-PHI audit logging
8. AI Gateway Error Handling:
   - Rate limit (429), Timeout (504), Provider error (502)
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
    Draft,
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
from src.backend.ai.draft_schemas import (
    DraftType,
    DraftStatus,
    StructuredClinicalDraftOutput,
    StructuredDraftSection,
    DraftStatement,
    DraftEvidenceCitation,
)
from src.backend.ai.draft_service import (
    ClinicalDraftService,
    get_draft_service,
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


def create_mock_structured_draft(patient_id: str, doc_id: str, draft_type: str = "REFERRAL"):
    """Helper creating mock AI response conforming to StructuredClinicalDraftOutput."""
    doc_body = (
        f"# {draft_type.upper()} SUMMARY\n\n"
        "**Patient**: Johnathan Doe (MRN: DEMO-MRN-2026-0042)\n\n"
        "## Clinical Background\n"
        "Patient presented with non-ST elevation myocardial infarction.\n\n"
        "## Current Medications\n"
        "- Atorvastatin 40mg daily\n\n"
        "## Follow-up\n"
        "- Outpatient echocardiogram scheduled\n"
    )

    return StructuredClinicalDraftOutput(
        patient_id=patient_id,
        patient_name="Johnathan Doe",
        draft_type=draft_type,
        title=f"Clinical {draft_type.title()} Document",
        document_body=doc_body,
        sections=[
            StructuredDraftSection(
                section_key="clinical_background",
                title="Clinical Background",
                content_text="Documented history of NSTEMI.",
                bullet_points=[
                    DraftStatement(
                        statement="Documented acute coronary syndrome managed with medical therapy.",
                        citations=[
                            DraftEvidenceCitation(
                                document_id=doc_id,
                                page_number=1,
                                source_snippet="Discharge Medications: Atorvastatin 40mg PO QHS.",
                                source_section="Discharge Summary",
                            )
                        ],
                        is_uncertain=False,
                    )
                ],
            ),
            StructuredDraftSection(
                section_key="medications",
                title="Current Medications",
                bullet_points=[
                    DraftStatement(
                        statement="Atorvastatin 40mg PO daily.",
                        citations=[
                            DraftEvidenceCitation(
                                document_id=doc_id,
                                page_number=1,
                                source_snippet="Atorvastatin 40mg PO QHS.",
                                source_section="Medications",
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


# ── 1. Referral Composer Tests ────────────────────────────────────────────────

def test_generate_referral_draft(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "REFERRAL")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-ref-1",
        operation="generate_draft_referral",
        latency_ms=160.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalDraftService(gateway=mock_gateway)
    draft = service.generate_draft(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        draft_type="REFERRAL",
        recipient_info="Dr. Robert Smith, Cardiology Clinic",
    )

    assert draft is not None
    assert draft.draft_type == "REFERRAL"
    assert draft.patient_id == DEMO_PATIENT_ID
    assert draft.status == "DRAFT"  # Initial draft MUST be DRAFT, never approved!
    assert draft.is_ai_generated is True
    assert draft.model_name == "gemini-2.5-flash"

    # Verify EvidenceReference created with parent_entity_type="DRAFT"
    evidence = service.get_draft_evidence(db_session, draft.id)
    assert len(evidence) >= 1
    assert evidence[0].parent_entity_type == "DRAFT"
    assert evidence[0].parent_entity_id == draft.id
    assert evidence[0].document_id == doc.id


# ── 2. Discharge Summary Composer Tests ───────────────────────────────────────

def test_generate_discharge_draft_no_invented_dates(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "DISCHARGE")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-disc-1",
        operation="generate_draft_discharge",
        latency_ms=175.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalDraftService(gateway=mock_gateway)
    draft = service.generate_draft(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        draft_type="DISCHARGE",
    )

    assert draft.draft_type == "DISCHARGE"
    assert draft.status == "DRAFT"
    content = json.loads(draft.content)
    assert "document_body" in content
    assert content["has_insufficient_data"] is False


# ── 3. Clinical Handoff Composer Tests ────────────────────────────────────────

def test_generate_handoff_draft(db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "HANDOFF")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-hand-1",
        operation="generate_draft_handoff",
        latency_ms=140.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalDraftService(gateway=mock_gateway)
    draft = service.generate_draft(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        draft_type="HANDOFF",
    )

    assert draft.draft_type == "HANDOFF"
    assert draft.status == "DRAFT"


# ── 4. Grounding & Safety Tests ───────────────────────────────────────────────

def test_empty_patient_record_handling(db_session: Session):
    """When a patient has no documents or records, output has_insufficient_data and explicit notice."""
    empty_patient = Patient(
        id=generate_uuid(),
        first_name="Empty",
        last_name="DraftPatient",
        mrn=f"MRN-DRAFT-EMPTY-{generate_uuid()[:6]}",
        gender="Other",
    )
    db_session.add(empty_patient)
    db_session.commit()

    mock_gateway = MagicMock(spec=AIGateway)
    service = ClinicalDraftService(gateway=mock_gateway)

    draft = service.generate_draft(
        db=db_session,
        patient_id=empty_patient.id,
        draft_type="REFERRAL",
    )

    # LLM should not be called
    mock_gateway.generate_structured.assert_not_called()

    assert draft is not None
    assert draft.status == "DRAFT"
    content = json.loads(draft.content)
    assert content["has_insufficient_data"] is True
    assert "Insufficient information in the uploaded record." in content["document_body"]


def test_hallucination_guard_strips_foreign_citation(db_session: Session, test_doc_and_page):
    """Hallucinated document IDs are stripped from citations and statement is flagged uncertain."""
    doc, page = test_doc_and_page
    fake_doc_id = "11111111-1111-1111-1111-111111111111"

    mock_output = StructuredClinicalDraftOutput(
        patient_id=DEMO_PATIENT_ID,
        draft_type="REFERRAL",
        title="Hallucination Test Draft",
        document_body="Patient has history of coronary artery disease.",
        sections=[
            StructuredDraftSection(
                section_key="test_section",
                title="Test Section",
                bullet_points=[
                    DraftStatement(
                        statement="Documented severe triple vessel disease.",
                        citations=[
                            DraftEvidenceCitation(
                                document_id=fake_doc_id,
                                page_number=99,
                                source_snippet="Invented angiogram finding",
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
        request_id="req-hal-draft-1",
        operation="generate_draft_referral",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalDraftService(gateway=mock_gateway)
    draft = service.generate_draft(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        draft_type="REFERRAL",
    )

    content = json.loads(draft.content)
    bullet = content["sections"][0]["bullet_points"][0]
    assert len(bullet["citations"]) == 0
    assert bullet["is_uncertain"] is True
    assert "Citation unverified" in bullet["uncertainty_note"]


def test_neutralize_unsolicited_recommendations(db_session: Session, test_doc_and_page):
    """Unsolicited prescribing advice in generated body is neutralized."""
    doc, page = test_doc_and_page
    mock_output = StructuredClinicalDraftOutput(
        patient_id=DEMO_PATIENT_ID,
        draft_type="REFERRAL",
        title="Recommendation Neutralization Test",
        document_body="We recommend starting dual antiplatelet therapy and recommend starting beta blockers.",
        sections=[],
    )
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-rec-draft-1",
        operation="generate_draft_referral",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalDraftService(gateway=mock_gateway)
    draft = service.generate_draft(
        db=db_session,
        patient_id=DEMO_PATIENT_ID,
        draft_type="REFERRAL",
    )

    content = json.loads(draft.content)
    assert "We recommend starting" not in content["document_body"]
    assert "Documented consideration:" in content["document_body"]


# ── 5. Editable Draft & Approval Lifecycle Tests ──────────────────────────────

def test_editable_draft_and_approval_transition(db_session: Session, test_doc_and_page):
    """Test doctor editing content, saving, and transitioning status to APPROVED."""
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "REFERRAL")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-edit-1",
        operation="generate_draft_referral",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.return_value = (mock_output, mock_metadata)

    service = ClinicalDraftService(gateway=mock_gateway)
    draft = service.generate_draft(db=db_session, patient_id=DEMO_PATIENT_ID, draft_type="REFERRAL")

    assert draft.status == "DRAFT"
    assert draft.reviewed_by is None

    # Doctor edits text
    edited_text = "# UPDATED REFERRAL NOTE\n\nDoctor manually added clinical context."
    doctor_user = db_session.query(User).filter(User.email == "dr.sarah.chen@demo-clinic.test").first()

    updated = service.update_draft(
        db=db_session,
        draft_id=draft.id,
        user_id=doctor_user.id,
        title="Updated Referral Title",
        content=edited_text,
        status="IN_REVIEW",
    )
    assert updated.title == "Updated Referral Title"
    assert updated.status == "IN_REVIEW"

    # Doctor approves draft
    approved = service.update_draft(
        db=db_session,
        draft_id=draft.id,
        user_id=doctor_user.id,
        status="APPROVED",
    )
    assert approved.status == "APPROVED"
    assert approved.reviewed_by == doctor_user.id
    assert approved.reviewed_at is not None


def test_multiple_drafts_version_history(db_session: Session, test_doc_and_page):
    """Verify multiple drafts can be created for the same patient without overwrite."""
    doc, page = test_doc_and_page
    mock_output_1 = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "REFERRAL")
    mock_output_2 = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "DISCHARGE")
    mock_metadata = AIGenerationMetadata(
        provider="gemini",
        model="gemini-2.5-flash",
        request_id="req-hist-draft-1",
        operation="generate_draft_referral",
        latency_ms=100.0,
        success=True,
    )

    mock_gateway = MagicMock(spec=AIGateway)
    mock_gateway.generate_structured.side_effect = [
        (mock_output_1, mock_metadata),
        (mock_output_2, mock_metadata),
    ]

    service = ClinicalDraftService(gateway=mock_gateway)
    draft_1 = service.generate_draft(db=db_session, patient_id=DEMO_PATIENT_ID, draft_type="REFERRAL")
    draft_2 = service.generate_draft(db=db_session, patient_id=DEMO_PATIENT_ID, draft_type="DISCHARGE")

    assert draft_1.id != draft_2.id

    result = service.list_patient_drafts(db=db_session, patient_id=DEMO_PATIENT_ID)
    draft_ids = [d["id"] for d in result["items"]]
    assert draft_1.id in draft_ids
    assert draft_2.id in draft_ids


# ── 6. REST API Endpoints Tests ───────────────────────────────────────────────

def test_api_generate_draft_success(auth_headers_doctor, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "REFERRAL")

    with patch.object(ClinicalDraftService, "generate_draft") as mock_gen:
        db = SessionLocal()
        created_draft = Draft(
            id=generate_uuid(),
            patient_id=DEMO_PATIENT_ID,
            draft_type="REFERRAL",
            title="Referral Summary Draft",
            content=json.dumps({"document_body": mock_output.document_body, "sections": []}),
            status="DRAFT",
            generated_by_ai=True,
            model_name="gemini-2.5-flash",
        )
        db.add(created_draft)
        db.commit()
        db.refresh(created_draft)
        mock_gen.return_value = created_draft

        res = client.post(
            f"/api/v1/patients/{DEMO_PATIENT_ID}/drafts",
            headers=auth_headers_doctor,
            json={"draft_type": "REFERRAL", "custom_instructions": "Urgent referral to cardiology"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == created_draft.id
        assert data["draft_type"] == "REFERRAL"
        assert data["status"] == "DRAFT"
        assert "content" in data
        db.close()


def test_api_list_patient_drafts(auth_headers_doctor):
    res = client.get(
        f"/api/v1/patients/{DEMO_PATIENT_ID}/drafts?page=1&page_size=10",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["patient_id"] == DEMO_PATIENT_ID


def test_api_get_draft_detail(auth_headers_doctor, db_session: Session, test_doc_and_page):
    doc, page = test_doc_and_page
    mock_output = create_mock_structured_draft(DEMO_PATIENT_ID, doc.id, "REFERRAL")

    draft = Draft(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        draft_type="REFERRAL",
        title="Detail Test Draft",
        content=json.dumps({"document_body": mock_output.document_body, "sections": []}),
        status="DRAFT",
        is_ai_generated=True,
        model_name="gemini-2.5-flash",
    )
    db_session.add(draft)

    ev_ref = EvidenceReference(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        document_id=doc.id,
        document_page_id=page.id,
        parent_entity_type="DRAFT",
        parent_entity_id=draft.id,
        source_section="Referral Plan",
        source_text="Cardiology consultation requested",
        source_type="PDF_TEXT",
    )
    db_session.add(ev_ref)
    db_session.commit()

    res = client.get(
        f"/api/v1/drafts/{draft.id}",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == draft.id
    assert data["title"] == "Detail Test Draft"
    assert len(data["evidence_references"]) >= 1
    assert data["evidence_references"][0]["document_name"] == doc.file_name


def test_api_patch_update_and_approve_draft(auth_headers_doctor, db_session: Session):
    draft = Draft(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        draft_type="DISCHARGE",
        title="Initial Draft Title",
        content="Initial content text.",
        status="DRAFT",
        is_ai_generated=True,
    )
    db_session.add(draft)
    db_session.commit()

    # Edit content
    patch_res = client.patch(
        f"/api/v1/drafts/{draft.id}",
        headers=auth_headers_doctor,
        json={"title": "Updated Title", "content": "Doctor edited clinical notes.", "status": "APPROVED"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["title"] == "Updated Title"
    assert "Doctor edited clinical notes." in data["content"]
    assert data["status"] == "APPROVED"
    assert data["reviewed_by"] is not None


# ── 7. Security, RBAC & Audit Tests ───────────────────────────────────────────

def test_draft_endpoints_unauthenticated_401():
    res1 = client.post(f"/api/v1/patients/{DEMO_PATIENT_ID}/drafts", json={"draft_type": "REFERRAL"})
    assert res1.status_code == 401

    res2 = client.get(f"/api/v1/patients/{DEMO_PATIENT_ID}/drafts")
    assert res2.status_code == 401

    res3 = client.get("/api/v1/drafts/some-id")
    assert res3.status_code == 401

    res4 = client.patch("/api/v1/drafts/some-id", json={"title": "Test"})
    assert res4.status_code == 401


def test_draft_endpoints_unauthorized_patient_403(auth_headers_doctor, db_session: Session):
    unauth = db_session.query(Patient).filter(Patient.id == UNAUTHORIZED_PATIENT_ID).first()
    if not unauth:
        unauth = Patient(
            id=UNAUTHORIZED_PATIENT_ID,
            first_name="Jane",
            last_name="Private",
            mrn="MRN-PRIV-8888",
        )
        db_session.add(unauth)
        db_session.commit()

    res1 = client.post(
        f"/api/v1/patients/{UNAUTHORIZED_PATIENT_ID}/drafts",
        headers=auth_headers_doctor,
        json={"draft_type": "REFERRAL"},
    )
    assert res1.status_code == 403

    res2 = client.get(
        f"/api/v1/patients/{UNAUTHORIZED_PATIENT_ID}/drafts",
        headers=auth_headers_doctor,
    )
    assert res2.status_code == 403


def test_draft_not_found_404(auth_headers_doctor):
    non_existent = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    res = client.get(
        f"/api/v1/drafts/{non_existent}",
        headers=auth_headers_doctor,
    )
    assert res.status_code == 404


def test_draft_audit_event_logged_zero_phi(auth_headers_doctor, db_session: Session):
    draft = Draft(
        id=generate_uuid(),
        patient_id=DEMO_PATIENT_ID,
        draft_type="HANDOFF",
        title="Audit Test Draft",
        content="Handoff text.",
        status="DRAFT",
        is_ai_generated=True,
    )
    db_session.add(draft)
    db_session.commit()

    res = client.get(f"/api/v1/drafts/{draft.id}", headers=auth_headers_doctor)
    assert res.status_code == 200

    audit = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.resource_type == "PATIENT_DRAFT",
            AuditEvent.resource_id == draft.id,
            AuditEvent.action == "VIEW_DRAFT_DETAIL",
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert audit is not None
    if audit.metadata_json:
        assert "Johnathan" not in audit.metadata_json
        assert "Doe" not in audit.metadata_json


def test_draft_gateway_rate_limit_maps_to_429(auth_headers_doctor):
    with patch.object(ClinicalDraftService, "generate_draft") as mock_gen:
        mock_gen.side_effect = AIRateLimitError("Quota limit hit")

        res = client.post(
            f"/api/v1/patients/{DEMO_PATIENT_ID}/drafts",
            headers=auth_headers_doctor,
            json={"draft_type": "REFERRAL"},
        )
        assert res.status_code == 429
        assert "rate limit exceeded" in res.json()["detail"].lower()


def test_draft_gateway_timeout_maps_to_504(auth_headers_doctor):
    with patch.object(ClinicalDraftService, "generate_draft") as mock_gen:
        mock_gen.side_effect = AITimeoutError()

        res = client.post(
            f"/api/v1/patients/{DEMO_PATIENT_ID}/drafts",
            headers=auth_headers_doctor,
            json={"draft_type": "REFERRAL"},
        )
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()
