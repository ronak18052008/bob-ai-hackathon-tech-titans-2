"""
MedBrief AI — Security & Access Control Matrix Tests
Step 14: Security + Testing + Reliability

Validates:
- Unauthenticated access rejection (401) across all patient endpoints
- Doctor access to authorized vs unauthorized patients (200 vs 403)
- Cross-patient data isolation (documents, timeline, medications, investigations, summaries, drafts)
- Role boundary enforcement (Doctor vs Admin route protection)
- Invalid/forged JWT rejection
- Mass-assignment protection on PATCH endpoints
- Input validation (invalid UUIDs, status enums, page numbers, path traversal)
- Patient not found handling (404)
- Empty body rejection on required fields (422)
"""

import pytest
from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

DOCTOR_CREDENTIALS = {
    "email": "dr.sarah.chen@demo-clinic.test",
    "password": "MedBrief2026!",
}

ADMIN_CREDENTIALS = {
    "email": "admin@demo-clinic.test",
    "password": "MedBriefAdmin2026!",
}

ASSIGNED_PATIENT_ID = "22222222-2222-4000-8000-222222222222"
UNASSIGNED_PATIENT_ID = "22222222-2222-4000-8000-222222222299"
NONEXISTENT_PATIENT_ID = "ffffffff-ffff-4000-8000-ffffffffffff"


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


# ── 1. Unauthenticated Access Rejection (401) ───────────────────────────────

class TestUnauthenticatedAccess:
    """All patient-related endpoints must reject unauthenticated requests with 401."""

    def test_list_patients_unauthenticated(self):
        res = client.get("/api/v1/patients")
        assert res.status_code == 401

    def test_get_patient_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}")
        assert res.status_code == 401

    def test_update_patient_unauthenticated(self):
        res = client.patch(
            f"/api/v1/patients/{ASSIGNED_PATIENT_ID}",
            json={"first_name": "Hacker"},
        )
        assert res.status_code == 401

    def test_patient_documents_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/documents")
        assert res.status_code == 401

    def test_patient_timeline_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/timeline")
        assert res.status_code == 401

    def test_patient_medications_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/medications")
        assert res.status_code == 401

    def test_patient_investigations_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/investigations")
        assert res.status_code == 401

    def test_patient_summaries_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/summaries")
        assert res.status_code == 401

    def test_patient_drafts_unauthenticated(self):
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/drafts")
        assert res.status_code == 401


# ── 2. Authorized Patient Access (200) ──────────────────────────────────────

class TestAuthorizedPatientAccess:
    """Doctor accessing assigned patient should receive 200."""

    def test_doctor_access_authorized_patient_returns_200(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == ASSIGNED_PATIENT_ID


# ── 3. Unauthorized Patient Access (403) ─────────────────────────────────────

class TestUnauthorizedPatientAccess:
    """Doctor accessing unassigned patient records must receive 403."""

    def test_doctor_access_unauthorized_patient_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}", headers=headers)
        assert res.status_code == 403

    def test_doctor_unauthorized_patient_documents_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/documents", headers=headers)
        assert res.status_code == 403

    def test_doctor_unauthorized_patient_timeline_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/timeline", headers=headers)
        assert res.status_code == 403

    def test_doctor_unauthorized_patient_medications_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/medications", headers=headers)
        assert res.status_code == 403

    def test_doctor_unauthorized_patient_investigations_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/investigations", headers=headers)
        assert res.status_code == 403

    def test_doctor_unauthorized_patient_summaries_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/summaries", headers=headers)
        assert res.status_code == 403

    def test_doctor_unauthorized_patient_drafts_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}/drafts", headers=headers)
        assert res.status_code == 403


# ── 4. Role Boundary Enforcement ─────────────────────────────────────────────

