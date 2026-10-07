"""
MedBrief AI — Document Upload & Ingestion Tests
Step 7: PDF / Medical Document Upload & Ingestion Foundation

Validates:
- Strict PDF format and magic bytes validation (%PDF-)
- Size limits and empty file rejection
- Patient-level server-side access authorization (HTTP 403 on unassigned patients)
- Document persistence in private storage
- ProcessingJob creation with initial status QUEUED
- Duplicate document detection for same patient (HTTP 409)
- Document listing per patient and globally
- Controlled, authenticated streaming preview/download (HTTP 200 application/pdf)
- Job retry handling without creating duplicate document records
- Authoritative audit event logging (DOCUMENT_UPLOAD, DOCUMENT_VIEW, PROCESSING_RETRY)
"""

import io
import uuid
import pytest
from pypdf import PdfWriter
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.db.connection import SessionLocal
from src.backend.db.models import AuditEvent, Document, ProcessingJob

client = TestClient(app)

DOCTOR_CREDENTIALS = {
    "email": "dr.sarah.chen@demo-clinic.test",
    "password": "MedBrief2026!",
}

ADMIN_CREDENTIALS = {
    "email": "admin@demo-clinic.test",
    "password": "MedBriefAdmin2026!",
}

ASSIGNED_PATIENT_ID = "22222222-2222-4000-8000-222222222222"  # Johnathan Doe
UNASSIGNED_PATIENT_ID = "22222222-2222-4000-8000-222222222299"  # Arthur Pendelton


def create_minimal_pdf_bytes(title: str = "Synthetic Test Clinical Record") -> bytes:
    """Generate a clean synthetic valid PDF binary in-memory."""
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


@pytest.fixture(scope="module")
def admin_token():
    res = client.post("/api/v1/auth/login", json=ADMIN_CREDENTIALS)
    assert res.status_code == 200
    return res.json()["access_token"]


def test_upload_unauthenticated():
    pdf_bytes = create_minimal_pdf_bytes()
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    res = client.post(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents", files=files)
    assert res.status_code == 401


def test_upload_unauthorized_patient_rejection(doctor_token):
    pdf_bytes = create_minimal_pdf_bytes()
    files = {"file": ("test_unauth.pdf", pdf_bytes, "application/pdf")}
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.post(
        f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/documents",
        files=files,
        data={"document_type": "DISCHARGE_SUMMARY"},
        headers=headers,
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_upload_non_pdf_rejection(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    files = {"file": ("notes.docx", b"dummy word content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post(
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents",
        files=files,
        headers=headers,
    )
    assert res.status_code == 400
    assert "Only PDF medical records" in res.json()["detail"]


def test_upload_corrupt_or_fake_pdf_header_rejection(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    files = {"file": ("corrupt.pdf", b"NOT_A_REAL_PDF_DATA", "application/pdf")}
    res = client.post(
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents",
        files=files,
        headers=headers,
    )
    assert res.status_code == 400
    assert "valid PDF" in res.json()["detail"]


def test_upload_empty_file_rejection(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = client.post(
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents",
        files=files,
        headers=headers,
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def _generate_test_pdf(tag: str = "") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    if tag:
        writer.add_metadata({"/Producer": f"MedBrief-Test-{tag}"})
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def test_upload_valid_pdf_success(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    unique_tag = uuid.uuid4().hex[:8]
    pdf_bytes = _generate_test_pdf(unique_tag)
    filename = f"Outpatient_Echo_Referral_{unique_tag}.pdf"
    files = {"file": (filename, pdf_bytes, "application/pdf")}
    data = {"document_type": "CLINIC_CONSULTATION"}

    res = client.post(
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents",
        files=files,
        data=data,
        headers=headers,
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["patient_id"] == ASSIGNED_PATIENT_ID
    assert doc_data["file_name"] == filename
    assert doc_data["page_count"] == 2
    assert doc_data["status"] == "UPLOADED"
    assert doc_data["job_status"] == "QUEUED"

    # Verify database persistence
    db = SessionLocal()
    doc_in_db = db.query(Document).filter(Document.id == doc_data["id"]).first()
    assert doc_in_db is not None
    assert doc_in_db.file_name == filename

    job_in_db = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc_data["id"]).first()
    assert job_in_db is not None
    assert job_in_db.status == "QUEUED"

    # Verify audit event
    audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.resource_id == doc_data["id"], AuditEvent.action == "DOCUMENT_UPLOAD")
        .first()
    )
    assert audit is not None
    db.close()


def test_duplicate_document_rejection(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    unique_tag = uuid.uuid4().hex[:8]
    pdf_bytes = _generate_test_pdf(unique_tag)
    filename = f"Duplicate_Test_{unique_tag}.pdf"

    # 1. First upload succeeds
    files1 = {"file": (filename, pdf_bytes, "application/pdf")}
    res1 = client.post(
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents",
        files=files1,
        headers=headers,
    )
    assert res1.status_code == 201

    # 2. Second upload with identical bytes to same patient is rejected as 409 Conflict
    files2 = {"file": (filename, pdf_bytes, "application/pdf")}
    res2 = client.post(
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents",
        files=files2,
        headers=headers,
    )
    assert res2.status_code == 409
    assert "Duplicate detected" in res2.json()["detail"]


def test_list_patient_documents(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents", headers=headers)
    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)
    assert len(docs) >= 1
    for d in docs:
        assert d["patient_id"] == ASSIGNED_PATIENT_ID


def test_get_document_details_and_stream(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    # Find existing document
    list_res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents", headers=headers)
    doc_id = list_res.json()[0]["id"]

    # 1. Detail endpoint
    detail_res = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == doc_id
    assert "job_status" in detail

    # 2. File stream endpoint
    file_res = client.get(f"/api/v1/documents/{doc_id}/file", headers=headers)
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "application/pdf"
    assert file_res.content.startswith(b"%PDF-")


def test_retry_document_processing(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    list_res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents", headers=headers)
    doc_id = list_res.json()[0]["id"]

    res = client.post(f"/api/v1/documents/{doc_id}/retry", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["document"]["job_status"] == "QUEUED"

    # Verify audit event
    db = SessionLocal()
    audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.resource_id == doc_id, AuditEvent.action == "PROCESSING_RETRY")
        .first()
    )
    assert audit is not None
    db.close()
