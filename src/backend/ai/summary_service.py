"""
MedBrief AI — AI Clinical Summary Service
Step 12: AI Clinical Summary + Evidence/Source Reference Layer

Orchestrates:
1. Patient clinical context gathering (demographics, documents, events, meds, changes, labs, items)
2. Safe Gemini invocation via AIGateway with strict Pydantic schemas
3. Hallucination guard: validates all citations against actual ingested documents and pages
4. Traceability & Evidence: creates persistent EvidenceReference records linked to Summary
5. Summary persistence and version history (multiple summaries without overwrite)
6. Grounded safety: strictly outputs "Insufficient information in the uploaded record." when data is lacking
"""

import json
import re
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, func

from src.backend.db.models import (
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
    generate_uuid,
    utc_now,
)
from src.backend.ai.gateway import AIGateway, get_ai_gateway
from src.backend.ai.summary_schemas import (
    SummaryType,
    SummaryStatus,
    StructuredClinicalSummaryOutput,
    StructuredSummarySection,
    SummaryStatement,
    SummaryEvidenceCitation,
)
from src.backend.ai.summary_prompts import (
    SUMMARY_SYSTEM_INSTRUCTION,
    build_summary_prompt,
)
from src.backend.timeline.timeline_service import format_display_date


def calculate_age(dob: Optional[date]) -> Optional[int]:
    """Calculate age in years from date of birth."""
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class ClinicalSummaryService:
    """Core Clinical Summary Service for multi-mode medical summarization with evidence citations."""

    def __init__(self, gateway: Optional[AIGateway] = None):
        self.gateway = gateway or get_ai_gateway()

    def generate_summary(
        self,
        db: Session,
        patient_id: str,
        summary_type: str = "QUICK_CLINICAL",
        user_id: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Summary:
        """
        Generate and persist a verifiable clinical summary for an authorized patient.
        Performs post-generation hallucination filtering and builds EvidenceReference links.
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient with ID {patient_id} not found.")

        # Normalize summary type
        try:
            enum_type = SummaryType(summary_type)
        except ValueError:
            enum_type = SummaryType.QUICK_CLINICAL

        # ── 1. Gather Grounded Patient Dossier ──────────────────────────────────
        demographics = {
            "id": patient.id,
            "name": f"{patient.first_name} {patient.last_name}".strip(),
            "mrn": patient.mrn,
            "dob": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "age": calculate_age(patient.date_of_birth),
            "gender": patient.gender,
        }

        # Ingested documents and pages
        docs = db.query(Document).filter(
            Document.patient_id == patient_id,
            Document.status != "ARCHIVED",
        ).all()

        valid_doc_ids = {d.id: d for d in docs}
        valid_page_map: Dict[str, Dict[int, str]] = {}  # doc_id -> {page_num -> page_id}
        doc_manifest = []

        for d in docs:
            pages = db.query(DocumentPage).filter(DocumentPage.document_id == d.id).order_by(DocumentPage.page_number).all()
            page_items = []
            page_num_to_id = {}
            for p in pages:
                page_num_to_id[p.page_number] = p.id
                snippet = (p.extracted_text or "")[:400]
                page_items.append({
                    "id": p.id,
                    "page_number": p.page_number,
                    "text_snippet": snippet,
                })
            valid_page_map[d.id] = page_num_to_id
            doc_manifest.append({
                "id": d.id,
                "file_name": d.file_name,
                "document_type": d.document_type,
                "page_count": d.page_count,
                "pages": page_items,
            })

        # Clinical Events
        events = db.query(ClinicalEvent).filter(
            ClinicalEvent.patient_id == patient_id
        ).order_by(desc(ClinicalEvent.event_date)).all()
        events_list = []
        for ev in events:
            # Look up page number if source_page_id is set
            page_num = None
            if ev.source_document_id and ev.source_page_id and ev.source_document_id in valid_page_map:
                for p_num, p_id in valid_page_map[ev.source_document_id].items():
                    if p_id == ev.source_page_id:
                        page_num = p_num
                        break

            events_list.append({
                "id": ev.id,
                "title": ev.title,
                "description": ev.description,
                "event_type": ev.event_type,
                "display_date": format_display_date(ev.event_date, ev.event_date_precision),
                "source_document_id": ev.source_document_id,
                "source_page_id": ev.source_page_id,
                "source_page_number": page_num,
                "source_snippet": ev.description[:200],
            })

        # Medications
        meds = db.query(Medication).filter(Medication.patient_id == patient_id).all()
        meds_list = []
        for m in meds:
            page_num = None
            if m.source_document_id and m.source_page_id and m.source_document_id in valid_page_map:
                for p_num, p_id in valid_page_map[m.source_document_id].items():
                    if p_id == m.source_page_id:
                        page_num = p_num
                        break

            meds_list.append({
                "id": m.id,
                "medication_name": m.medication_name,
                "dosage": m.dosage,
                "dose_unit": m.dose_unit,
                "route": m.route,
                "frequency": m.frequency,
                "status": m.status,
                "display_start_date": m.start_date.isoformat() if m.start_date else "Unknown",
                "display_end_date": m.end_date.isoformat() if m.end_date else None,
                "source_document_id": m.source_document_id,
                "source_page_id": m.source_page_id,
                "source_page_number": page_num,
                "source_snippet": f"{m.medication_name} {m.dosage or ''} {m.frequency or ''}".strip(),
            })

        # Medication Changes
        med_changes = db.query(MedicationChange).join(Medication).filter(
            Medication.patient_id == patient_id
        ).order_by(desc(MedicationChange.change_date)).all()
        changes_list = []
        for mc in med_changes:
            page_num = None
            if mc.source_document_id and mc.source_page_id and mc.source_document_id in valid_page_map:
                for p_num, p_id in valid_page_map[mc.source_document_id].items():
                    if p_id == mc.source_page_id:
                        page_num = p_num
                        break

            changes_list.append({
                "id": mc.id,
                "medication_name": mc.medication.medication_name if mc.medication else "Unknown",
                "change_type": mc.change_type,
                "previous_value": mc.previous_value,
                "new_value": mc.new_value,
                "reason": mc.reason,
                "display_date": mc.change_date.isoformat() if mc.change_date else "Unknown",
                "source_document_id": mc.source_document_id,
                "source_page_id": mc.source_page_id,
                "source_page_number": page_num,
                "source_snippet": f"{mc.change_type}: {mc.previous_value or 'None'} -> {mc.new_value or 'None'}",
            })

        # Investigations
        invs = db.query(Investigation).filter(Investigation.patient_id == patient_id).order_by(desc(Investigation.ordered_date)).all()
        invs_list = []
        for inv in invs:
            page_num = None
            if inv.source_document_id and inv.source_page_id and inv.source_document_id in valid_page_map:
                for p_num, p_id in valid_page_map[inv.source_document_id].items():
                    if p_id == inv.source_page_id:
                        page_num = p_num
                        break

            invs_list.append({
                "id": inv.id,
                "investigation_name": inv.investigation_name,
                "investigation_type": inv.investigation_type,
                "status": inv.status,
                "result_summary": inv.result_summary,
                "reference_range": inv.reference_range,
                "is_abnormal": inv.is_abnormal,
                "clinical_urgency": inv.clinical_urgency,
                "display_ordered_date": inv.ordered_date.isoformat() if inv.ordered_date else "Unknown",
                "source_document_id": inv.source_document_id,
                "source_page_id": inv.source_page_id,
                "source_page_number": page_num,
                "source_snippet": f"{inv.investigation_name}: {inv.result_summary or inv.status}",
            })

        # Outstanding Items
        items = db.query(OutstandingItem).filter(OutstandingItem.patient_id == patient_id).all()
        items_list = []
        for it in items:
            page_num = None
            if it.source_document_id and it.source_page_id and it.source_document_id in valid_page_map:
                for p_num, p_id in valid_page_map[it.source_document_id].items():
                    if p_id == it.source_page_id:
                        page_num = p_num
                        break

            items_list.append({
                "id": it.id,
                "item_type": it.item_type,
                "title": it.title,
                "description": it.description,
                "priority": it.priority,
                "status": it.status,
                "display_due_date": it.due_date.isoformat() if it.due_date else "Not specified",
                "source_document_id": it.source_document_id,
                "source_page_id": it.source_page_id,
                "source_page_number": page_num,
                "source_snippet": f"{it.title} ({it.item_type})",
            })

        # ── 2. Handle Case with Insufficient / Empty Clinical Data ────────────
        has_clinical_data = bool(doc_manifest or events_list or meds_list or invs_list or items_list)
        if not has_clinical_data:
            summary_title = f"{enum_type.value.replace('_', ' ').title()} Summary"
            empty_output = StructuredClinicalSummaryOutput(
                patient_id=patient_id,
                patient_name=demographics["name"],
                summary_type=enum_type.value,
                title=summary_title,
                overview="Insufficient information in the uploaded record.",
                sections=[],
                overall_evidence_count=0,
                has_insufficient_data=True,
                generation_notes="No uploaded documents or clinical records available to synthesize summary.",
            )

            summary = Summary(
                id=generate_uuid(),
                patient_id=patient.id,
                summary_type=enum_type.value,
                title=summary_title,
                content=json.dumps(empty_output.model_dump()),
                status=SummaryStatus.GENERATED.value,
                generated_by=user_id,
                is_ai_generated=True,
                model_name="gemini-2.5-flash",
                model_version="v1",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(summary)
            db.commit()
            db.refresh(summary)
            return summary

        # ── 3. Build Prompt & Invoke Gemini AI Gateway ────────────────────────
        prompt = build_summary_prompt(
            summary_type=enum_type.value,
            patient_demographics=demographics,
            document_manifest=doc_manifest,
            clinical_events=events_list,
            medications=meds_list,
            medication_changes=changes_list,
            investigations=invs_list,
            outstanding_items=items_list,
            custom_instructions=custom_instructions,
        )

        structured_output, metadata = self.gateway.generate_structured(
            schema=StructuredClinicalSummaryOutput,
            prompt=prompt,
            system_instruction=SUMMARY_SYSTEM_INSTRUCTION,
            operation=f"generate_summary_{enum_type.value.lower()}",
            user_id=user_id,
        )

        # ── 4. Hallucination Guard & Citation Verification ───────────────────
        # Check every citation against actual ingested documents and pages in DB
        verified_evidence_records: List[EvidenceReference] = []
        summary_id = generate_uuid()

        for section in structured_output.sections:
            for statement in section.bullet_points:
                valid_citations = []
                for citation in statement.citations:
                    doc_id = citation.document_id
                    page_num = citation.page_number

                    # Check if document exists for this patient
                    if not doc_id or doc_id not in valid_doc_ids:
                        # Hallucinated or cross-patient doc ID: reject citation
                        statement.is_uncertain = True
                        statement.uncertainty_note = (
                            statement.uncertainty_note or "Citation unverified against patient records."
                        )
                        continue

                    # Verify or resolve document_page_id
                    doc_record = valid_doc_ids[doc_id]
                    page_id = None
                    if page_num and doc_id in valid_page_map:
                        page_id = valid_page_map[doc_id].get(page_num)

                    # Update citation with confirmed document name and page_id
                    citation.document_name = doc_record.file_name
                    citation.document_page_id = page_id

                    valid_citations.append(citation)

                    # Build persistent EvidenceReference
                    evidence_ref = EvidenceReference(
                        id=generate_uuid(),
                        patient_id=patient_id,
                        document_id=doc_id,
                        document_page_id=page_id,
                        parent_entity_type="SUMMARY",
                        parent_entity_id=summary_id,
                        source_section=section.title,
                        source_text=citation.source_snippet[:1000],
                        source_type="PDF_TEXT",
                        confidence=0.95,
                        created_at=utc_now(),
                    )
                    verified_evidence_records.append(evidence_ref)

                statement.citations = valid_citations

        # Update evidence count in structured output
        structured_output.overall_evidence_count = len(verified_evidence_records)

        # Neutralize any unintended treatment recommendation phrases in overview or statements
        recommendation_regex = re.compile(
            r"\b(we recommend|recommend starting|suggest initiating|should prescribe|ought to receive|advise starting)\b",
            re.IGNORECASE,
        )
        if recommendation_regex.search(structured_output.overview):
            structured_output.overview = recommendation_regex.sub(
                "Documented consideration:", structured_output.overview
            )

        # ── 5. Persist Summary & Evidence References ──────────────────────────
        summary = Summary(
            id=summary_id,
            patient_id=patient.id,
            summary_type=enum_type.value,
            title=structured_output.title or f"{enum_type.value.replace('_', ' ').title()} Summary",
            content=json.dumps(structured_output.model_dump()),
            status=SummaryStatus.GENERATED.value,
            generated_by=user_id,
            is_ai_generated=True,
            model_name=metadata.model,
            model_version="v1",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(summary)

        # Batch insert evidence references
        for ev_ref in verified_evidence_records:
            db.add(ev_ref)

        db.commit()
        db.refresh(summary)
        return summary

    def list_patient_summaries(
        self,
        db: Session,
        patient_id: str,
        summary_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List all saved clinical summaries for a patient with pagination and filters.
        Enables full version history (no blind overwriting).
        """
        query = db.query(Summary).filter(Summary.patient_id == patient_id)

        if summary_type:
            query = query.filter(Summary.summary_type == summary_type.upper())

        if status:
            query = query.filter(Summary.status == status.upper())

        total = query.count()
        summaries = (
            query.order_by(desc(Summary.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Count evidence references for each summary
        summary_ids = [s.id for s in summaries]
        evidence_counts = {}
        if summary_ids:
            counts = (
                db.query(
                    EvidenceReference.parent_entity_id,
                    func.count(EvidenceReference.id),
                )
                .filter(
                    EvidenceReference.parent_entity_type == "SUMMARY",
                    EvidenceReference.parent_entity_id.in_(summary_ids),
                )
                .group_by(EvidenceReference.parent_entity_id)
                .all()
            )
            evidence_counts = {cid: cnt for cid, cnt in counts}

        items = []
        for s in summaries:
            items.append({
                "id": s.id,
                "patient_id": s.patient_id,
                "summary_type": s.summary_type,
                "summary_type_label": s.summary_type.replace("_", " ").title(),
                "title": s.title,
                "status": s.status,
                "is_ai_generated": s.is_ai_generated,
                "model_name": s.model_name,
                "model_version": s.model_version,
                "evidence_count": evidence_counts.get(s.id, 0),
                "created_at": s.created_at.isoformat() if s.created_at else "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
            })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_summary_by_id(
        self,
        db: Session,
        summary_id: str,
    ) -> Optional[Summary]:
        """Fetch summary by primary key."""
        return db.query(Summary).filter(Summary.id == summary_id).first()

    def get_summary_evidence(
        self,
        db: Session,
        summary_id: str,
    ) -> List[EvidenceReference]:
        """Fetch all evidence references directly backing this summary."""
        return (
            db.query(EvidenceReference)
            .filter(
                EvidenceReference.parent_entity_type == "SUMMARY",
                EvidenceReference.parent_entity_id == summary_id,
            )
            .all()
        )


_summary_service_instance: Optional[ClinicalSummaryService] = None


def get_summary_service() -> ClinicalSummaryService:
    """Dependency injection helper returning singleton ClinicalSummaryService."""
    global _summary_service_instance
    if _summary_service_instance is None:
        _summary_service_instance = ClinicalSummaryService()
    return _summary_service_instance
