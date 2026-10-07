"""
MedBrief AI — Clinical Timeline Service
Step 10: Clinical Timeline

Transforms fragmented, extracted clinical events into a clear chronological representation
of the documented patient journey.

Principles:
- Pure deterministic construction from structured clinical_events (Zero LLM calls)
- Strict date fidelity: Never invents days, months, or years
- Date precision formatting (EXACT, MONTH_YEAR, YEAR_ONLY, APPROXIMATE, UNKNOWN)
- Clear separation of dated events and "Date not documented" events
- Preserves conflicting documented dates and uncertainties
- Grounded source traceability (document name, page number, verbatim snippet)
- High performance batch queries (zero N+1 queries)
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, and_, func

from src.backend.db.models import (
    ClinicalEvent,
    Document,
    DocumentPage,
    EvidenceReference,
    Patient,
)

# Canonical Event Types & Visual Badges
EVENT_TYPE_METADATA: Dict[str, Dict[str, str]] = {
    "consultation": {"label": "Consultation", "icon": "💬", "badge_class": "consultation"},
    "diagnosis": {"label": "Condition / Diagnosis", "icon": "🩺", "badge_class": "diagnosis"},
    "admission": {"label": "Hospital Admission", "icon": "🏥", "badge_class": "admission"},
    "discharge": {"label": "Hospital Discharge", "icon": "🚪", "badge_class": "discharge"},
    "procedure": {"label": "Procedure", "icon": "🔬", "badge_class": "procedure"},
    "investigation": {"label": "Investigation / Lab", "icon": "🧪", "badge_class": "investigation"},
    "result": {"label": "Test Result", "icon": "📊", "badge_class": "result"},
    "medication_start": {"label": "Medication Started", "icon": "💊", "badge_class": "medication"},
    "medication_stop": {"label": "Medication Stopped", "icon": "🛑", "badge_class": "medication"},
    "medication_change": {"label": "Medication Changed", "icon": "🔄", "badge_class": "medication"},
    "follow_up": {"label": "Follow-Up", "icon": "📅", "badge_class": "follow-up"},
    "referral": {"label": "Referral", "icon": "↗️", "badge_class": "referral"},
    "other": {"label": "Clinical Observation", "icon": "📋", "badge_class": "other"},
}


def normalize_event_type(event_type: Optional[str]) -> str:
    """Normalize event type to lowercase canonical key."""
    if not event_type:
        return "other"
    key = str(event_type).strip().lower().replace(" ", "_")
    return key if key in EVENT_TYPE_METADATA else "other"


def format_display_date(event_date: Optional[datetime], date_precision: Optional[str]) -> str:
    """
    Format clinical event date respecting strict precision rules.
    NEVER invents missing days or months.
    """
    if not event_date:
        return "Date not documented"

    prec = (date_precision or "EXACT").upper().strip()

    if prec == "UNKNOWN":
        return "Date not documented"

    if prec == "YEAR_ONLY":
        return str(event_date.year)

    if prec == "MONTH_YEAR":
        return event_date.strftime("%b %Y")

    if prec == "APPROXIMATE":
        if event_date.month == 1 and event_date.day == 1:
            return f"Approx. {event_date.year}"
        return f"Approx. {event_date.strftime('%b %Y')}"

    # EXACT date
    if event_date.hour != 0 or event_date.minute != 0:
        return event_date.strftime("%d %b %Y, %H:%M")
    return event_date.strftime("%d %b %Y")


def get_event_type_meta(event_type: str) -> Dict[str, str]:
    """Retrieve human-readable label and icon for clinical event type."""
    norm = normalize_event_type(event_type)
    return EVENT_TYPE_METADATA.get(norm, EVENT_TYPE_METADATA["other"])


class TimelineService:
    """Deterministic Clinical Timeline Construction Service."""

    @staticmethod
    def get_patient_timeline(
        db: Session,
        patient_id: str,
        event_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Build complete chronological timeline for an authorized patient record.
        - Deterministic ordering
        - Date precision preservation
        - Batch-resolves documents, pages, and ground truth evidence
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        # Base query for patient's clinical events
        query = db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient_id)

        # Filter by event type
        if event_type and event_type.upper() != "ALL":
            norm_filter = normalize_event_type(event_type)
            query = query.filter(func.lower(ClinicalEvent.event_type) == norm_filter)

        # Filter by date range
        if date_from:
            try:
                dt_from = datetime.fromisoformat(date_from)
                query = query.filter(ClinicalEvent.event_date >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                dt_to = datetime.fromisoformat(date_to)
                query = query.filter(ClinicalEvent.event_date <= dt_to)
            except ValueError:
                pass

        # Text search within title or description
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(ClinicalEvent.title).like(term),
                    func.lower(ClinicalEvent.description).like(term),
                )
            )

        # Total matching events count
        total_matching = query.count()

        # Deterministic sorting
        # We split dated vs undated in Python for clean grouping, but query with deterministic order
        if sort.lower() == "asc":
            raw_events = (
                query.order_by(
                    ClinicalEvent.event_date.asc().nulls_last(),
                    ClinicalEvent.created_at.asc(),
                    ClinicalEvent.id.asc(),
                )
                .all()
            )
        else:
            raw_events = (
                query.order_by(
                    ClinicalEvent.event_date.desc().nulls_last(),
                    ClinicalEvent.created_at.desc(),
                    ClinicalEvent.id.asc(),
                )
                .all()
            )

        if not raw_events:
            return {
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "patient_mrn": patient.mrn,
                "summary": {
                    "total_events": 0,
                    "dated_events_count": 0,
                    "undated_events_count": 0,
                    "first_event_date": None,
                    "last_event_date": None,
                    "event_types": {},
                },
                "groups": [],
                "undated_events": [],
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "sort": sort,
            }

        # ── Batch Load Source Documents, Pages, and Evidence References (Zero N+1) ──
        doc_ids = {e.source_document_id for e in raw_events if e.source_document_id}
        page_ids = {e.source_page_id for e in raw_events if e.source_page_id}
        event_ids = [e.id for e in raw_events]

        doc_map: Dict[str, Document] = {}
        if doc_ids:
            docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            doc_map = {d.id: d for d in docs}

        page_map: Dict[str, DocumentPage] = {}
        if page_ids:
            pages = db.query(DocumentPage).filter(DocumentPage.id.in_(page_ids)).all()
            page_map = {p.id: p for p in pages}

        evidence_map: Dict[str, EvidenceReference] = {}
        if event_ids:
            refs = (
                db.query(EvidenceReference)
                .filter(
                    EvidenceReference.parent_entity_type == "CLINICAL_EVENT",
                    EvidenceReference.parent_entity_id.in_(event_ids),
                )
                .all()
            )
            evidence_map = {r.parent_entity_id: r for r in refs}

        # ── Transform into Rich Timeline Items ──
        dated_items: List[Dict[str, Any]] = []
        undated_items: List[Dict[str, Any]] = []
        event_type_counts: Dict[str, int] = {}

        earliest_date: Optional[datetime] = None
        latest_date: Optional[datetime] = None

        for ev in raw_events:
            norm_type = normalize_event_type(ev.event_type)
            meta = get_event_type_meta(norm_type)
            event_type_counts[norm_type] = event_type_counts.get(norm_type, 0) + 1

            disp_date = format_display_date(ev.event_date, ev.event_date_precision)
            is_dated = bool(ev.event_date and ev.event_date_precision != "UNKNOWN")

            if is_dated and ev.event_date:
                if earliest_date is None or ev.event_date < earliest_date:
                    earliest_date = ev.event_date
                if latest_date is None or ev.event_date > latest_date:
                    latest_date = ev.event_date

            # Source metadata
            source_doc = doc_map.get(ev.source_document_id) if ev.source_document_id else None
            source_page = page_map.get(ev.source_page_id) if ev.source_page_id else None
            evidence_ref = evidence_map.get(ev.id)

            source_dict = {
                "document_id": ev.source_document_id,
                "document_name": source_doc.file_name if source_doc else None,
                "document_type": source_doc.document_type if source_doc else None,
                "page_id": ev.source_page_id,
                "page_number": source_page.page_number if source_page else None,
                "source_snippet": evidence_ref.source_text if evidence_ref else None,
                "source_section": evidence_ref.source_section if evidence_ref else None,
            }

            item = {
                "id": ev.id,
                "patient_id": ev.patient_id,
                "event_type": norm_type,
                "event_type_label": meta["label"],
                "event_type_icon": meta["icon"],
                "badge_class": meta["badge_class"],
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "display_date": disp_date,
                "date_precision": ev.event_date_precision or "EXACT",
                "title": ev.title,
                "description": ev.description,
                "source": source_dict,
                "confidence": ev.confidence,
                "is_conflict": bool(ev.is_conflict),
                "conflict_details": ev.conflict_details,
                "is_ai_generated": bool(ev.is_ai_generated),
                "review_status": ev.review_status or "UNREVIEWED",
                "created_at": ev.created_at.isoformat() if ev.created_at else "",
            }

            if is_dated:
                dated_items.append(item)
            else:
                undated_items.append(item)

        # ── Deterministic Grouping for Dated Items ──
        # Group by Year / Month
        groups_dict: Dict[str, Dict[str, Any]] = {}
        for item in dated_items:
            # Parse ISO date
            dt = datetime.fromisoformat(item["event_date"])
            prec = item["date_precision"]

            if prec == "YEAR_ONLY":
                key = f"{dt.year}"
                label = f"{dt.year}"
                y = dt.year
                m_name = None
            else:
                key = f"{dt.year}-{dt.month:02d}"
                label = dt.strftime("%B %Y")
                y = dt.year
                m_name = dt.strftime("%B")

            if key not in groups_dict:
                groups_dict[key] = {
                    "period_key": key,
                    "year": y,
                    "month_name": m_name,
                    "period_label": label,
                    "event_count": 0,
                    "events": [],
                }

            groups_dict[key]["events"].append(item)
            groups_dict[key]["event_count"] += 1

        # Groups list preserves chronological order
        groups_list = list(groups_dict.values())

        # Pagination over combined items
        all_items = dated_items + undated_items
        total_items = len(all_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = all_items[start_idx:end_idx]
        total_pages = max(1, (total_items + page_size - 1) // page_size)

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_mrn": patient.mrn,
            "summary": {
                "total_events": total_items,
                "dated_events_count": len(dated_items),
                "undated_events_count": len(undated_items),
                "first_event_date": earliest_date.strftime("%d %b %Y") if earliest_date else None,
                "last_event_date": latest_date.strftime("%d %b %Y") if latest_date else None,
                "event_types": event_type_counts,
            },
            "groups": groups_list,
            "undated_events": undated_items,
            "items": paged_items,
            "total": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "sort": sort,
        }

    @staticmethod
    def get_patient_timeline_summary(db: Session, patient_id: str) -> Dict[str, Any]:
        """
        Lightweight endpoint for Patient Overview widget:
        Returns counts and the most recent 3-5 clinical events.
        """
        patient = db.query(Patient.first_name, Patient.last_name, Patient.mrn).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        total_count = db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient_id).count()
        recent_events = (
            db.query(ClinicalEvent)
            .filter(ClinicalEvent.patient_id == patient_id)
            .order_by(
                ClinicalEvent.event_date.desc().nulls_last(),
                ClinicalEvent.created_at.desc(),
            )
            .limit(5)
            .all()
        )

        recent_items = []
        for e in recent_events:
            norm_type = normalize_event_type(e.event_type)
            meta = get_event_type_meta(norm_type)
            recent_items.append({
                "id": e.id,
                "title": e.title,
                "event_type": norm_type,
                "event_type_label": meta["label"],
                "event_type_icon": meta["icon"],
                "display_date": format_display_date(e.event_date, e.event_date_precision),
                "date_precision": e.event_date_precision or "EXACT",
                "description": e.description[:120] + "..." if len(e.description) > 120 else e.description,
            })

        return {
            "patient_id": patient_id,
            "patient_name": f"{patient[0]} {patient[1]}",
            "patient_mrn": patient[2],
            "total_events": total_count,
            "recent_events": recent_items,
        }


# Singleton service instance
timeline_service = TimelineService()


def get_timeline_service() -> TimelineService:
    """Dependency provider for FastAPI route injection."""
    return timeline_service
