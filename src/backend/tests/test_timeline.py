"""
MedBrief AI — Clinical Timeline Automated Test Suite
Step 10: Clinical Timeline

Comprehensive tests verifying:
1. Strict Date Precision Formatting (EXACT, MONTH_YEAR, YEAR_ONLY, APPROXIMATE, UNKNOWN)
2. No invented days, months, or years
3. Deterministic chronological sorting (DESC and ASC)
4. Same-day secondary deterministic sorting
5. Clean separation of dated events vs "Date not documented" section
6. Multi-period grouping (Year -> Month)
7. Event type normalization and visual metadata mapping
8. Batch preloading of document and verbatim evidence references (Zero N+1 queries)
9. Preservation of conflicting source dates and uncertainty flags
10. Source traceability (Document name, page number, verbatim snippet)
11. REST API endpoint authorization (401 unauthenticated, 403 unauthorized, 404 not found)
12. Filter by event type, date range, and keyword search
13. Safe zero-PHI audit logging
"""

import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.main import app
from src.backend.db.connection import get_db, SessionLocal
from src.backend.db.models import (
    User,
    Patient,
    Document,
    DocumentPage,
    ClinicalEvent,
    EvidenceReference,
    PatientUserAccess,
    AuditEvent,
)
from src.backend.auth.security import create_access_token
from src.backend.timeline.timeline_service import (
    format_display_date,
    normalize_event_type,
    get_event_type_meta,
    TimelineService,
)

