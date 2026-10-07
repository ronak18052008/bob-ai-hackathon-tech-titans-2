"""
MedBrief AI — Patient Management Tests
Step 6: Patient Management

Validates:
- Patient listing with role-based scoping (clinician vs admin)
- Search across MRN, first name, and last name
- Status filtering (ACTIVE, INACTIVE, etc.)
- Pagination mechanics (page, page_size, total, total_pages)
- Patient detail retrieval and server-side RBAC access control
- Patient creation with automatic PRIMARY_PHYSICIAN assignment and audit logging
- Patient updating with field validation, conflict handling, and audit logging
- Strict rejection of unauthorized patient access attempts (HTTP 403)
"""

import pytest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.db.connection import SessionLocal
from src.backend.db.models import AuditEvent, Patient, PatientUserAccess

client = TestClient(app)

DOCTOR_CREDENTIALS = {
    "email": "dr.sarah.chen@demo-clinic.test",
    "password": "MedBrief2026!",
}

ADMIN_CREDENTIALS = {
    "email": "admin@demo-clinic.test",
    "password": "MedBriefAdmin2026!",
}


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


def test_list_patients_unauthenticated():
    res = client.get("/api/v1/patients")
    assert res.status_code == 401


def test_list_patients_doctor_scoping(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.get("/api/v1/patients", params={"page_size": 50}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    # Dr. Sarah Chen is assigned to 4 demo patients (Johnathan Doe, Eleanor Vance, Marcus Bennett, Sarah Jenkins)
    # Arthur Pendelton is unassigned and MUST NOT appear in clinician query
    mrns = [item["mrn"] for item in data["items"]]
    assert "DEMO-MRN-2026-0042" in mrns
    assert "DEMO-MRN-2026-0087" in mrns
    assert "DEMO-MRN-2026-0999" not in mrns  # Arthur Pendelton unassigned


def test_list_patients_admin_full_visibility(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/patients", params={"search": "Arthur"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    # Admin can see all patients including unassigned Arthur Pendelton
    mrns = [item["mrn"] for item in data["items"]]
    assert "DEMO-MRN-2026-0999" in mrns


def test_list_patients_search(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.get("/api/v1/patients?search=Eleanor", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["first_name"] == "Eleanor"
    assert data["items"][0]["last_name"] == "Vance"


def test_list_patients_status_filter(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.get("/api/v1/patients?status=INACTIVE", headers=headers)
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["status"] == "INACTIVE"
    assert any(item["first_name"] == "Sarah" for item in data["items"])


def test_list_patients_pagination(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.get("/api/v1/patients?page=1&page_size=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] >= 2


def test_get_patient_detail_authorized(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    # Johnathan Doe
    res = client.get("/api/v1/patients/22222222-2222-4000-8000-222222222222", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "22222222-2222-4000-8000-222222222222"
    assert data["first_name"] == "Johnathan"
    assert data["last_name"] == "Doe"
    assert data["document_count"] >= 1
    assert data["access_role"] == "PRIMARY_PHYSICIAN"

    # Verify audit event logged
    db = SessionLocal()
    audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.resource_id == "22222222-2222-4000-8000-222222222222", AuditEvent.action == "PATIENT_VIEW")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert audit is not None
    db.close()


def test_get_patient_detail_unauthorized_rejection(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    # Arthur Pendelton is unassigned to Dr. Sarah Chen
    res = client.get("/api/v1/patients/22222222-2222-4000-8000-222222222299", headers=headers)
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_create_patient_success(doctor_token):
    import uuid
    unique_mrn = f"TEST-MRN-{uuid.uuid4().hex[:8].upper()}"
    headers = {"Authorization": f"Bearer {doctor_token}"}
    payload = {
        "first_name": "TestNew",
        "last_name": "PatientCreated",
        "mrn": unique_mrn,
        "date_of_birth": "1990-01-15",
        "gender": "Female",
        "contact_phone": "+1-555-4321",
        "status": "ACTIVE",
    }
    res = client.post("/api/v1/patients", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["first_name"] == "TestNew"
    assert data["last_name"] == "PatientCreated"
    assert data["mrn"] == unique_mrn
    assert data["access_role"] == "PRIMARY_PHYSICIAN"

    # Verify access mapping created
    db = SessionLocal()
    access = (
        db.query(PatientUserAccess)
        .filter(PatientUserAccess.patient_id == data["id"])
        .first()
    )
    assert access is not None
    assert access.access_role == "PRIMARY_PHYSICIAN"

    # Verify audit event logged
    audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.resource_id == data["id"], AuditEvent.action == "PATIENT_CREATED")
        .first()
    )
    assert audit is not None
    db.close()


def test_create_patient_duplicate_mrn_conflict(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    payload = {
        "first_name": "Duplicate",
        "last_name": "Test",
        "mrn": "DEMO-MRN-2026-0042",  # Johnathan Doe's MRN
    }
    res = client.post("/api/v1/patients", json=payload, headers=headers)
    assert res.status_code == 409
    assert "already registered" in res.json()["detail"]


def test_update_patient_success(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    # Update Eleanor Vance contact phone
    patient_id = "22222222-2222-4000-8000-222222222223"
    update_payload = {
        "contact_phone": "+1-555-9999",
    }
    res = client.patch(f"/api/v1/patients/{patient_id}", json=update_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["contact_phone"] == "+1-555-9999"

    # Verify audit event logged
    db = SessionLocal()
    audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.resource_id == patient_id, AuditEvent.action == "PATIENT_UPDATED")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert audit is not None
    db.close()


def test_update_patient_unauthorized_rejection(doctor_token):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    # Attempt to update Arthur Pendelton (unassigned)
    res = client.patch(
        "/api/v1/patients/22222222-2222-4000-8000-222222222299",
        json={"first_name": "Hacked"},
        headers=headers,
    )
    assert res.status_code == 403
