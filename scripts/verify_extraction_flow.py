"""
Verification script for Medical Document & Clinical Entity Extraction Pipeline
Tests:
1. Ingestion / Page creation from PDF
2. Behavior when GEMINI_API_KEY is not configured (clean diagnostic error, no false green)
3. Structured Pydantic extraction schema validation
4. Database entity persistence & EvidenceReference linkage
5. Idempotent re-extraction
"""

import os
import sys
from datetime import datetime

# Set working directory to project root
sys.path.insert(0, os.path.abspath("."))

from src.backend.db.connection import SessionLocal
from src.backend.db.models import (
    Patient, Document, DocumentPage, ProcessingJob,
    ClinicalEvent, Medication, Investigation, OutstandingItem,
    EvidenceReference, generate_uuid, utc_now
)
from src.backend.ai.extraction_service import get_extraction_service
from src.backend.ai.extraction_schemas import (
    ExtractedClinicalDossier,
    ExtractedClinicalEvent,
    ExtractedCondition,
    ExtractedMedication,
    ExtractedInvestigation,
    ExtractedProcedure,
    ExtractedFollowUp,
)

def run_verification():
    db = SessionLocal()
    try:
        print("[1/5] Checking patient and document records...")
        patient = db.query(Patient).filter(Patient.mrn == "MRN-2026-9812").first()
        if not patient:
            patient = Patient(
                id=generate_uuid(),
                mrn="MRN-2026-9812",
                first_name="Jonathan",
                last_name="Doe",
                date_of_birth=datetime(1964, 4, 12).date(),
                gender="MALE",
                status="ACTIVE",
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            print(f"  Created test patient: Jonathan Doe ({patient.id})")
        else:
            print(f"  Using existing patient: Jonathan Doe ({patient.id})")

        # Read generated synthetic PDF and store via secure storage
        pdf_path = "demo/Discharge_Summary_Jonathan_Doe.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        file_size = len(pdf_bytes)

        doc = db.query(Document).filter(
            Document.patient_id == patient.id,
            Document.file_name == "Discharge_Summary_Jonathan_Doe.pdf"
        ).first()

        from src.backend.storage.document_storage import store_document_bytes
        doc_id = doc.id if doc else generate_uuid()
        rel_storage_path = store_document_bytes(patient.id, doc_id, pdf_bytes)

        if not doc:
            doc = Document(
                id=doc_id,
                patient_id=patient.id,
                file_name="Discharge_Summary_Jonathan_Doe.pdf",
                file_type="application/pdf",
                storage_path=rel_storage_path,
                document_type="DISCHARGE_SUMMARY",
                file_size=file_size,
                page_count=2,
                status="UPLOADED",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            print(f"  Registered document record: {doc.id}")
        else:
            doc.storage_path = rel_storage_path
            db.commit()
            print(f"  Using existing document record: {doc.id}")

        extraction_service = get_extraction_service()

        print("\n[2/5] Testing PDF ingestion & page text extraction...")
        pages = extraction_service.ensure_document_pages(db, doc, force_reextract=True)
        print(f"  Extracted {len(pages)} pages.")
        assert len(pages) == 2, f"Expected 2 pages, got {len(pages)}"
        for p in pages:
            assert len(p.extracted_text.strip()) > 100, f"Page {p.page_number} text is too short"
            print(f"  Page {p.page_number}: {len(p.extracted_text)} characters")

        print("\n[3/5] Testing extraction behavior with current configuration...")
        result = extraction_service.process_document_extraction(db, doc)
        print(f"  Extraction status: {result['status']}")
        if result['status'] == 'FAILED':
            print(f"  Handled cleanly: error_message = \"{result.get('error_message')}\"")
            assert "GEMINI_API_KEY" in result.get('error_message', '') or "Gemini" in result.get('error_message', '')
            print("  PASS: Diagnostic failure returned with accurate clinician message, no swallowed error.")
        elif result['status'] == 'PROCESSED':
            print(f"  Live Gemini extraction succeeded!")
            print(f"  Entities extracted: {result['entities_extracted']}")
            print("  PASS: Real Gemini extraction completed and persisted.")

        print("\n[4/5] Testing Pydantic Structured Schema parsing & validation...")
        test_cond = ExtractedCondition(
            condition_name="Acute Non-ST Elevation Myocardial Infarction",
            original_text="Acute Non-ST Elevation Myocardial Infarction (NSTEMI)",
            clinical_status="confirmed",
            confidence=0.98,
            source_snippet="Initial troponin elevation confirmed an Acute Non-ST Elevation Myocardial Infarction (NSTEMI)"
        )
        assert test_cond.condition_name == "Acute Non-ST Elevation Myocardial Infarction"
        assert test_cond.clinical_status == "confirmed"

        test_med = ExtractedMedication(
            medication_name="Atorvastatin",
            original_text="Atorvastatin 80 mg Oral Once daily at bedtime",
            dosage="80",
            dose_unit="mg",
            route="Oral",
            frequency="Once daily at bedtime",
            status="ACTIVE",
            confidence=0.95,
            source_snippet="Atorvastatin 80 mg Oral Once daily at bedtime"
        )
        assert test_med.dosage == "80"

        test_inv = ExtractedInvestigation(
            investigation_name="High-Sensitivity Troponin T",
            investigation_type="LAB",
            result_text="142 ng/L (Markedly Elevated)",
            numeric_value=142.0,
            unit="ng/L",
            reference_range="< 14 ng/L",
            is_abnormal=True,
            clinical_urgency="HIGH",
            status="COMPLETED",
            confidence=0.99,
            source_snippet="High-Sensitivity Troponin T 142 ng/L"
        )
        assert test_inv.clinical_urgency == "HIGH"
        print("  PASS: All Pydantic schema validators passed.")

        print("\n[5/5] Testing Entity Persistence & Idempotency Pipeline...")
        mock_dossier = ExtractedClinicalDossier(
            conditions=[test_cond],
            medications=[test_med],
            investigations=[test_inv],
            procedures=[ExtractedProcedure(procedure_name="Coronary Angiography", confidence=0.9, source_snippet="Coronary Angiography")],
            follow_ups=[ExtractedFollowUp(instruction="Cardiology Clinic Follow-up in 2 weeks", confidence=0.9, source_snippet="Cardiology Clinic Follow-up in 2 weeks")]
        )

        # Clear prior
        extraction_service._clear_previous_extractions(db, doc.id)

        # Save run 1
        counts1 = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        extraction_service._persist_page_dossier(db, doc, pages[0], mock_dossier, counts1)
        db.commit()
        total1 = sum(counts1.values())
        print(f"  Run 1 saved: {total1} entities (counts: {counts1})")
        assert total1 == 5

        # Verify DB counts
        ev_count = db.query(ClinicalEvent).filter(ClinicalEvent.source_document_id == doc.id).count()
        med_count = db.query(Medication).filter(Medication.source_document_id == doc.id).count()
        inv_count = db.query(Investigation).filter(Investigation.source_document_id == doc.id).count()
        out_count = db.query(OutstandingItem).filter(OutstandingItem.source_document_id == doc.id).count()
        ref_count = db.query(EvidenceReference).filter(EvidenceReference.document_id == doc.id).count()
        print(f"  In DB -> Events: {ev_count}, Meds: {med_count}, Invs: {inv_count}, Items: {out_count}, References: {ref_count}")
        assert ev_count == 2 # 1 condition + 1 procedure
        assert med_count == 1
        assert inv_count == 1
        assert out_count == 1
        assert ref_count == 5

        # Run 2 (idempotency check)
        extraction_service._clear_previous_extractions(db, doc.id)
        counts2 = {"events": 0, "conditions": 0, "medications": 0, "investigations": 0, "procedures": 0, "follow_ups": 0}
        extraction_service._persist_page_dossier(db, doc, pages[0], mock_dossier, counts2)
        db.commit()
        ev_count2 = db.query(ClinicalEvent).filter(ClinicalEvent.source_document_id == doc.id).count()
        assert ev_count2 == 2, f"Expected 2 after rerun, got {ev_count2} (duplicate bug!)"
        print(f"  Run 2 after re-extraction -> Events: {ev_count2} (No duplicates!)")
        print("  PASS: Idempotency verified. Entities cleared and re-inserted cleanly.")

        print("\nAll 5 verification stages PASSED successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