class TestRoleBoundaryEnforcement:
    """Roles must be strictly partitioned — Doctor cannot access Admin routes and vice versa."""

    def test_doctor_accessing_admin_route_returns_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get("/api/v1/auth/admin-access", headers=headers)
        assert res.status_code == 403

    def test_admin_accessing_doctor_route_returns_403(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = client.get("/api/v1/auth/doctor-access", headers=headers)
        assert res.status_code == 403


# ── 5. Invalid/Forged JWT Rejection ──────────────────────────────────────────

class TestJWTRejection:
    """Invalid, forged, or malformed tokens must be rejected with 401."""

    def test_invalid_jwt_rejected(self):
        headers = {"Authorization": "Bearer completely.invalid.jwt.token.here"}
        res = client.get("/api/v1/patients", headers=headers)
        assert res.status_code == 401

    def test_expired_token_like_string_rejected(self):
        headers = {"Authorization": "Bearer not-even-a-jwt"}
        res = client.get("/api/v1/patients", headers=headers)
        assert res.status_code == 401

    def test_empty_bearer_token_rejected(self):
        headers = {"Authorization": "Bearer "}
        res = client.get("/api/v1/patients", headers=headers)
        assert res.status_code == 401

    def test_no_bearer_prefix_rejected(self):
        headers = {"Authorization": "Token some-random-token"}
        res = client.get("/api/v1/patients", headers=headers)
        assert res.status_code == 401


# ── 6. Mass-Assignment Protection on PATCH ───────────────────────────────────

class TestMassAssignmentProtection:
    """Protected fields (id, created_by, created_at) must be silently ignored on PATCH."""

    def test_mass_assignment_patient_update_ignores_protected_fields(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}

        # Get original patient data
        original_res = client.get(f"/api/v1/patients/{ASSIGNED_PATIENT_ID}", headers=headers)
        assert original_res.status_code == 200
        original = original_res.json()
        original_id = original["id"]
        original_created_by = original.get("created_by")
        original_created_at = original.get("created_at")

        # Attempt to modify protected fields alongside a valid field
        update_res = client.patch(
            f"/api/v1/patients/{ASSIGNED_PATIENT_ID}",
            headers=headers,
            json={
                "first_name": original["first_name"],  # Keep same to avoid test pollution
                "id": "attacker-controlled-id",
                "created_by": "attacker-controlled-user",
                "created_at": "1999-01-01T00:00:00",
            },
        )
        # PATCH should succeed (protected fields silently ignored) or 422 if fields are rejected
        assert update_res.status_code in (200, 422)

        if update_res.status_code == 200:
            updated = update_res.json()
            # Protected fields must NOT have changed
            assert updated["id"] == original_id
            if original_created_by is not None:
                assert updated.get("created_by") == original_created_by
            if original_created_at is not None:
                assert updated.get("created_at") == original_created_at


# ── 7. Input Validation ──────────────────────────────────────────────────────

class TestInputValidation:
    """Invalid inputs must be rejected with appropriate HTTP error codes."""

    def test_invalid_uuid_patient_id_returns_error(self, doctor_token):
        """Non-UUID patient IDs should return 403, 404, or 422, never 200 or 500."""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get("/api/v1/patients/not-a-valid-uuid", headers=headers)
        assert res.status_code in (403, 404, 422)

    def test_invalid_status_enum_rejected(self, doctor_token):
        """Creating a patient with an invalid status must return 422."""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.post(
            "/api/v1/patients",
            headers=headers,
            json={
                "first_name": "TestInvalid",
                "last_name": "StatusEnum",
                "status": "INVALID_STATUS_VALUE",
            },
        )
        assert res.status_code == 422

    def test_path_traversal_attempt_patient_id(self, doctor_token):
        """Path traversal attempts in patient_id must return 404 or 422, never 200 or 500."""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get("/api/v1/patients/..%2F..%2Fetc%2Fpasswd", headers=headers)
        assert res.status_code in (404, 422)
        assert res.status_code != 500  # Must never trigger internal error

    def test_negative_page_number_handling(self, doctor_token):
        """Negative page numbers should be rejected or safely defaulted."""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get("/api/v1/patients?page=-1", headers=headers)
        # Either 422 validation error or 200 with defaulted pagination
        assert res.status_code in (200, 422)

    def test_empty_body_patient_creation_rejected(self, doctor_token):
        """Creating a patient without required fields must return 422."""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.post("/api/v1/patients", headers=headers, json={})
        assert res.status_code == 422


# ── 8. Patient Not Found ─────────────────────────────────────────────────────

class TestPatientNotFound:
    """Accessing a non-existent patient should return 404 or 403 (fail-closed)."""

    def test_patient_not_found_returns_404_or_403(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{NONEXISTENT_PATIENT_ID}", headers=headers)
        assert res.status_code in (403, 404)

    def test_nonexistent_patient_documents_returns_error(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{NONEXISTENT_PATIENT_ID}/documents", headers=headers)
        assert res.status_code in (403, 404)

    def test_nonexistent_patient_timeline_returns_error(self, doctor_token):
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = client.get(f"/api/v1/patients/{NONEXISTENT_PATIENT_ID}/timeline", headers=headers)
        assert res.status_code in (403, 404)


# ── 9. Health Endpoint Security ──────────────────────────────────────────────

class TestHealthEndpointSecurity:
    """Health check must not leak internal state or credentials."""

    def test_health_endpoint_accessible_without_auth(self):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        # Must never contain connection strings, passwords, or stack traces
        response_str = str(data).lower()
        assert "password" not in response_str
        assert "postgres://" not in response_str
        assert "sqlite:///" not in response_str or "memory" in response_str
        assert data["status"] in ("healthy", "degraded")

    def test_root_endpoint_accessible_without_auth(self):
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["app"] == "MedBrief AI"
        # Must not leak sensitive config
        assert "api_key" not in str(data).lower()
        assert "secret" not in str(data).lower()
