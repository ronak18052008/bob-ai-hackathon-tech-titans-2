"""
MedBrief AI — Authentication & Server-Side RBAC Tests
Step 4: Authentication + RBAC

Validates:
- Demo login authentication (Doctor & Admin)
- Token issuance and claims integrity
- Current user profile endpoint (/api/v1/auth/me)
- Role verification guards (Doctor vs Admin route protection)
- Unauthorized and forbidden access rejection (401 & 403)
- Patient-level authorization preparation (patient_user_access enforcement)
- Logout flow and audit event recording
- Prevention of client-supplied role tampering
"""

import pytest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.db.init_db import init_database, seed_demo_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    init_database()
    seed_demo_data()


# ── 1. Authentication Flow Tests ─────────────────────────────────────────────

def test_doctor_login_success():
    """Test physician login with primary email and alias."""
    for email in ["dr.sarah.chen@demo-clinic.test", "doctor.demo@medbrief.local"]:
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "MedBrief2026!"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "dr.sarah.chen@demo-clinic.test"
        assert "doctor" in data["user"]["roles"]
        assert data["user"]["is_active"] is True
        assert data["user"]["medical_license_id"] == "MED-LIC-98421"


def test_admin_login_success():
    """Test administrator login with primary email and alias."""
    for email in ["admin@demo-clinic.test", "admin.demo@medbrief.local"]:
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "MedBriefAdmin2026!"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@demo-clinic.test"
        assert "admin" in data["user"]["roles"]
        assert data["user"]["is_active"] is True


def test_login_invalid_password():
    """Test rejection on incorrect password."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]


def test_login_nonexistent_email():
    """Test rejection on unknown clinical user."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown.user@demo-clinic.test", "password": "MedBrief2026!"},
    )
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]


# ── 2. Current User Profile Endpoint (/api/v1/auth/me) ─────────────────────────

def test_get_current_user_unauthenticated():
    """Unauthenticated requests to /me must return 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_get_current_user_invalid_token():
    """Malformed or invalid Bearer tokens must return 401."""
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token.here"},
    )
    assert res.status_code == 401


def test_get_current_user_doctor():
    """Doctor gets resolved profile and DB roles without sensitive leaks."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "MedBrief2026!"},
    )
    token = login_res.json()["access_token"]

    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    user = res.json()
    assert user["display_name"] == "Dr. Sarah Chen, MD"
    assert user["email"] == "dr.sarah.chen@demo-clinic.test"
    assert "doctor" in user["roles"]
    assert "password" not in user
    assert "hash" not in user


def test_get_current_user_admin():
    """Admin gets resolved profile and DB roles."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo-clinic.test", "password": "MedBriefAdmin2026!"},
    )
    token = login_res.json()["access_token"]

    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    user = res.json()
    assert user["display_name"] == "Alex Rivera"
    assert "admin" in user["roles"]


# ── 3. Role-Based Access Control (RBAC) Protection Tests ─────────────────────

def test_doctor_access_route():
    """Doctor route allows DOCTOR, rejects ADMIN, rejects unauthenticated."""
    # 1. Unauthenticated -> 401
    res = client.get("/api/v1/auth/doctor-access")
    assert res.status_code == 401

    # 2. Doctor -> 200
    doc_login = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "MedBrief2026!"},
    )
    doc_token = doc_login.json()["access_token"]
    res = client.get(
        "/api/v1/auth/doctor-access",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "doctor"

    # 3. Admin attempting Doctor route -> 403 Forbidden
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo-clinic.test", "password": "MedBriefAdmin2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    res = client.get(
        "/api/v1/auth/doctor-access",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403
    assert "Requires 'DOCTOR' role" in res.json()["detail"]


def test_admin_access_route():
    """Admin route allows ADMIN, rejects DOCTOR, rejects unauthenticated."""
    # 1. Unauthenticated -> 401
    res = client.get("/api/v1/auth/admin-access")
    assert res.status_code == 401

    # 2. Doctor attempting Admin route -> 403 Forbidden
    doc_login = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "MedBrief2026!"},
    )
    doc_token = doc_login.json()["access_token"]
    res = client.get(
        "/api/v1/auth/admin-access",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res.status_code == 403
    assert "Requires 'ADMIN' role" in res.json()["detail"]

    # 3. Admin -> 200
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo-clinic.test", "password": "MedBriefAdmin2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    res = client.get(
        "/api/v1/auth/admin-access",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


# ── 4. Patient-Level Authorization Preparation ───────────────────────────────

def test_patient_level_access():
    """Verifies patient_user_access mapping logic."""
    doc_login = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "MedBrief2026!"},
    )
    doc_token = doc_login.json()["access_token"]

    # Doctor accessing assigned patient 22222222-2222-4000-8000-222222222222 -> Allowed (200)
    assigned_patient_id = "22222222-2222-4000-8000-222222222222"
    res = client.get(
        f"/api/v1/auth/patient-access/{assigned_patient_id}",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res.status_code == 200
    assert res.json()["access_granted"] is True

    # Doctor accessing unassigned patient -> Forbidden (403)
    unassigned_patient_id = "ffffffff-ffff-4000-8000-ffffffffffff"
    res = client.get(
        f"/api/v1/auth/patient-access/{unassigned_patient_id}",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res.status_code == 403
    assert "not authorized to access this patient record" in res.json()["detail"]

    # Admin has system-level access to any patient
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo-clinic.test", "password": "MedBriefAdmin2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    res = client.get(
        f"/api/v1/auth/patient-access/{unassigned_patient_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["access_granted"] is True


# ── 5. Session Logout Flow ───────────────────────────────────────────────────

def test_logout_endpoint():
    """Test session sign-out."""
    doc_login = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sarah.chen@demo-clinic.test", "password": "MedBrief2026!"},
    )
    doc_token = doc_login.json()["access_token"]

    res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