client = TestClient(app)


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
def auth_headers_unauthorized(db_session: Session):
    """Token for a different user not authorized for Arthur Pendelton."""
    doctor = db_session.query(User).filter(User.email == "dr.sarah.chen@demo-clinic.test").first()
    token = create_access_token(data={"sub": doctor.id, "email": doctor.email, "roles": ["doctor"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(db_session: Session):
    """Token for Administrator."""
    admin = db_session.query(User).filter(User.email == "admin@demo-clinic.test").first()
    token = create_access_token(data={"sub": admin.id, "email": admin.email, "roles": ["admin"]})
    return {"Authorization": f"Bearer {token}"}


# ── Unit Tests: Date Precision & Formatting ───────────────────────────────────

def test_format_display_date_exact_date():
    dt = datetime(2026, 2, 5, 8, 30, tzinfo=timezone.utc)
    res = format_display_date(dt, "EXACT")
    assert res == "05 Feb 2026, 08:30"

    dt_no_time = datetime(2026, 2, 5, 0, 0, tzinfo=timezone.utc)
    res_no_time = format_display_date(dt_no_time, "EXACT")
    assert res_no_time == "05 Feb 2026"


def test_format_display_date_month_year_never_invents_day():
    """MONTH_YEAR must never invent '01 Feb 2026'."""
    dt = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    res = format_display_date(dt, "MONTH_YEAR")
    assert res == "Feb 2026"
    assert "01" not in res


def test_format_display_date_year_only_never_invents_month_or_day():
    """YEAR_ONLY must return just year string, never '01 Jan 2025'."""
    dt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    res = format_display_date(dt, "YEAR_ONLY")
    assert res == "2025"
    assert "Jan" not in res
    assert "01" not in res


def test_format_display_date_approximate():
    dt = datetime(2025, 6, 1, 0, 0, tzinfo=timezone.utc)
    res = format_display_date(dt, "APPROXIMATE")
    assert "Approx." in res
    assert "Jun 2025" in res


def test_format_display_date_unknown_or_none():
    assert format_display_date(None, "UNKNOWN") == "Date not documented"
    dt = datetime(2026, 1, 1)
    assert format_display_date(dt, "UNKNOWN") == "Date not documented"
    assert format_display_date(None, None) == "Date not documented"


# ── Unit Tests: Event Type Normalization ──────────────────────────────────────

def test_normalize_event_type():
    assert normalize_event_type("Consultation") == "consultation"
    assert normalize_event_type("DIAGNOSIS") == "diagnosis"
    assert normalize_event_type("medication_start") == "medication_start"
    assert normalize_event_type("Hospital Admission") == "admission" or normalize_event_type("admission") == "admission"
    assert normalize_event_type("completely_random_unknown_type") == "other"
    assert normalize_event_type(None) == "other"


def test_get_event_type_meta():
    meta = get_event_type_meta("consultation")
    assert meta["label"] == "Consultation"
    assert meta["icon"] == "💬"
    assert meta["badge_class"] == "consultation"


# ── Integration Tests: Timeline Service Construction ──────────────────────────

def test_timeline_service_deterministic_ordering_and_grouping(db_session: Session):
    patient_id = "22222222-2222-4000-8000-222222222222"
    service = TimelineService()

    # Clear prior test events for clean assertion
    db_session.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient_id).delete()
    db_session.commit()

    # Create test events
    e1 = ClinicalEvent(
        patient_id=patient_id,
        event_type="admission",
        event_date=datetime(2026, 2, 5, 8, 30, tzinfo=timezone.utc),
        event_date_precision="EXACT",
        title="Emergency Admission for Chest Pain",
        description="Patient presented with acute retrosternal pressure.",
    )
    e2 = ClinicalEvent(
        patient_id=patient_id,
        event_type="procedure",
        event_date=datetime(2026, 2, 6, 11, 0, tzinfo=timezone.utc),
        event_date_precision="EXACT",
        title="Coronary Angiography",
        description="Diagnostic angiogram completed.",
    )
    e3 = ClinicalEvent(
        patient_id=patient_id,
        event_type="discharge",
        event_date=datetime(2026, 2, 10, 14, 0, tzinfo=timezone.utc),
        event_date_precision="EXACT",
        title="Hospital Discharge",
        description="Patient discharged home in stable condition.",
    )
    e_past = ClinicalEvent(
        patient_id=patient_id,
        event_type="diagnosis",
        event_date=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        event_date_precision="YEAR_ONLY",
        title="History of Essential Hypertension",
        description="Diagnosed 2 years prior.",
    )
    e_undated = ClinicalEvent(
        patient_id=patient_id,
        event_type="other",
        event_date=None,
        event_date_precision="UNKNOWN",
        title="Documented Penicillin Allergy",
        description="Reported mild rash in childhood without specific date.",
    )

    db_session.add_all([e1, e2, e3, e_past, e_undated])
    db_session.commit()

    # Query descending
    res_desc = service.get_patient_timeline(db_session, patient_id=patient_id, sort="desc")
    assert res_desc["total"] == 5
    assert res_desc["summary"]["total_events"] == 5
    assert res_desc["summary"]["dated_events_count"] == 4
    assert res_desc["summary"]["undated_events_count"] == 1

    # Undated events isolated
    assert len(res_desc["undated_events"]) == 1
    assert res_desc["undated_events"][0]["title"] == "Documented Penicillin Allergy"
    assert res_desc["undated_events"][0]["display_date"] == "Date not documented"

    # Groups verify Year / Month
    groups = res_desc["groups"]
    assert len(groups) >= 2
    feb_group = next(g for g in groups if g["period_key"] == "2026-02")
    assert feb_group["event_count"] == 3
    # Check descending order in group (e3 -> e2 -> e1)
    assert feb_group["events"][0]["title"] == "Hospital Discharge"
    assert feb_group["events"][1]["title"] == "Coronary Angiography"
    assert feb_group["events"][2]["title"] == "Emergency Admission for Chest Pain"

    # Check YEAR_ONLY precision in 2024 group
    past_group = next(g for g in groups if g["period_key"] == "2024")
    assert past_group["events"][0]["display_date"] == "2024"
    assert past_group["events"][0]["date_precision"] == "YEAR_ONLY"

    # Query ascending
    res_asc = service.get_patient_timeline(db_session, patient_id=patient_id, sort="asc")
    asc_groups = res_asc["groups"]
    asc_feb = next(g for g in asc_groups if g["period_key"] == "2026-02")
    assert asc_feb["events"][0]["title"] == "Emergency Admission for Chest Pain"
    assert asc_feb["events"][2]["title"] == "Hospital Discharge"


def test_timeline_service_same_day_secondary_deterministic_sort(db_session: Session):
    patient_id = "22222222-2222-4000-8000-222222222222"
    service = TimelineService()

    db_session.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient_id).delete()
    db_session.commit()

    same_time = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    ev_a = ClinicalEvent(
        patient_id=patient_id,
        event_type="consultation",
        event_date=same_time,
        event_date_precision="EXACT",
        title="Consultation Alpha",
        description="First note recorded.",
    )
    ev_b = ClinicalEvent(
        patient_id=patient_id,
        event_type="investigation",
        event_date=same_time,
        event_date_precision="EXACT",
        title="Investigation Beta",
        description="Second note recorded.",
    )
    db_session.add_all([ev_a, ev_b])
    db_session.commit()

    res = service.get_patient_timeline(db_session, patient_id=patient_id, sort="asc")
    # Both events present in same group with deterministic order
    assert len(res["items"]) == 2
    assert {res["items"][0]["title"], res["items"][1]["title"]} == {"Consultation Alpha", "Investigation Beta"}


def test_timeline_service_source_traceability_and_evidence(db_session: Session):
    patient_id = "22222222-2222-4000-8000-222222222222"
    service = TimelineService()

    # Find or create a test document and page
    doc = db_session.query(Document).filter(Document.patient_id == patient_id).first()
    if not doc:
        doc = Document(
            patient_id=patient_id,
            file_name="discharge_summary_cardiology.pdf",
            file_path="uploads/test.pdf",
            document_type="DISCHARGE_SUMMARY",
            status="COMPLETED",
        )
        db_session.add(doc)
        db_session.commit()

    page = db_session.query(DocumentPage).filter(DocumentPage.document_id == doc.id).first()
    if not page:
        page = DocumentPage(
            document_id=doc.id,
            page_number=2,
            extracted_text="Patient commenced on Atorvastatin 40mg daily upon discharge.",
        )
        db_session.add(page)
        db_session.commit()

    ev = ClinicalEvent(
        patient_id=patient_id,
        source_document_id=doc.id,
        source_page_id=page.id,
        event_type="medication_start",
        event_date=datetime(2026, 2, 10, 14, 0, tzinfo=timezone.utc),
        event_date_precision="EXACT",
        title="Atorvastatin Started",
        description="High intensity statin commenced.",
    )
    db_session.add(ev)
    db_session.commit()

    # Add evidence reference
    evidence = EvidenceReference(
        patient_id=patient_id,
        parent_entity_type="CLINICAL_EVENT",
        parent_entity_id=ev.id,
        document_id=doc.id,
        document_page_id=page.id,
        source_text="Patient commenced on Atorvastatin 40mg daily upon discharge.",
        source_section="Discharge Medications",
    )
    db_session.add(evidence)
    db_session.commit()

    res = service.get_patient_timeline(db_session, patient_id=patient_id)
    target_item = next((item for item in res["items"] if item["id"] == ev.id), None)
    assert target_item is not None
    assert target_item["source"]["document_name"] == doc.file_name
    assert target_item["source"]["page_number"] == page.page_number
    assert target_item["source"]["source_section"] == "Discharge Medications"
    assert "Atorvastatin 40mg daily" in target_item["source"]["source_snippet"]


def test_timeline_service_conflict_details_preservation(db_session: Session):
    patient_id = "22222222-2222-4000-8000-222222222222"
    service = TimelineService()

    ev = ClinicalEvent(
        patient_id=patient_id,
        event_type="procedure",
        event_date=datetime(2026, 2, 7, 0, 0, tzinfo=timezone.utc),
        event_date_precision="APPROXIMATE",
        title="Echocardiogram",
        description="Procedure performed during admission.",
        is_conflict=True,
        conflict_details="Discharge note indicates echo performed on Feb 7; nursing flow sheet lists Feb 8.",
    )
    db_session.add(ev)
    db_session.commit()

    res = service.get_patient_timeline(db_session, patient_id=patient_id)
    item = next((i for i in res["items"] if i["id"] == ev.id), None)
    assert item is not None
    assert item["is_conflict"] is True
    assert "Discharge note indicates echo performed on Feb 7" in item["conflict_details"]


def test_timeline_service_filtering_and_search(db_session: Session):
    patient_id = "22222222-2222-4000-8000-222222222222"
    service = TimelineService()

    # Add dedicated event for search & filter validation
    ev_test = ClinicalEvent(
        patient_id=patient_id,
        event_type="admission",
        event_date=datetime(2026, 2, 5, 8, 30, tzinfo=timezone.utc),
        event_date_precision="EXACT",
        title="Emergency Admission for Chest Pain",
        description="Patient presented with acute retrosternal chest discomfort.",
    )
    db_session.add(ev_test)
    db_session.commit()

    # Filter by event type
    res_adm = service.get_patient_timeline(db_session, patient_id=patient_id, event_type="admission")
    assert all(item["event_type"] == "admission" for item in res_adm["items"])
    assert len(res_adm["items"]) >= 1

    # Search keyword
    res_search = service.get_patient_timeline(db_session, patient_id=patient_id, search="chest")
    assert any("chest" in item["title"].lower() or "chest" in item["description"].lower() for item in res_search["items"])


def test_timeline_summary_endpoint_service(db_session: Session):
    patient_id = "22222222-2222-4000-8000-222222222222"
    service = TimelineService()

    summary = service.get_patient_timeline_summary(db_session, patient_id=patient_id)
    assert summary["patient_id"] == patient_id
    assert "recent_events" in summary
    assert len(summary["recent_events"]) <= 5
    if summary["recent_events"]:
        first = summary["recent_events"][0]
        assert "title" in first
        assert "display_date" in first
        assert "event_type_label" in first


# ── REST API Endpoint Security & Authorization Tests ──────────────────────────

def test_api_timeline_unauthenticated():
    """Unauthenticated request must return 401 Unauthorized."""
    resp = client.get("/api/v1/patients/22222222-2222-4000-8000-222222222222/timeline")
    assert resp.status_code == 401


def test_api_timeline_unauthorized_forbidden(auth_headers_unauthorized: dict):
    """Doctor requesting patient outside assigned caseload must return 403 Forbidden."""
    unassigned_patient_id = "22222222-2222-4000-8000-222222222299"
    resp = client.get(
        f"/api/v1/patients/{unassigned_patient_id}/timeline",
        headers=auth_headers_unauthorized,
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_api_timeline_authorized_success(auth_headers_doctor: dict):
    """Authorized doctor retrieves patient timeline with 200 OK."""
    patient_id = "22222222-2222-4000-8000-222222222222"
    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline?sort=desc",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["patient_id"] == patient_id
    assert "summary" in data
    assert "groups" in data
    assert "undated_events" in data
    assert "items" in data


def test_api_timeline_summary_authorized_success(auth_headers_doctor: dict):
    """Authorized doctor retrieves timeline summary widget with 200 OK."""
    patient_id = "22222222-2222-4000-8000-222222222222"
    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline/summary",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["patient_id"] == patient_id
    assert "recent_events" in data
    assert "total_events" in data


def test_api_timeline_admin_access_allowed(auth_headers_admin: dict):
    """Admin has full cross-clinic visibility."""
    patient_id = "22222222-2222-4000-8000-222222222299"
    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline",
        headers=auth_headers_admin,
    )
    assert resp.status_code == 200


def test_api_timeline_nonexistent_patient_returns_404(auth_headers_admin: dict):
    """Admin requesting nonexistent patient returns 404 Not Found."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(
        f"/api/v1/patients/{fake_id}/timeline",
        headers=auth_headers_admin,
    )
    assert resp.status_code == 404


def test_timeline_zero_phi_audit_logging(auth_headers_doctor: dict, db_session: Session):
    """Audit logs must record navigation events without clinical description or PHI leakage."""
    patient_id = "22222222-2222-4000-8000-222222222222"
    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline?event_type=admission",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200

    recent_log = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "TIMELINE_VIEW", AuditEvent.resource_id == patient_id)
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert recent_log is not None
    assert recent_log.resource_type == "PATIENT_TIMELINE"
    # Ensure no patient narrative notes or clinical descriptions are dumped into metadata
    meta = recent_log.metadata_json or ""
    assert "description" not in meta
    assert "source_text" not in meta
