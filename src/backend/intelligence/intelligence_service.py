"""
MedBrief AI — Medication & Investigation Intelligence Service
Step 11: Medication + Investigation Intelligence

Core Intelligence Layer:
A. Medication Change Intelligence (started, stopped, dose/freq/route changes, chronological comparison, conflicting records)
B. Investigation Intelligence (ordered, pending, completed, cancelled; strict rules for pending states)
C. Outstanding / Pending Clinical Items (follow-ups, monitoring, reviews, handoffs)

Principles:
- 100% Documented Information Only (Zero invented facts, diagnoses, or recommendations)
- Pure deterministic logic: Zero LLM calls for sorting, grouping, or status detection
- Explicit distinction between DOCUMENTED facts and DERIVED comparisons
- Dose comparison (5 mg -> 10 mg) only generated when BOTH values exist in the record
- Missing result does NOT automatically mean pending; only marked PENDING when explicitly supported
- Medication disappearing from later document is NEVER assumed stopped
- Conflicting source information is preserved and flagged with source links
- Strict date precision formatting (no invented days, months, or years)
- Batch preloading of documents, pages, and evidence (Zero N+1 queries)
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, and_, func

from src.backend.db.models import (
    Medication,
    MedicationChange,
    Investigation,
    OutstandingItem,
    ClinicalEvent,
    Document,
    DocumentPage,
    EvidenceReference,
    Patient,
)
from src.backend.timeline.timeline_service import format_display_date


# ── Explicit Keyword Helpers for Investigation Status ──────────────────────────

PENDING_EXPLICIT_KEYWORDS = [
    "pending",
    "awaiting result",
    "awaiting results",
    "results awaited",
    "result awaited",
    "awaited",
    "follow up after",
    "follow-up after",
    "outstanding report",
    "to be reviewed upon receipt",
    "sample sent",
    "specimen sent",
    "scheduled for",
]


def is_explicitly_pending(
    raw_status: Optional[str],
    result_text: Optional[str] = None,
    source_snippet: Optional[str] = None,
) -> bool:
    """
    Strict rule: Only mark an investigation as PENDING when the source
    explicitly supports a pending/unresolved state.
    A missing result does NOT automatically mean pending!
    """
    if raw_status and raw_status.strip().upper() == "PENDING":
        return True

    text_corpus = f"{result_text or ''} {source_snippet or ''}".lower()
    return any(keyword in text_corpus for keyword in PENDING_EXPLICIT_KEYWORDS)


class ClinicalIntelligenceService:
    """Core Clinical Intelligence Service for Medications, Investigations, and Outstanding Items."""

    # ──────────────────────────────────────────────────────────────────────────
    # 1. MEDICATION INTELLIGENCE
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_patient_medications(
        db: Session,
        patient_id: str,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieve structured medications documented for an authorized patient.
        Supports filtering by status (ACTIVE, STOPPED, HISTORICAL, UNKNOWN),
        search by drug name, and batch source evidence preloading.
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        query = db.query(Medication).filter(Medication.patient_id == patient_id)

        # Status filter
        if status and status.upper() != "ALL":
            norm_status = status.strip().upper()
            query = query.filter(Medication.status == norm_status)

        # Search filter
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Medication.medication_name).like(term),
                    func.lower(Medication.generic_name).like(term),
                )
            )

        total_count = query.count()

        # Deterministic sorting
        if sort.lower() == "asc":
            meds = (
                query.order_by(
                    Medication.start_date.asc().nulls_last(),
                    Medication.created_at.asc(),
                    Medication.id.asc(),
                )
                .all()
            )
        else:
            meds = (
                query.order_by(
                    Medication.start_date.desc().nulls_last(),
                    Medication.created_at.desc(),
                    Medication.id.asc(),
                )
                .all()
            )

        if not meds:
            return {
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "patient_mrn": patient.mrn,
                "summary": {
                    "total_medications": 0,
                    "active_count": 0,
                    "stopped_count": 0,
                    "historical_count": 0,
                    "unknown_count": 0,
                },
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "message": "No documented medications found in the available record.",
            }

        # ── Batch Preload Source Documents, Pages, Evidence References (Zero N+1) ──
        doc_ids = {m.source_document_id for m in meds if m.source_document_id}
        page_ids = {m.source_page_id for m in meds if m.source_page_id}
        med_ids = [m.id for m in meds]

        doc_map = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
        page_map = {p.id: p for p in db.query(DocumentPage).filter(DocumentPage.id.in_(page_ids)).all()} if page_ids else {}

        evidence_map: Dict[str, EvidenceReference] = {}
        if med_ids:
            refs = (
                db.query(EvidenceReference)
                .filter(
                    EvidenceReference.parent_entity_type == "MEDICATION",
                    EvidenceReference.parent_entity_id.in_(med_ids),
                )
                .all()
            )
            evidence_map = {r.parent_entity_id: r for r in refs}

        # Batch preload medication changes count
        change_counts: Dict[str, int] = {}
        if med_ids:
            c_rows = (
                db.query(MedicationChange.medication_id, func.count(MedicationChange.id))
                .filter(MedicationChange.medication_id.in_(med_ids))
                .group_by(MedicationChange.medication_id)
                .all()
            )
            change_counts = {row[0]: row[1] for row in c_rows}

        # Status counts calculation
        active_count = 0
        stopped_count = 0
        historical_count = 0
        unknown_count = 0

        # Group by drug name to detect potential conflicts across documents
        name_groups: Dict[str, List[Medication]] = {}
        for m in meds:
            key = (m.generic_name or m.medication_name or "").strip().lower()
            name_groups.setdefault(key, []).append(m)

        items = []
        for m in meds:
            if m.status == "ACTIVE":
                active_count += 1
            elif m.status == "STOPPED":
                stopped_count += 1
            elif m.status == "HISTORICAL":
                historical_count += 1
            else:
                unknown_count += 1

            source_doc = doc_map.get(m.source_document_id)
            source_page = page_map.get(m.source_page_id)
            evidence_ref = evidence_map.get(m.id)

            # Check if this medication has discordant dosages documented across records
            key = (m.generic_name or m.medication_name or "").strip().lower()
            group = name_groups.get(key, [])
            is_conflict = False
            conflict_details = None

            if len(group) > 1:
                dosages = {g.dosage for g in group if g.dosage}
                if len(dosages) > 1 and change_counts.get(m.id, 0) == 0:
                    is_conflict = True
                    conflict_details = f"Discordant dosages ({', '.join(sorted(dosages))}) documented across source records without recorded transition."

            source_dict = {
                "document_id": m.source_document_id,
                "document_name": source_doc.file_name if source_doc else None,
                "document_type": source_doc.document_type if source_doc else None,
                "page_id": m.source_page_id,
                "page_number": source_page.page_number if source_page else None,
                "source_snippet": evidence_ref.source_text if evidence_ref else None,
                "source_section": evidence_ref.source_section if evidence_ref else None,
            }

            items.append({
                "id": m.id,
                "patient_id": m.patient_id,
                "medication_name": m.medication_name,
                "generic_name": m.generic_name,
                "dosage": m.dosage,
                "dose_unit": m.dose_unit,
                "route": m.route,
                "frequency": m.frequency,
                "status": m.status or "UNKNOWN",
                "start_date": m.start_date.isoformat() if m.start_date else None,
                "end_date": m.end_date.isoformat() if m.end_date else None,
                "display_start_date": m.start_date.strftime("%d %b %Y") if m.start_date else "Date not documented",
                "display_end_date": m.end_date.strftime("%d %b %Y") if m.end_date else None,
                "source": source_dict,
                "origin": "DOCUMENTED",
                "is_conflict": is_conflict,
                "conflict_details": conflict_details,
                "changes_count": change_counts.get(m.id, 0),
                "created_at": m.created_at.isoformat() if m.created_at else "",
            })

        # Paginate items
        start_idx = (page - 1) * page_size
        paged_items = items[start_idx : start_idx + page_size]
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_mrn": patient.mrn,
            "summary": {
                "total_medications": total_count,
                "active_count": active_count,
                "stopped_count": stopped_count,
                "historical_count": historical_count,
                "unknown_count": unknown_count,
            },
            "items": paged_items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 2. MEDICATION CHANGE INTELLIGENCE
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_patient_medication_changes(
        db: Session,
        patient_id: str,
        change_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Identify and compare medication events over time:
        - Explicit documented changes from medication_changes
        - Derived historical dose/frequency/route changes where both previous and new values are documented
        - Flagging conflicting regimens
        - Zero false assumptions: missing previous dose != change, disappearing med != stopped
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        # 1. Fetch explicit medication_changes
        q_changes = (
            db.query(MedicationChange, Medication)
            .join(Medication, MedicationChange.medication_id == Medication.id)
            .filter(Medication.patient_id == patient_id)
        )

        if change_type and change_type.upper() != "ALL":
            norm_type = change_type.strip().upper()
            q_changes = q_changes.filter(MedicationChange.change_type == norm_type)

        if date_from:
            try:
                dt_f = datetime.fromisoformat(date_from).date()
                q_changes = q_changes.filter(MedicationChange.change_date >= dt_f)
            except ValueError:
                pass

        if date_to:
            try:
                dt_t = datetime.fromisoformat(date_to).date()
                q_changes = q_changes.filter(MedicationChange.change_date <= dt_t)
            except ValueError:
                pass

        explicit_records = q_changes.all()

        # Batch preload for explicit records
        doc_ids = {c.source_document_id for c, _ in explicit_records if c.source_document_id}
        page_ids = {c.source_page_id for c, _ in explicit_records if c.source_page_id}
        change_ids = [c.id for c, _ in explicit_records]

        doc_map = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
        page_map = {p.id: p for p in db.query(DocumentPage).filter(DocumentPage.id.in_(page_ids)).all()} if page_ids else {}

        evidence_map: Dict[str, EvidenceReference] = {}
        if change_ids:
            refs = (
                db.query(EvidenceReference)
                .filter(
                    EvidenceReference.parent_entity_type == "MEDICATION_CHANGE",
                    EvidenceReference.parent_entity_id.in_(change_ids),
                )
                .all()
            )
            evidence_map = {r.parent_entity_id: r for r in refs}

        formatted_changes: List[Dict[str, Any]] = []
        covered_med_names = set()

        for c, med in explicit_records:
            source_doc = doc_map.get(c.source_document_id)
            source_page = page_map.get(c.source_page_id)
            evidence_ref = evidence_map.get(c.id)

            med_name = med.medication_name or med.generic_name or "Medication"
            covered_med_names.add(med_name.lower())

            # Format human-readable change description
            if c.change_type == "DOSE_CHANGED":
                desc = f"Documented dose change: {c.previous_value or '—'} → {c.new_value or '—'}"
            elif c.change_type == "STARTED":
                desc = f"Medication started: {med_name} {c.new_value or med.dosage or ''}".strip()
            elif c.change_type == "STOPPED":
                desc = f"Medication stopped: {med_name}"
            elif c.change_type == "FREQUENCY_CHANGED":
                desc = f"Documented frequency change: {c.previous_value or '—'} → {c.new_value or '—'}"
            elif c.change_type == "ROUTE_CHANGED":
                desc = f"Documented route change: {c.previous_value or '—'} → {c.new_value or '—'}"
            else:
                desc = c.reason or f"Documented {c.change_type.lower().replace('_', ' ')}"

            formatted_changes.append({
                "id": c.id,
                "medication_id": c.medication_id,
                "medication_name": med_name,
                "generic_name": med.generic_name,
                "change_type": c.change_type,
                "change_type_label": c.change_type.replace("_", " ").title(),
                "previous_value": c.previous_value,
                "new_value": c.new_value,
                "change_date": c.change_date.isoformat() if c.change_date else None,
                "display_date": c.change_date.strftime("%d %b %Y") if c.change_date else "Date not documented",
                "description": desc,
                "reason": c.reason,
                "origin": "DOCUMENTED",
                "is_conflict": False,
                "conflict_details": None,
                "is_ai_generated": bool(c.is_ai_generated),
                "source": {
                    "document_id": c.source_document_id,
                    "document_name": source_doc.file_name if source_doc else None,
                    "document_type": source_doc.document_type if source_doc else None,
                    "page_id": c.source_page_id,
                    "page_number": source_page.page_number if source_page else None,
                    "source_snippet": evidence_ref.source_text if evidence_ref else None,
                    "source_section": evidence_ref.source_section if evidence_ref else None,
                },
                "created_at": c.created_at.isoformat() if c.created_at else "",
            })

        # 2. Historical comparison across all Medication records
        # Check for changes between successive medication records not already represented in explicit changes
        all_meds = (
            db.query(Medication)
            .filter(Medication.patient_id == patient_id)
            .order_by(Medication.start_date.asc().nulls_last(), Medication.created_at.asc())
            .all()
        )

        meds_by_name: Dict[str, List[Medication]] = {}
        for m in all_meds:
            norm_k = (m.generic_name or m.medication_name or "").strip().lower()
            meds_by_name.setdefault(norm_k, []).append(m)

        for norm_name, records in meds_by_name.items():
            if len(records) < 2:
                continue

            for i in range(len(records) - 1):
                prev_rec = records[i]
                curr_rec = records[i + 1]

                # Compare doses strictly when BOTH values exist and are different
                if prev_rec.dosage and curr_rec.dosage and prev_rec.dosage.strip() != curr_rec.dosage.strip():
                    p_dose = f"{prev_rec.dosage} {prev_rec.dose_unit or ''}".strip()
                    c_dose = f"{curr_rec.dosage} {curr_rec.dose_unit or ''}".strip()

                    # Avoid duplicate if explicit record already captured this
                    already_captured = any(
                        fc["medication_name"].lower() == curr_rec.medication_name.lower()
                        and fc["change_type"] == "DOSE_CHANGED"
                        and fc["previous_value"] == p_dose
                        and fc["new_value"] == c_dose
                        for fc in formatted_changes
                    )

                    if not already_captured:
                        formatted_changes.append({
                            "id": f"derived-dose-{prev_rec.id}-{curr_rec.id}",
                            "medication_id": curr_rec.id,
                            "medication_name": curr_rec.medication_name,
                            "generic_name": curr_rec.generic_name,
                            "change_type": "DOSE_CHANGED",
                            "change_type_label": "Dose Changed",
                            "previous_value": p_dose,
                            "new_value": c_dose,
                            "change_date": curr_rec.start_date.isoformat() if curr_rec.start_date else None,
                            "display_date": curr_rec.start_date.strftime("%d %b %Y") if curr_rec.start_date else "Date not documented",
                            "description": f"Documented dose change: {p_dose} → {c_dose}",
                            "reason": "Derived from sequential clinical documentation",
                            "origin": "DERIVED",
                            "is_conflict": False,
                            "conflict_details": None,
                            "is_ai_generated": True,
                            "source": {
                                "document_id": curr_rec.source_document_id,
                                "document_name": None,
                                "document_type": None,
                                "page_id": curr_rec.source_page_id,
                                "page_number": None,
                                "source_snippet": None,
                                "source_section": "Sequential Medication Reconciliation",
                            },
                            "created_at": curr_rec.created_at.isoformat() if curr_rec.created_at else "",
                        })

                # Compare frequency strictly when BOTH values exist and are different
                if prev_rec.frequency and curr_rec.frequency and prev_rec.frequency.strip().lower() != curr_rec.frequency.strip().lower():
                    already_captured = any(
                        fc["medication_name"].lower() == curr_rec.medication_name.lower()
                        and fc["change_type"] == "FREQUENCY_CHANGED"
                        for fc in formatted_changes
                    )
                    if not already_captured:
                        formatted_changes.append({
                            "id": f"derived-freq-{prev_rec.id}-{curr_rec.id}",
                            "medication_id": curr_rec.id,
                            "medication_name": curr_rec.medication_name,
                            "generic_name": curr_rec.generic_name,
                            "change_type": "FREQUENCY_CHANGED",
                            "change_type_label": "Frequency Changed",
                            "previous_value": prev_rec.frequency,
                            "new_value": curr_rec.frequency,
                            "change_date": curr_rec.start_date.isoformat() if curr_rec.start_date else None,
                            "display_date": curr_rec.start_date.strftime("%d %b %Y") if curr_rec.start_date else "Date not documented",
                            "description": f"Documented frequency change: {prev_rec.frequency} → {curr_rec.frequency}",
                            "reason": "Derived from sequential clinical documentation",
                            "origin": "DERIVED",
                            "is_conflict": False,
                            "conflict_details": None,
                            "is_ai_generated": True,
                            "source": {
                                "document_id": curr_rec.source_document_id,
                                "document_name": None,
                                "document_type": None,
                                "page_id": curr_rec.source_page_id,
                                "page_number": None,
                                "source_snippet": None,
                                "source_section": "Sequential Medication Reconciliation",
                            },
                            "created_at": curr_rec.created_at.isoformat() if curr_rec.created_at else "",
                        })

        # Deterministic sorting of combined changes
        def change_sort_key(item: Dict[str, Any]):
            d_str = item.get("change_date")
            dt = datetime.fromisoformat(d_str) if d_str else datetime.min
            return dt

        formatted_changes.sort(key=change_sort_key, reverse=(sort.lower() == "desc"))

        # Summary statistics
        total_changes = len(formatted_changes)
        started_count = sum(1 for c in formatted_changes if c["change_type"] == "STARTED")
        stopped_count = sum(1 for c in formatted_changes if c["change_type"] == "STOPPED")
        dose_changes_count = sum(1 for c in formatted_changes if c["change_type"] == "DOSE_CHANGED")
        freq_changes_count = sum(1 for c in formatted_changes if c["change_type"] == "FREQUENCY_CHANGED")
        route_changes_count = sum(1 for c in formatted_changes if c["change_type"] == "ROUTE_CHANGED")

        # Paginate
        start_idx = (page - 1) * page_size
        paged_items = formatted_changes[start_idx : start_idx + page_size]
        total_pages = max(1, (total_changes + page_size - 1) // page_size)

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_mrn": patient.mrn,
            "summary": {
                "total_changes": total_changes,
                "started_count": started_count,
                "stopped_count": stopped_count,
                "dose_changes_count": dose_changes_count,
                "frequency_changes_count": freq_changes_count,
                "route_changes_count": route_changes_count,
            },
            "items": paged_items,
            "total": total_changes,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "message": "No documented medication changes found in the available record." if total_changes == 0 else None,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 3. INVESTIGATION INTELLIGENCE
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_patient_investigations(
        db: Session,
        patient_id: str,
        status: Optional[str] = None,
        investigation_type: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "desc",
        page: int = 1,
        page_size: int = 200,
    ) -> Dict[str, Any]:
        """
        Retrieve structured investigations and diagnostic reports.
        Adheres to strict status classification rules:
        - Only mark PENDING when the source explicitly supports it (e.g. 'pending', 'awaiting results')
        - Missing result does NOT automatically mean pending!
        - Preserve UNKNOWN when the source does not establish the status
        - Preserve conflicting statuses chronologically
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        query = db.query(Investigation).filter(Investigation.patient_id == patient_id)

        # Status filter
        if status and status.upper() != "ALL":
            norm_status = status.strip().upper()
            query = query.filter(Investigation.status == norm_status)

        # Investigation type filter
        if investigation_type and investigation_type.upper() != "ALL":
            norm_type = investigation_type.strip().upper()
            query = query.filter(Investigation.investigation_type == norm_type)

        # Search filter
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Investigation.investigation_name).like(term),
                    func.lower(Investigation.result_summary).like(term),
                )
            )

        total_count = query.count()

        # Deterministic sorting
        if sort.lower() == "asc":
            raw_invs = (
                query.order_by(
                    func.coalesce(Investigation.completed_date, Investigation.ordered_date).asc().nulls_last(),
                    Investigation.created_at.asc(),
                    Investigation.id.asc(),
                )
                .all()
            )
        else:
            raw_invs = (
                query.order_by(
                    func.coalesce(Investigation.completed_date, Investigation.ordered_date).desc().nulls_last(),
                    Investigation.created_at.desc(),
                    Investigation.id.asc(),
                )
                .all()
            )

        if not raw_invs:
            return {
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "patient_mrn": patient.mrn,
                "summary": {
                    "total_investigations": 0,
                    "completed_count": 0,
                    "pending_count": 0,
                    "ordered_count": 0,
                    "cancelled_count": 0,
                    "unknown_count": 0,
                    "abnormal_count": 0,
                },
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "message": "No documented investigations found in the available record.",
            }

        # Batch preload source documents, pages, and evidence
        doc_ids = {inv.source_document_id for inv in raw_invs if inv.source_document_id}
        page_ids = {inv.source_page_id for inv in raw_invs if inv.source_page_id}
        inv_ids = [inv.id for inv in raw_invs]

        doc_map = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
        page_map = {p.id: p for p in db.query(DocumentPage).filter(DocumentPage.id.in_(page_ids)).all()} if page_ids else {}

        evidence_map: Dict[str, EvidenceReference] = {}
        if inv_ids:
            refs = (
                db.query(EvidenceReference)
                .filter(
                    EvidenceReference.parent_entity_type == "INVESTIGATION",
                    EvidenceReference.parent_entity_id.in_(inv_ids),
                )
                .all()
            )
            evidence_map = {r.parent_entity_id: r for r in refs}

        # Status counts
        completed_count = 0
        pending_count = 0
        ordered_count = 0
        cancelled_count = 0
        unknown_count = 0
        abnormal_count = 0

        # Group by name to detect chronological conflict / resolution
        inv_by_name: Dict[str, List[Investigation]] = {}
        for inv in raw_invs:
            key = inv.investigation_name.strip().lower()
            inv_by_name.setdefault(key, []).append(inv)

        items = []
        for inv in raw_invs:
            evidence_ref = evidence_map.get(inv.id)
            source_snippet = evidence_ref.source_text if evidence_ref else None

            # Evaluate final status respecting strict pending rule
            evaluated_status = inv.status or "UNKNOWN"
            # If marked ORDERED or UNKNOWN, check if explicit pending phrase is documented
            if evaluated_status in ("ORDERED", "UNKNOWN"):
                if is_explicitly_pending(inv.status, inv.result_summary, source_snippet):
                    evaluated_status = "PENDING"

            if evaluated_status == "COMPLETED":
                completed_count += 1
            elif evaluated_status == "PENDING":
                pending_count += 1
            elif evaluated_status == "ORDERED":
                ordered_count += 1
            elif evaluated_status == "CANCELLED":
                cancelled_count += 1
            else:
                unknown_count += 1

            if inv.is_abnormal:
                abnormal_count += 1

            # Chronological conflict check
            # E.g. Earlier doc says PENDING, later doc says COMPLETED -> show progression
            key = inv.investigation_name.strip().lower()
            group = inv_by_name.get(key, [])
            is_conflict = False
            conflict_details = None

            if len(group) > 1:
                statuses = {g.status for g in group if g.status}
                results = {g.result_summary for g in group if g.result_summary}
                abnormals = {g.is_abnormal for g in group if g.is_abnormal is not None}
                if len(statuses) > 1:
                    is_conflict = True
                    conflict_details = f"Multiple documented records with statuses: {', '.join(sorted(statuses))}."
                elif len(abnormals) > 1 or len(results) > 1:
                    is_conflict = True
                    conflict_details = f"Discordant documented results across reports: {', '.join(sorted(results))}."

            source_doc = doc_map.get(inv.source_document_id)
            source_page = page_map.get(inv.source_page_id)

            disp_date = None
            if inv.completed_date:
                disp_date = inv.completed_date.strftime("%d %b %Y")
            elif inv.ordered_date:
                disp_date = f"Ordered {inv.ordered_date.strftime('%d %b %Y')}"
            else:
                disp_date = "Date not documented"

            items.append({
                "id": inv.id,
                "patient_id": inv.patient_id,
                "investigation_name": inv.investigation_name,
                "investigation_type": inv.investigation_type,
                "ordered_date": inv.ordered_date.isoformat() if inv.ordered_date else None,
                "completed_date": inv.completed_date.isoformat() if inv.completed_date else None,
                "display_date": disp_date,
                "status": evaluated_status,
                "result_summary": inv.result_summary,
                "reference_range": inv.reference_range,
                "is_abnormal": bool(inv.is_abnormal),
                "clinical_urgency": inv.clinical_urgency or "NORMAL",
                "origin": "DOCUMENTED",
                "is_conflict": is_conflict,
                "conflict_details": conflict_details,
                "source": {
                    "document_id": inv.source_document_id,
                    "document_name": source_doc.file_name if source_doc else None,
                    "document_type": source_doc.document_type if source_doc else None,
                    "page_id": inv.source_page_id,
                    "page_number": source_page.page_number if source_page else None,
                    "source_snippet": source_snippet,
                    "source_section": evidence_ref.source_section if evidence_ref else None,
                },
                "created_at": inv.created_at.isoformat() if inv.created_at else "",
            })

        # Paginate
        start_idx = (page - 1) * page_size
        paged_items = items[start_idx : start_idx + page_size]
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_mrn": patient.mrn,
            "summary": {
                "total_investigations": total_count,
                "completed_count": completed_count,
                "pending_count": pending_count,
                "ordered_count": ordered_count,
                "cancelled_count": cancelled_count,
                "unknown_count": unknown_count,
                "abnormal_count": abnormal_count,
            },
            "items": paged_items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "message": "No documented investigations found in the available record." if total_count == 0 else None,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 4. OUTSTANDING / PENDING CLINICAL ITEMS
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_patient_outstanding_items(
        db: Session,
        patient_id: str,
        item_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sort: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieve doctor-facing outstanding/pending clinical items:
        - PENDING_INVESTIGATION
        - FOLLOW_UP
        - MEDICATION_REVIEW
        - SPECIALIST_FOLLOW_UP
        - MONITORING
        - DOCUMENTATION
        - OTHER
        Traceable to source document, page, and verbatim evidence.
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        query = db.query(OutstandingItem).filter(OutstandingItem.patient_id == patient_id)

        if item_type and item_type.upper() != "ALL":
            norm_type = item_type.strip().upper()
            query = query.filter(OutstandingItem.item_type == norm_type)

        if status and status.upper() != "ALL":
            norm_status = status.strip().upper()
            query = query.filter(OutstandingItem.status == norm_status)

        if priority and priority.upper() != "ALL":
            norm_prio = priority.strip().upper()
            query = query.filter(OutstandingItem.priority == norm_prio)

        total_count = query.count()

        if sort.lower() == "asc":
            raw_items = (
                query.order_by(
                    OutstandingItem.due_date.asc().nulls_last(),
                    OutstandingItem.created_at.asc(),
                    OutstandingItem.id.asc(),
                )
                .all()
            )
        else:
            raw_items = (
                query.order_by(
                    OutstandingItem.due_date.desc().nulls_last(),
                    OutstandingItem.created_at.desc(),
                    OutstandingItem.id.asc(),
                )
                .all()
            )

        if not raw_items:
            return {
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "patient_mrn": patient.mrn,
                "summary": {
                    "total_outstanding": 0,
                    "open_count": 0,
                    "high_priority_count": 0,
                    "type_counts": {},
                },
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "message": "No documented outstanding clinical items found.",
            }

        # Batch preload
        doc_ids = {it.source_document_id for it in raw_items if it.source_document_id}
        page_ids = {it.source_page_id for it in raw_items if it.source_page_id}
        item_ids = [it.id for it in raw_items]

        doc_map = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
        page_map = {p.id: p for p in db.query(DocumentPage).filter(DocumentPage.id.in_(page_ids)).all()} if page_ids else {}

        evidence_map: Dict[str, EvidenceReference] = {}
        if item_ids:
            refs = (
                db.query(EvidenceReference)
                .filter(
                    EvidenceReference.parent_entity_type == "OUTSTANDING_ITEM",
                    EvidenceReference.parent_entity_id.in_(item_ids),
                )
                .all()
            )
            evidence_map = {r.parent_entity_id: r for r in refs}

        open_count = 0
        high_priority_count = 0
        type_counts: Dict[str, int] = {}

        items = []
        for it in raw_items:
            if it.status in ("OPEN", "IN_PROGRESS"):
                open_count += 1
            if it.priority in ("HIGH", "CRITICAL"):
                high_priority_count += 1

            type_counts[it.item_type] = type_counts.get(it.item_type, 0) + 1

            source_doc = doc_map.get(it.source_document_id)
            source_page = page_map.get(it.source_page_id)
            evidence_ref = evidence_map.get(it.id)

            disp_date = it.due_date.strftime("%d %b %Y") if it.due_date else "No due date documented"

            items.append({
                "id": it.id,
                "patient_id": it.patient_id,
                "item_type": it.item_type,
                "item_type_label": it.item_type.replace("_", " ").title(),
                "title": it.title,
                "description": it.description,
                "priority": it.priority,
                "status": it.status,
                "due_date": it.due_date.isoformat() if it.due_date else None,
                "display_due_date": disp_date,
                "origin": "AI_EXTRACTED" if it.is_ai_generated else "DOCUMENTED",
                "is_ai_generated": bool(it.is_ai_generated),
                "review_status": it.review_status,
                "source": {
                    "document_id": it.source_document_id,
                    "document_name": source_doc.file_name if source_doc else None,
                    "document_type": source_doc.document_type if source_doc else None,
                    "page_id": it.source_page_id,
                    "page_number": source_page.page_number if source_page else None,
                    "source_snippet": evidence_ref.source_text if evidence_ref else None,
                    "source_section": evidence_ref.source_section if evidence_ref else None,
                },
                "created_at": it.created_at.isoformat() if it.created_at else "",
            })

        start_idx = (page - 1) * page_size
        paged_items = items[start_idx : start_idx + page_size]
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_mrn": patient.mrn,
            "summary": {
                "total_outstanding": total_count,
                "open_count": open_count,
                "high_priority_count": high_priority_count,
                "type_counts": type_counts,
            },
            "items": paged_items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "message": "No documented outstanding clinical items found." if total_count == 0 else None,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 5. UNIFIED CLINICAL INTELLIGENCE SUMMARY
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_patient_intelligence_summary(db: Session, patient_id: str) -> Dict[str, Any]:
        """
        Lightweight aggregated intelligence payload for Patient Overview and Doctor Dashboard:
        - Active medications count & latest changes
        - Total / pending investigations & abnormal count
        - Outstanding follow-ups and monitoring items
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        # 1. Medications quick stats
        total_meds = db.query(Medication).filter(Medication.patient_id == patient_id).count()
        active_meds = db.query(Medication).filter(Medication.patient_id == patient_id, Medication.status == "ACTIVE").count()

        # 2. Medication changes
        med_changes_res = ClinicalIntelligenceService.get_patient_medication_changes(db, patient_id, page_size=3)
        total_med_changes = med_changes_res.get("total", 0)
        recent_changes = med_changes_res.get("items", [])[:3]

        # 3. Investigations quick stats
        total_invs = db.query(Investigation).filter(Investigation.patient_id == patient_id).count()
        completed_invs = db.query(Investigation).filter(Investigation.patient_id == patient_id, Investigation.status == "COMPLETED").count()
        abnormal_invs = db.query(Investigation).filter(Investigation.patient_id == patient_id, Investigation.is_abnormal == True).count()

        # Explicitly pending investigations
        pending_invs_res = ClinicalIntelligenceService.get_patient_investigations(db, patient_id, status="PENDING", page_size=3)
        pending_count = pending_invs_res.get("total", 0)
        recent_pending_invs = pending_invs_res.get("items", [])[:3]

        # 4. Outstanding Items
        outstanding_res = ClinicalIntelligenceService.get_patient_outstanding_items(db, patient_id, status="OPEN", page_size=3)
        total_outstanding = outstanding_res.get("total", 0)
        recent_outstanding = outstanding_res.get("items", [])[:3]

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_mrn": patient.mrn,
            "medications": {
                "total_count": total_meds,
                "active_count": active_meds,
                "changes_count": total_med_changes,
                "recent_changes": recent_changes,
            },
            "investigations": {
                "total_count": total_invs,
                "completed_count": completed_invs,
                "pending_count": pending_count,
                "abnormal_count": abnormal_invs,
                "recent_pending": recent_pending_invs,
            },
            "outstanding_items": {
                "open_count": total_outstanding,
                "recent_items": recent_outstanding,
            },
        }


# Global singleton instance
intelligence_service = ClinicalIntelligenceService()


def get_intelligence_service() -> ClinicalIntelligenceService:
    """Dependency provider for FastAPI route injection."""
    return intelligence_service
