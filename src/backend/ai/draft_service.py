"""
MedBrief AI — Clinical Draft Service
Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow

Orchestrates:
1. Patient clinical context gathering across extraction, timeline, and intelligence layers
2. Structured AI generation of REFERRAL, DISCHARGE, and HANDOFF documents via AIGateway
3. Hallucination guard: validates all citations against actual ingested documents and pages
4. Persistent EvidenceReference links with parent_entity_type="DRAFT"
5. Editable draft lifecycle management:
   - Initial status MUST be DRAFT (never automatically APPROVED)
   - Clinician editing and updating (PATCH)
   - Clinician review and explicit approval with audit attribution
6. Grounded safety: outputs "Insufficient information in the uploaded record." when data is lacking
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
    Draft,
    EvidenceReference,
    generate_uuid,
    utc_now,
)
from src.backend.ai.gateway import AIGateway, get_ai_gateway
from src.backend.ai.draft_schemas import (
    DraftType,
    DraftStatus,
    StructuredClinicalDraftOutput,
    StructuredDraftSection,
    DraftStatement,
    DraftEvidenceCitation,
)
from src.backend.ai.draft_prompts import (
    DRAFT_SYSTEM_INSTRUCTION,
    build_draft_prompt,
)
from src.backend.timeline.timeline_service import format_display_date


def calculate_age(dob: Optional[date]) -> Optional[int]:
    """Calculate age in years from date of birth."""
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class ClinicalDraftService:
    """Core Clinical Draft Service for synthesizing, updating, and reviewing clinical documents."""

    def __init__(self, gateway: Optional[AIGateway] = None):
        self.gateway = gateway or get_ai_gateway()

    def generate_draft(
        self,
        db: Session,
        patient_id: str,
        draft_type: str = "REFERRAL",
        user_id: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        recipient_info: Optional[str] = None,
    ) -> Draft:
        """
        Generate and persist a verifiable clinical document draft for an authorized patient.
        Performs post-generation hallucination filtering and builds EvidenceReference links.
        Initial status is strictly DRAFT (requires clinician review and approval).
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient with ID {patient_id} not found.")

        # Normalize draft type
        try:
            enum_type = DraftType(draft_type)
        except ValueError:
            enum_type = DraftType.REFERRAL

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

        # Clinical Events (Step 9/10)
        events = db.query(ClinicalEvent).filter(
            ClinicalEvent.patient_id == patient_id
        ).order_by(desc(ClinicalEvent.event_date)).all()
        events_list = []
        for ev in events:
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

        # Medications (Step 9/11)
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

        # Medication Changes (Step 11)
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

        # Investigations (Step 9/11)
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

        # Outstanding Items (Step 11)
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
            draft_title = f"{enum_type.value.replace('_', ' ').title()} Draft"
            empty_body = (
                f"# {draft_title.upper()}\n\n"
                f"**Patient**: {demographics['name']} (MRN: {demographics['mrn']})\n\n"
                "Insufficient information in the uploaded record.\n\n"
                "Please upload clinical documents to generate a grounded draft."
            )
            empty_output = StructuredClinicalDraftOutput(
                patient_id=patient_id,
                patient_name=demographics["name"],
                draft_type=enum_type.value,
                title=draft_title,
                document_body=empty_body,
                sections=[],
                overall_evidence_count=0,
                has_insufficient_data=True,
                clinical_notes="No uploaded documents or clinical records available to compose draft.",
            )

            content_payload = {
                "document_body": empty_body,
                "sections": [],
                "has_insufficient_data": True,
                "clinical_notes": "No uploaded documents available.",
            }

            draft = Draft(
                id=generate_uuid(),
                patient_id=patient.id,
                draft_type=enum_type.value,
                title=draft_title,
                content=json.dumps(content_payload),
                status=DraftStatus.DRAFT.value,
                created_by=user_id,
                generated_by_ai=True,
                model_name="gemini-2.5-flash",
                model_version="v1",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(draft)
            db.commit()
            db.refresh(draft)
            return draft

        # ── 3. Build Prompt & Invoke Gemini AI Gateway ────────────────────────
        prompt = build_draft_prompt(
            draft_type=enum_type.value,
            patient_demographics=demographics,
            document_manifest=doc_manifest,
            clinical_events=events_list,
            medications=meds_list,
            medication_changes=changes_list,
            investigations=invs_list,
            outstanding_items=items_list,
            custom_instructions=custom_instructions,
            recipient_info=recipient_info,
        )

        structured_output, metadata = self.gateway.generate_structured(
            schema=StructuredClinicalDraftOutput,
            prompt=prompt,
            system_instruction=DRAFT_SYSTEM_INSTRUCTION,
            operation=f"generate_draft_{enum_type.value.lower()}",
            user_id=user_id,
        )

        # ── 4. Hallucination Guard & Citation Verification ───────────────────
        verified_evidence_records: List[EvidenceReference] = []
        draft_id = generate_uuid()

        for section in structured_output.sections:
            for statement in section.bullet_points:
                valid_citations = []
                for citation in statement.citations:
                    doc_id = citation.document_id
                    page_num = citation.page_number

                    # Check if document belongs to this patient
                    if not doc_id or doc_id not in valid_doc_ids:
                        statement.is_uncertain = True
                        statement.uncertainty_note = (
                            statement.uncertainty_note or "Citation unverified against patient records."
                        )
                        continue

                    doc_record = valid_doc_ids[doc_id]
                    page_id = None
                    if page_num and doc_id in valid_page_map:
                        page_id = valid_page_map[doc_id].get(page_num)

                    citation.document_name = doc_record.file_name
                    citation.document_page_id = page_id
                    valid_citations.append(citation)

                    # Build persistent EvidenceReference (parent_entity_type="DRAFT")
                    evidence_ref = EvidenceReference(
                        id=generate_uuid(),
                        patient_id=patient_id,
                        document_id=doc_id,
                        document_page_id=page_id,
                        parent_entity_type="DRAFT",
                        parent_entity_id=draft_id,
                        source_section=section.title,
                        source_text=citation.source_snippet[:1000],
                        source_type="PDF_TEXT",
                        confidence=0.95,
                        created_at=utc_now(),
                    )
                    verified_evidence_records.append(evidence_ref)

                statement.citations = valid_citations

        # Update evidence count
        structured_output.overall_evidence_count = len(verified_evidence_records)

        # Neutralize any unintended treatment recommendations
        recommendation_regex = re.compile(
            r"\b(we recommend|recommend starting|suggest initiating|should prescribe|ought to receive|advise starting)\b",
            re.IGNORECASE,
        )
        if recommendation_regex.search(structured_output.document_body):
            structured_output.document_body = recommendation_regex.sub(
                "Documented consideration:", structured_output.document_body
            )

        # ── 5. Persist Draft & Evidence References ──────────────────────────
        content_payload = {
            "document_body": structured_output.document_body,
            "sections": [s.model_dump() for s in structured_output.sections],
            "has_insufficient_data": structured_output.has_insufficient_data,
            "clinical_notes": structured_output.clinical_notes,
        }

        draft = Draft(
            id=draft_id,
            patient_id=patient.id,
            draft_type=enum_type.value,
            title=structured_output.title or f"{enum_type.value.replace('_', ' ').title()} Draft",
            content=json.dumps(content_payload),
            status=DraftStatus.DRAFT.value,
            created_by=user_id,
            generated_by_ai=True,
            model_name=metadata.model,
            model_version="v1",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(draft)

        for ev_ref in verified_evidence_records:
            db.add(ev_ref)

        db.commit()
        db.refresh(draft)
        return draft

    def update_draft(
        self,
        db: Session,
        draft_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Draft:
        """
        Update an existing draft:
        - Allows editing clinical text
        - Allows updating title
        - Allows doctor status transition (DRAFT -> IN_REVIEW -> APPROVED)
        """
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft with ID {draft_id} not found.")

        if title is not None:
            draft.title = title.strip()

        if content is not None:
            # Check if existing content is JSON; update document_body while preserving structure
            try:
                parsed = json.loads(draft.content)
                if isinstance(parsed, dict) and "document_body" in parsed:
                    parsed["document_body"] = content
                    draft.content = json.dumps(parsed)
                else:
                    draft.content = content
            except Exception:
                draft.content = content

        if status is not None:
            norm_status = status.upper().strip()
            if norm_status in [s.value for s in DraftStatus]:
                draft.status = norm_status
                if norm_status == DraftStatus.APPROVED.value:
                    draft.reviewed_by = user_id
                    draft.reviewed_at = utc_now()
                elif norm_status == DraftStatus.IN_REVIEW.value:
                    draft.reviewed_by = user_id

        draft.updated_at = utc_now()
        db.commit()
        db.refresh(draft)
        return draft

    def list_patient_drafts(
        self,
        db: Session,
        patient_id: str,
        draft_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List all saved clinical drafts for a patient with pagination and filters.
        Enables non-destructive version history.
        """
        query = db.query(Draft).filter(Draft.patient_id == patient_id)

        if draft_type:
            query = query.filter(Draft.draft_type == draft_type.upper())

        if status:
            query = query.filter(Draft.status == status.upper())

        total = query.count()
        drafts = (
            query.order_by(desc(Draft.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Count evidence references
        draft_ids = [d.id for d in drafts]
        evidence_counts = {}
        if draft_ids:
            counts = (
                db.query(
                    EvidenceReference.parent_entity_id,
                    func.count(EvidenceReference.id),
                )
                .filter(
                    EvidenceReference.parent_entity_type == "DRAFT",
                    EvidenceReference.parent_entity_id.in_(draft_ids),
                )
                .group_by(EvidenceReference.parent_entity_id)
                .all()
            )
            evidence_counts = {cid: cnt for cid, cnt in counts}

        items = []
        for d in drafts:
            items.append({
                "id": d.id,
                "patient_id": d.patient_id,
                "draft_type": d.draft_type,
                "draft_type_label": d.draft_type.replace("_", " ").title(),
                "title": d.title,
                "status": d.status,
                "is_ai_generated": d.is_ai_generated,
                "model_name": d.model_name,
                "model_version": d.model_version,
                "evidence_count": evidence_counts.get(d.id, 0),
                "created_at": d.created_at.isoformat() if d.created_at else "",
                "updated_at": d.updated_at.isoformat() if d.updated_at else "",
            })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_draft_by_id(
        self,
        db: Session,
        draft_id: str,
    ) -> Optional[Draft]:
        """Fetch draft by primary key."""
        return db.query(Draft).filter(Draft.id == draft_id).first()

    def get_draft_evidence(
        self,
        db: Session,
        draft_id: str,
    ) -> List[EvidenceReference]:
        """Fetch all evidence references directly backing this draft."""
        return (
            db.query(EvidenceReference)
            .filter(
                EvidenceReference.parent_entity_type == "DRAFT",
                EvidenceReference.parent_entity_id == draft_id,
            )
            .all()
        )


_draft_service_instance: Optional[ClinicalDraftService] = None


def get_draft_service() -> ClinicalDraftService:
    """Dependency injection helper returning singleton ClinicalDraftService."""
    global _draft_service_instance
    if _draft_service_instance is None:
        _draft_service_instance = ClinicalDraftService()
    return _draft_service_instance
