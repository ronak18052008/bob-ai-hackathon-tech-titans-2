"""
MedBrief AI — Medical Information Extraction Service
Step 9: Medical Information Extraction

Orchestrates the page-aware clinical extraction pipeline:
1. Ingests document pages from private storage via pypdf (without faking OCR)
2. Executes page-aware extraction through the Step 8 Gemini AI Gateway
3. Strictly validates structured Pydantic schemas (events, conditions, meds, labs, procedures, follow-ups)
4. Persists structured records into Step 3 relational tables (clinical_events, medications, investigations, outstanding_items, evidence_references)
5. Enforces idempotency (safely replaces prior AI extractions for the document upon retry)
6. Manages ProcessingJob and Document lifecycle statuses (PROCESSING, COMPLETED, PARTIAL, FAILED)
7. Preserves source page citations and original wording for clinician auditability
"""

import io
import re
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any, Tuple
import pypdf
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.backend.db.models import (
    Document,
    DocumentPage,
    ProcessingJob,
    ClinicalEvent,
    Medication,
    Investigation,
    OutstandingItem,
    EvidenceReference,
    AuditEvent,
    generate_uuid,
    utc_now,
)
from src.backend.storage.document_storage import read_document_bytes
from src.backend.ai.gateway import AIGateway, get_ai_gateway
from src.backend.ai.extraction_schemas import (
    ExtractedClinicalDossier,
    ExtractedClinicalEvent,
    ExtractedCondition,
    ExtractedMedication,
    ExtractedInvestigation,
    ExtractedProcedure,
    ExtractedFollowUp,
)
from src.backend.ai.extraction_prompts import get_medical_extraction_template
from src.backend.ai.errors import (
    AIGatewayError,
    AIInvalidResponseError,
    AISchemaValidationError,
)
from src.backend.ai.logging import SafeAILogger


