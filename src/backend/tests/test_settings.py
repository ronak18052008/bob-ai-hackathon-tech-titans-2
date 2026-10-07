"""
MedBrief AI — Settings & User Security Test Suite
Tests:
- Profile retrieval and real persistence (PUT /api/v1/auth/me)
- Validation on profile updates
- Change Password verification (current password checking, password matching, complexity requirements)
- Real password update: old password rejected, new password authenticated
- Application & UI preferences persistence (GET and PUT /api/v1/auth/preferences)
- Audit event recording for security actions
"""

import pytest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.db.connection import SessionLocal
from src.backend.db.models import User, AuditEvent, UserPreference
from src.backend.db.init_db import init_database, seed_demo_data

client = TestClient(app)

DOCTOR_EMAIL = "dr.sarah.chen@demo-clinic.test"
INITIAL_PASSWORD = "MedBrief2026!"


@pytest.fixture(autouse=True)
def setup_db():
    init_database()
    seed_demo_data()
    # Reset doctor password_hash and preferences before each test
    db = SessionLocal()
    user = db.query(User).filter(User.email == DOCTOR_EMAIL).first()
    if user:
        user.password_hash = None
        user.display_name = "Dr. Sarah Chen, MD"
        user.role_title = "Attending Physician"
        user.medical_license_id = "MED-LIC-98421"
        db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
        db.commit()
    db.close()
    yield
    # Cleanup after each test
    db = SessionLocal()
    user = db.query(User).filter(User.email == DOCTOR_EMAIL).first()
    if user:
        user.password_hash = None
        user.display_name = "Dr. Sarah Chen, MD"
        user.role_title = "Attending Physician"
        user.medical_license_id = "MED-LIC-98421"
        db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
        db.commit()
    db.close()


def get_doctor_token(password=INITIAL_PASSWORD):
    res = client.post("/api/v1/auth/login", json={"email": DOCTOR_EMAIL, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_get_profile():
    token = get_doctor_token()
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == DOCTOR_EMAIL
    assert data["display_name"] == "Dr. Sarah Chen, MD"
    assert "doctor" in data["roles"]


def test_update_profile_success():
    token = get_doctor_token()
    res = client.put(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "Dr. Sarah Chen, MD, FACC",
            "role_title": "Lead Cardiologist",
            "medical_license_id": "MD-LIC-98421-CA",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "Dr. Sarah Chen, MD, FACC"
    assert data["role_title"] == "Lead Cardiologist"
    assert data["medical_license_id"] == "MD-LIC-98421-CA"

    # Verify database persistence
    db = SessionLocal()
    user = db.query(User).filter(User.email == DOCTOR_EMAIL).first()
    assert user.display_name == "Dr. Sarah Chen, MD, FACC"
    assert user.role_title == "Lead Cardiologist"
    assert user.medical_license_id == "MD-LIC-98421-CA"

    # Verify audit event
    audit = db.query(AuditEvent).filter(
        AuditEvent.user_id == user.id,
        AuditEvent.action == "PROFILE_UPDATE"
    ).first()
    assert audit is not None
    db.close()


def test_update_profile_validation_empty_name():
    token = get_doctor_token()
    res = client.put(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "   ", "role_title": "Cardiologist"},
    )
    assert res.status_code == 400
    assert "cannot be empty" in res.json()["detail"]


def test_update_profile_unauthenticated():
    res = client.put(
        "/api/v1/auth/me",
        json={"display_name": "Dr. Hacker"},
    )
    assert res.status_code == 401


def test_change_password_wrong_current():
    token = get_doctor_token()
    res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "WrongPassword123!",
            "new_password": "SecurePassword2026!",
            "confirm_password": "SecurePassword2026!",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Current password is incorrect."


def test_change_password_mismatch():
    token = get_doctor_token()
    res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": INITIAL_PASSWORD,
            "new_password": "SecurePassword2026!",
            "confirm_password": "DifferentPassword2026!",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Passwords do not match."


def test_change_password_too_weak():
    token = get_doctor_token()
    # Missing uppercase/number/special
    res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": INITIAL_PASSWORD,
            "new_password": "simple",
            "confirm_password": "simple",
        },
    )
    assert res.status_code == 400
    assert "security requirements" in res.json()["detail"]


def test_change_password_success_and_login_flow():
    token = get_doctor_token()
    new_password = "BrandNewSecret2026!"

    res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": INITIAL_PASSWORD,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "successfully" in res.json()["message"]

    # 1. Attempt login with old password - MUST FAIL
    old_res = client.post(
        "/api/v1/auth/login",
        json={"email": DOCTOR_EMAIL, "password": INITIAL_PASSWORD},
    )
    assert old_res.status_code == 401

    # 2. Attempt login with new password - MUST SUCCEED
    new_res = client.post(
        "/api/v1/auth/login",
        json={"email": DOCTOR_EMAIL, "password": new_password},
    )
    assert new_res.status_code == 200
    assert "access_token" in new_res.json()

    # 3. Verify audit event
    db = SessionLocal()
    user = db.query(User).filter(User.email == DOCTOR_EMAIL).first()
    audit = db.query(AuditEvent).filter(
        AuditEvent.user_id == user.id,
        AuditEvent.action == "PASSWORD_CHANGE"
    ).first()
    assert audit is not None
    db.close()


def test_get_and_update_preferences():
    token = get_doctor_token()

    # 1. Get initial preferences
    get_res = client.get(
        "/api/v1/auth/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    pref = get_res.json()
    assert pref["theme"] == "light"
    assert pref["reduced_motion"] is False

    # 2. Update preferences
    update_res = client.put(
        "/api/v1/auth/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "theme": "light",
            "reduced_motion": True,
            "density": "compact",
            "notify_in_app": True,
            "notify_doc_processing": False,
            "notify_ai_completion": True,
            "notify_follow_up_alerts": True,
            "default_dashboard_view": "timeline",
            "default_summary_type": "TIMELINE_REVIEW",
            "results_per_page": 25,
            "date_format": "YYYY-MM-DD",
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["reduced_motion"] is True
    assert updated["density"] == "compact"
    assert updated["notify_doc_processing"] is False
    assert updated["default_dashboard_view"] == "timeline"
    assert updated["results_per_page"] == 25

    # 3. Retrieve back and confirm persistence
    re_get_res = client.get(
        "/api/v1/auth/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert re_get_res.status_code == 200
    assert re_get_res.json()["reduced_motion"] is True
    assert re_get_res.json()["density"] == "compact"
    assert re_get_res.json()["default_dashboard_view"] == "timeline"