def parse_date_safely(date_str: Optional[str]) -> Tuple[Optional[datetime], str]:
    """
    Safely parse date string into datetime and precision.
    Never invents dates. If unparseable or relative, returns (None, 'APPROXIMATE'|'UNKNOWN').
    """
    if not date_str or not date_str.strip():
        return None, "UNKNOWN"

    clean = date_str.strip()

    # Match YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
        try:
            dt = datetime.strptime(clean, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt, "EXACT"
        except ValueError:
            pass

    # Match YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", clean):
        try:
            dt = datetime.strptime(f"{clean}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt, "MONTH_YEAR"
        except ValueError:
            pass

    # Match YYYY
    if re.match(r"^\d{4}$", clean):
        try:
            dt = datetime.strptime(f"{clean}-01-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt, "YEAR_ONLY"
        except ValueError:
            pass

    # Relative or descriptive date
    return None, "APPROXIMATE"


class ExtractionService:
    """Production service for page-aware medical entity extraction and database persistence."""

    def __init__(self, gateway: Optional[AIGateway] = None):
        self.gateway = gateway or get_ai_gateway()

    def ensure_document_pages(
        self, db: Session, document: Document, force_reextract: bool = False
    ) -> List[DocumentPage]:
        """
        Extract page text from stored PDF using pypdf and persist DocumentPage records.
        If pages contain no text (e.g. scanned image with no OCR), marked as PENDING without faking text.
        """
        existing_pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number.asc())
            .all()
        )
        if existing_pages and not force_reextract:
            return existing_pages

        if existing_pages and force_reextract:
            for ep in existing_pages:
                db.delete(ep)
            db.flush()

        # Read PDF binary from private storage
        pdf_bytes = read_document_bytes(document.storage_path)
        pages_to_create: List[DocumentPage] = []

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            document.page_count = total_pages

            for idx, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                clean_text = raw_text.strip()
                has_text = bool(clean_text)

                doc_page = DocumentPage(
                    id=generate_uuid(),
                    document_id=document.id,
                    page_number=idx,
                    extracted_text=clean_text if has_text else None,
                    ocr_applied=False,
                    processing_status="EXTRACTED" if has_text else "PENDING",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(doc_page)
                pages_to_create.append(doc_page)

            db.flush()
            return pages_to_create

        except Exception as e:
            # Fallback if PDF parsing fails
            fallback_page = DocumentPage(
                id=generate_uuid(),
                document_id=document.id,
                page_number=1,
                extracted_text=None,
                ocr_applied=False,
                processing_status="FAILED",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(fallback_page)
            db.flush()
            return [fallback_page]

    def _clear_previous_extractions(self, db: Session, document_id: str) -> None:
        """
        Idempotency guard: Clean previous AI-generated entities for this document
        to prevent duplicate clinical records upon re-processing or retries.
        """
        # Clear evidence references linked to this document
        db.query(EvidenceReference).filter(EvidenceReference.document_id == document_id).delete(synchronize_session=False)

        # Clear AI-generated clinical events for this document
        db.query(ClinicalEvent).filter(
            ClinicalEvent.source_document_id == document_id,
            ClinicalEvent.is_ai_generated == True,
        ).delete(synchronize_session=False)

        # Clear medications from this document
        db.query(Medication).filter(
            Medication.source_document_id == document_id,
        ).delete(synchronize_session=False)

        # Clear investigations from this document
        db.query(Investigation).filter(
            Investigation.source_document_id == document_id,
        ).delete(synchronize_session=False)

        # Clear AI-generated outstanding follow-up items from this document
        db.query(OutstandingItem).filter(
            OutstandingItem.source_document_id == document_id,
            OutstandingItem.is_ai_generated == True,
        ).delete(synchronize_session=False)

        db.flush()

    def process_document_extraction(
        self,
        db: Session,
        document: Document,
        user_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute full page-aware extraction pipeline on an authorized document.
        """
        # 1. Resolve or create active ProcessingJob
        job: Optional[ProcessingJob] = None
        if job_id:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            job = (
                db.query(ProcessingJob)
                .filter(ProcessingJob.document_id == document.id)
                .order_by(ProcessingJob.created_at.desc())
                .first()
            )
        if not job:
            job = ProcessingJob(
                id=generate_uuid(),
                document_id=document.id,
                job_type="AI_EXTRACTION",
                status="PROCESSING",
                progress=5,
                total_pages=document.page_count or 1,
                processed_pages=0,
                started_at=utc_now(),
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(job)
        else:
            job.status = "PROCESSING"
            job.started_at = utc_now()
            job.progress = 10
            job.updated_at = utc_now()

        document.status = "PROCESSING"
        document.updated_at = utc_now()
        db.flush()

        # 2. Extract or load pages
        pages = self.ensure_document_pages(db, document)
        job.total_pages = len(pages)
        db.flush()

        total_extracted = {
            "events": 0,
            "conditions": 0,
            "medications": 0,
            "investigations": 0,
            "procedures": 0,
            "follow_ups": 0,
        }

        # Check if usable document text exists
        pages_with_text = [p for p in pages if p.extracted_text and p.extracted_text.strip()]
        if not pages_with_text:
            error_msg = "Document text is not available yet. Please retry document processing."
            job.status = "FAILED"
            job.error_message = error_msg
            job.progress = 0
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            document.status = "FAILED"
            document.updated_at = utc_now()
            db.commit()
            return {
                "document_id": document.id,
                "patient_id": document.patient_id,
                "job_id": job.id,
                "status": "FAILED",
                "job_status": "FAILED",
                "processed_pages": 0,
                "total_pages": len(pages),
                "failed_pages": [p.page_number for p in pages],
                "extracted_counts": total_extracted,
                "error_message": error_msg,
            }

        # Check if Gemini AI Gateway is configured
        if not self.gateway.config.is_configured:
            error_msg = "Gemini API is not configured. GEMINI_API_KEY is missing."
            job.status = "FAILED"
            job.error_message = error_msg
            job.progress = 0
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            document.status = "FAILED"
            document.updated_at = utc_now()
            db.commit()
            return {
                "document_id": document.id,
                "patient_id": document.patient_id,
                "job_id": job.id,
                "status": "FAILED",
                "job_status": "FAILED",
                "processed_pages": 0,
                "total_pages": len(pages),
                "failed_pages": [p.page_number for p in pages],
                "extracted_counts": total_extracted,
                "error_message": error_msg,
            }

        # 3. Apply idempotency cleanup before inserting fresh run data
        self._clear_previous_extractions(db, document.id)

        template = get_medical_extraction_template()
        failed_pages: List[int] = []
        processed_count = 0
        last_error_message: Optional[str] = None

        # 4. Page-aware extraction loop
        for p in pages_with_text:
            page_context = (
                f"DOCUMENT: {document.file_name} (Type: {document.document_type})\n"
                f"PAGE NUMBER: {p.page_number} of {len(pages)}\n\n"
                f"--- CLINICAL TEXT START (PAGE {p.page_number}) ---\n"
                f"{p.extracted_text}\n"
                f"--- CLINICAL TEXT END ---"
            )

            prompt = template.render(context_input=page_context)

            try:
                dossier, _meta = self.gateway.generate_structured(
                    schema=ExtractedClinicalDossier,
                    prompt=prompt,
                    system_instruction=template.system_instruction,
                    user_id=user_id,
                    operation="medical_information_extraction",
                )

                # Persist extracted entities for this page
                self._persist_page_dossier(db, document, p, dossier, total_extracted)
                processed_count += 1
                p.processing_status = "EXTRACTED"
                p.updated_at = utc_now()

            except AIGatewayError as ai_err:
                failed_pages.append(p.page_number)
                p.processing_status = "FAILED"
                p.updated_at = utc_now()
                last_error_message = ai_err.message
                SafeAILogger.log_operation_failure(
                    request_id=f"doc_{document.id}_p_{p.page_number}",
                    operation="extract_page",
                    model=self.gateway.config.model,
                    error_category=ai_err.category,
                    error_message=ai_err.message,
                    latency_ms=0.0,
                )
            except Exception as page_err:
                failed_pages.append(p.page_number)
                p.processing_status = "FAILED"
                p.updated_at = utc_now()
                last_error_message = str(page_err)
                SafeAILogger.log_operation_failure(
                    request_id=f"doc_{document.id}_p_{p.page_number}",
                    operation="extract_page",
                    model=self.gateway.config.model,
                    error_category="EXTRACTION_PAGE_FAILURE",
                    error_message=str(page_err),
                    latency_ms=0.0,
                )

            # Update progress incrementally
            progress_pct = min(10 + int((processed_count / max(len(pages), 1)) * 85), 95)
            job.progress = progress_pct
            job.processed_pages = processed_count
            db.flush()

        # 5. Evaluate final status (Full Success, Partial, or Failed)
        if failed_pages and processed_count > 0:
            final_job_status = "PARTIAL"
            final_doc_status = "PARTIAL"
            job.error_message = f"Medical extraction completed with partial errors on page(s): {failed_pages} ({last_error_message or 'partial error'})."
        elif failed_pages and processed_count == 0:
            final_job_status = "FAILED"
            final_doc_status = "FAILED"
            job.error_message = last_error_message or f"All pages failed extraction: {failed_pages}"
        else:
            final_job_status = "COMPLETED"
            final_doc_status = "PROCESSED"
            job.error_message = None

        job.status = final_job_status
        job.progress = 100
        job.processed_pages = processed_count
        job.completed_at = utc_now()
        job.updated_at = utc_now()

        document.status = final_doc_status
        document.updated_at = utc_now()

        # Audit Event Logging
        audit = AuditEvent(
            id=generate_uuid(),
            user_id=user_id,
            action="CLINICAL_EXTRACTION",
            resource_type="DOCUMENT",
            resource_id=document.id,
            metadata_json=f'{{"status":"{final_job_status}","extracted_counts":{total_extracted},"pages_processed":{processed_count}}}',
            created_at=utc_now(),
        )
        db.add(audit)
        db.commit()

        return {
            "document_id": document.id,
            "patient_id": document.patient_id,
            "job_id": job.id,
            "status": final_doc_status,
            "job_status": final_job_status,
            "processed_pages": processed_count,
            "total_pages": len(pages),
            "failed_pages": failed_pages,
            "extracted_counts": total_extracted,
            "error_message": job.error_message,
        }

    def _persist_page_dossier(
        self,
        db: Session,
        document: Document,
        page: DocumentPage,
        dossier: ExtractedClinicalDossier,
        counts: Dict[str, int],
    ) -> None:
        """Persist structured items and create EvidenceReferences linked to page and document."""
        patient_id = document.patient_id

        # 1. Clinical Events
        for ev in dossier.events:
            dt, precision = parse_date_safely(ev.event_date)
            # If user prompt has explicit precision override, honor it
            if ev.date_precision != "EXACT":
                precision = ev.date_precision

            event_record = ClinicalEvent(
                id=generate_uuid(),
                patient_id=patient_id,
                event_type=ev.event_type,
                event_date=dt,
                event_date_precision=precision,
                title=ev.title,
                description=ev.description,
                source_document_id=document.id,
                source_page_id=page.id,
                confidence=ev.confidence,
                is_ai_generated=True,
                is_conflict=ev.is_uncertain,
                conflict_details=ev.uncertainty_note,
                review_status="UNREVIEWED",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(event_record)
            counts["events"] += 1

            if ev.source_snippet:
                ref = EvidenceReference(
                    id=generate_uuid(),
                    patient_id=patient_id,
                    document_id=document.id,
                    document_page_id=page.id,
                    parent_entity_type="CLINICAL_EVENT",
                    parent_entity_id=event_record.id,
                    source_section=ev.department or "Clinical Events",
                    source_text=ev.source_snippet,
                    source_type="PDF_TEXT",
                    confidence=ev.confidence,
                    created_at=utc_now(),
                )
                db.add(ref)

        # 2. Conditions (Recorded as clinical events of type 'diagnosis' or 'other')
        for cond in dossier.conditions:
            dt, precision = parse_date_safely(cond.onset_date)
            status_prefix = ""
            if cond.is_negated:
                status_prefix = "[Ruled Out / Denied] "
            elif cond.clinical_status in ("suspected", "possible"):
                status_prefix = f"[{cond.clinical_status.capitalize()}] "

            cond_title = f"{status_prefix}{cond.condition_name}"
            cond_desc = f"Original text: {cond.original_text}"
            if cond.uncertainty_note:
                cond_desc += f" (Note: {cond.uncertainty_note})"

            cond_record = ClinicalEvent(
                id=generate_uuid(),
                patient_id=patient_id,
                event_type="diagnosis",
                event_date=dt,
                event_date_precision=precision,
                title=cond_title,
                description=cond_desc,
                source_document_id=document.id,
                source_page_id=page.id,
                confidence=cond.confidence,
                is_ai_generated=True,
                is_conflict=cond.is_uncertain,
                conflict_details=cond.uncertainty_note,
                review_status="UNREVIEWED",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(cond_record)
            counts["conditions"] += 1

            if cond.source_snippet:
                ref = EvidenceReference(
                    id=generate_uuid(),
                    patient_id=patient_id,
                    document_id=document.id,
                    document_page_id=page.id,
                    parent_entity_type="CLINICAL_EVENT",
                    parent_entity_id=cond_record.id,
                    source_section="Conditions / Problem List",
                    source_text=cond.source_snippet,
                    source_type="PDF_TEXT",
                    confidence=cond.confidence,
                    created_at=utc_now(),
                )
                db.add(ref)

        # 3. Medications
        for med in dossier.medications:
            start_dt, _ = parse_date_safely(med.start_date)
            stop_dt, _ = parse_date_safely(med.stop_date)

            med_record = Medication(
                id=generate_uuid(),
                patient_id=patient_id,
                medication_name=med.medication_name,
                generic_name=med.medication_name,
                dosage=med.dosage,
                dose_unit=med.dose_unit,
                route=med.route,
                frequency=med.frequency,
                status=med.status,
                start_date=start_dt.date() if start_dt else None,
                end_date=stop_dt.date() if stop_dt else None,
                source_document_id=document.id,
                source_page_id=page.id,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(med_record)
            counts["medications"] += 1

            if med.source_snippet:
                ref = EvidenceReference(
                    id=generate_uuid(),
                    patient_id=patient_id,
                    document_id=document.id,
                    document_page_id=page.id,
                    parent_entity_type="MEDICATION",
                    parent_entity_id=med_record.id,
                    source_section="Prescriptions / Medications",
                    source_text=med.source_snippet,
                    source_type="PDF_TEXT",
                    confidence=med.confidence,
                    created_at=utc_now(),
                )
                db.add(ref)

        # 4. Investigations
        for inv in dossier.investigations:
            ord_dt, _ = parse_date_safely(inv.ordered_date)
            comp_dt, _ = parse_date_safely(inv.result_date or inv.performed_date)

            inv_record = Investigation(
                id=generate_uuid(),
                patient_id=patient_id,
                investigation_name=inv.investigation_name,
                investigation_type=inv.investigation_type,
                ordered_date=ord_dt.date() if ord_dt else None,
                completed_date=comp_dt.date() if comp_dt else None,
                status=inv.status,
                result_summary=inv.result_text,
                reference_range=inv.reference_range,
                is_abnormal=inv.is_abnormal,
                clinical_urgency=inv.clinical_urgency,
                source_document_id=document.id,
                source_page_id=page.id,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(inv_record)
            counts["investigations"] += 1

            if inv.source_snippet:
                ref = EvidenceReference(
                    id=generate_uuid(),
                    patient_id=patient_id,
                    document_id=document.id,
                    document_page_id=page.id,
                    parent_entity_type="INVESTIGATION",
                    parent_entity_id=inv_record.id,
                    source_section="Diagnostic Reports",
                    source_text=inv.source_snippet,
                    source_type="PDF_TEXT",
                    confidence=inv.confidence,
                    created_at=utc_now(),
                )
                db.add(ref)

        # 5. Procedures
        for proc in dossier.procedures:
            proc_dt, precision = parse_date_safely(proc.procedure_date)
            proc_record = ClinicalEvent(
                id=generate_uuid(),
                patient_id=patient_id,
                event_type="procedure",
                event_date=proc_dt,
                event_date_precision=precision,
                title=f"Procedure: {proc.procedure_name}",
                description=proc.outcome or proc.indication or proc.procedure_name,
                source_document_id=document.id,
                source_page_id=page.id,
                confidence=proc.confidence,
                is_ai_generated=True,
                is_conflict=proc.is_uncertain,
                review_status="UNREVIEWED",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(proc_record)
            counts["procedures"] += 1

            if proc.source_snippet:
                ref = EvidenceReference(
                    id=generate_uuid(),
                    patient_id=patient_id,
                    document_id=document.id,
                    document_page_id=page.id,
                    parent_entity_type="CLINICAL_EVENT",
                    parent_entity_id=proc_record.id,
                    source_section="Procedures",
                    source_text=proc.source_snippet,
                    source_type="PDF_TEXT",
                    confidence=proc.confidence,
                    created_at=utc_now(),
                )
                db.add(ref)

        # 6. Follow-up Instructions
        for fu in dossier.follow_ups:
            due_dt, _ = parse_date_safely(fu.target_date)
            fu_record = OutstandingItem(
                id=generate_uuid(),
                patient_id=patient_id,
                item_type="FOLLOW_UP",
                title=fu.instruction,
                description=f"Specialty/Provider: {fu.specialty_or_provider or 'Not specified'}. Target: {fu.target_date or 'As directed'}",
                priority="NORMAL",
                status="OPEN",
                due_date=due_dt.date() if due_dt else None,
                source_document_id=document.id,
                source_page_id=page.id,
                is_ai_generated=True,
                review_status="UNREVIEWED",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(fu_record)
            counts["follow_ups"] += 1

            if fu.source_snippet:
                ref = EvidenceReference(
                    id=generate_uuid(),
                    patient_id=patient_id,
                    document_id=document.id,
                    document_page_id=page.id,
                    parent_entity_type="OUTSTANDING_ITEM",
                    parent_entity_id=fu_record.id,
                    source_section="Follow-up Instructions",
                    source_text=fu.source_snippet,
                    source_type="PDF_TEXT",
                    confidence=fu.confidence,
                    created_at=utc_now(),
                )
                db.add(ref)

        db.flush()


# Global service singleton
extraction_service = ExtractionService()


def get_extraction_service() -> ExtractionService:
    """Dependency provider for FastAPI route injection."""
    return extraction_service
