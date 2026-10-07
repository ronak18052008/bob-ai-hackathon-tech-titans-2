-- =============================================================================
-- MedBrief AI — Seed Demo/Test Data Migration
-- Version: 002
-- Phase: Step 3 — Database Foundation
-- Description: Strictly fictional demo medical records for development and testing.
--              NO real patient health information (PHI) is present.
-- =============================================================================

-- Deterministic UUIDs for demo records
DO $$
DECLARE
    role_doc_id UUID := '00000000-0000-4000-8000-000000000001';
    role_admin_id UUID := '00000000-0000-4000-8000-000000000002';
    demo_user_id UUID := '11111111-1111-4000-8000-111111111111';
    demo_admin_user_id UUID := '00000000-0000-4000-8000-000000000099';
    demo_patient_id UUID := '22222222-2222-4000-8000-222222222222';
    demo_doc_id UUID := '33333333-3333-4000-8000-333333333333';
    demo_page1_id UUID := '44444444-4444-4000-8000-444444444441';
    demo_page2_id UUID := '44444444-4444-4000-8000-444444444442';
    demo_job_id UUID := '55555555-5555-4000-8000-555555555555';
    demo_event1_id UUID := '66666666-6666-4000-8000-666666666661';
    demo_event2_id UUID := '66666666-6666-4000-8000-666666666662';
    demo_med1_id UUID := '77777777-7777-4000-8000-777777777771';
    demo_med2_id UUID := '77777777-7777-4000-8000-777777777772';
    demo_med_change_id UUID := '88888888-8888-4000-8000-888888888888';
    demo_inv1_id UUID := '99999999-9999-4000-8000-999999999991';
    demo_inv2_id UUID := '99999999-9999-4000-8000-999999999992';
    demo_item_id UUID := 'aaaaaaaa-aaaa-4000-8000-aaaaaaaaaaaa';
    demo_summary_id UUID := 'bbbbbbbb-bbbb-4000-8000-bbbbbbbbbbbb';
    demo_ev1_id UUID := 'cccccccc-cccc-4000-8000-cccccccccccc';
    demo_draft_id UUID := 'dddddddd-dddd-4000-8000-dddddddddddd';
    demo_audit_id UUID := 'eeeeeeee-eeee-4000-8000-eeeeeeeeeeee';
BEGIN
    -- 1. Roles
    INSERT INTO roles (id, name, description)
    VALUES 
        (role_doc_id, 'doctor', 'Licensed clinical physician with patient management and sign-off authority'),
        (role_admin_id, 'admin', 'System administrator with audit and user management privileges')
    ON CONFLICT (id) DO NOTHING;

    -- 2. Demo Physician User
    INSERT INTO users (id, email, display_name, role_title, medical_license_id, is_active)
    VALUES 
        (demo_user_id, 'dr.sarah.chen@demo-clinic.test', 'Dr. Sarah Chen, MD', 'Attending Physician', 'MED-LIC-98421', TRUE)
    ON CONFLICT (id) DO NOTHING;

    -- 2b. Demo Systems Admin User
    INSERT INTO users (id, email, display_name, role_title, is_active)
    VALUES 
        (demo_admin_user_id, 'admin@demo-clinic.test', 'Alex Rivera', 'Lead Systems Administrator', TRUE)
    ON CONFLICT (id) DO NOTHING;

    -- 3. Assign Roles
    INSERT INTO user_roles (user_id, role_id)
    VALUES 
        (demo_user_id, role_doc_id),
        (demo_admin_user_id, role_admin_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;

    -- 4. Demo Patient (Strictly Synthetic)
    INSERT INTO patients (id, mrn, first_name, last_name, date_of_birth, gender, contact_phone, status, created_by)
    VALUES 
        (demo_patient_id, 'DEMO-MRN-2026-0042', 'Johnathan', 'Doe', '1968-05-14', 'Male', '+1-555-0199', 'ACTIVE', demo_user_id)
    ON CONFLICT (id) DO NOTHING;

    -- 5. Clinician Access
    INSERT INTO patient_user_access (patient_id, user_id, access_role)
    VALUES (demo_patient_id, demo_user_id, 'PRIMARY_PHYSICIAN')
    ON CONFLICT (patient_id, user_id) DO NOTHING;

    -- 6. Demo Document
    INSERT INTO documents (id, patient_id, uploaded_by, file_name, file_type, storage_path, document_type, file_size, page_count, status)
    VALUES 
        (demo_doc_id, demo_patient_id, demo_user_id, 'Discharge_Summary_CityGeneral_20260210.pdf', 'application/pdf', '/demo/docs/demo_discharge_summary.pdf', 'DISCHARGE_SUMMARY', 148200, 2, 'PROCESSED')
    ON CONFLICT (id) DO NOTHING;

    -- 7. Document Pages
    INSERT INTO document_pages (id, document_id, page_number, extracted_text, ocr_applied, processing_status)
    VALUES 
        (demo_page1_id, demo_doc_id, 1, 'City General Hospital. Patient: Johnathan Doe, DOB: 14/05/1968. Admitted with acute coronary syndrome. Diagnosed with NSTEMI.', FALSE, 'EXTRACTED'),
        (demo_page2_id, demo_doc_id, 2, 'Discharge medications: Atorvastatin increased to 40mg OD. Metformin 500mg BD continued. Plan: Outpatient transthoracic echocardiogram in 4 weeks.', FALSE, 'EXTRACTED')
    ON CONFLICT (id) DO NOTHING;

    -- 8. Processing Job
    INSERT INTO processing_jobs (id, document_id, job_type, status, progress, total_pages, processed_pages, retry_count)
    VALUES 
        (demo_job_id, demo_doc_id, 'FULL_DOCUMENT_PROCESSING', 'COMPLETED', 100, 2, 2, 0)
    ON CONFLICT (id) DO NOTHING;

    -- 9. Clinical Events
    INSERT INTO clinical_events (id, patient_id, event_type, event_date, event_date_precision, title, description, source_document_id, source_page_id, confidence, is_ai_generated, review_status)
    VALUES 
        (demo_event1_id, demo_patient_id, 'ADMISSION', '2026-02-05 08:30:00+00', 'EXACT', 'Hospital Admission for NSTEMI', 'Patient admitted with acute substernal chest discomfort. Troponin I elevated at 0.42 ng/mL.', demo_doc_id, demo_page1_id, 0.98, TRUE, 'VERIFIED'),
        (demo_event2_id, demo_patient_id, 'DISCHARGE', '2026-02-10 14:00:00+00', 'EXACT', 'Hospital Discharge', 'Hemodynamically stable discharge on dual antiplatelet and high-intensity statin therapy.', demo_doc_id, demo_page2_id, 0.99, TRUE, 'VERIFIED')
    ON CONFLICT (id) DO NOTHING;

    -- 10. Medications
    INSERT INTO medications (id, patient_id, medication_name, generic_name, dosage, dose_unit, route, frequency, status, start_date, source_document_id, source_page_id)
    VALUES 
        (demo_med1_id, demo_patient_id, 'Lipitor', 'Atorvastatin', '40', 'mg', 'Oral', 'Once daily at bedtime', 'ACTIVE', '2026-02-09', demo_doc_id, demo_page2_id),
        (demo_med2_id, demo_patient_id, 'Glucophage', 'Metformin', '500', 'mg', 'Oral', 'Twice daily with meals', 'ACTIVE', '2020-03-12', demo_doc_id, demo_page2_id)
    ON CONFLICT (id) DO NOTHING;

    -- 11. Medication Changes
    INSERT INTO medication_changes (id, medication_id, change_type, previous_value, new_value, change_date, reason, source_document_id, source_page_id, is_ai_generated, review_status)
    VALUES 
        (demo_med_change_id, demo_med1_id, 'DOSE_CHANGED', '20mg OD', '40mg OD', '2026-02-09', 'Up-titration to high-intensity statin therapy post-NSTEMI', demo_doc_id, demo_page2_id, TRUE, 'VERIFIED')
    ON CONFLICT (id) DO NOTHING;

    -- 12. Investigations
    INSERT INTO investigations (id, patient_id, investigation_name, investigation_type, completed_date, status, result_summary, reference_range, is_abnormal, clinical_urgency, source_document_id, source_page_id)
    VALUES 
        (demo_inv1_id, demo_patient_id, 'Troponin I', 'LAB', '2026-02-05', 'COMPLETED', '0.42 ng/mL', '< 0.04 ng/mL', TRUE, 'HIGH', demo_doc_id, demo_page1_id),
        (demo_inv2_id, demo_patient_id, 'Transthoracic Echocardiogram', 'IMAGING', NULL, 'ORDERED', 'Pending outpatient appointment', 'N/A', NULL, 'HIGH', demo_doc_id, demo_page2_id)
    ON CONFLICT (id) DO NOTHING;

    -- 13. Outstanding Items
    INSERT INTO outstanding_items (id, patient_id, item_type, title, description, priority, status, due_date, source_document_id, source_page_id, is_ai_generated, review_status)
    VALUES 
        (demo_item_id, demo_patient_id, 'PENDING_INVESTIGATION', 'Follow-up Transthoracic Echocardiogram', 'Outpatient TTE ordered at discharge to assess post-infarct left ventricular ejection fraction.', 'HIGH', 'OPEN', '2026-03-10', demo_doc_id, demo_page2_id, TRUE, 'VERIFIED')
    ON CONFLICT (id) DO NOTHING;

    -- 14. Summaries
    INSERT INTO summaries (id, patient_id, summary_type, title, content, status, generated_by, is_ai_generated, model_name, model_version)
    VALUES 
        (demo_summary_id, demo_patient_id, 'QUICK_CLINICAL', 'Clinical Brief — Post-NSTEMI Admission', '57M admitted Feb 2026 with NSTEMI. Successfully stabilized. Statin dose increased to Atorvastatin 40mg OD. Outstanding outpatient echocardiogram required.', 'DRAFT', demo_user_id, TRUE, 'gemini-1.5-flash', '002')
    ON CONFLICT (id) DO NOTHING;

    -- 15. Evidence References
    INSERT INTO evidence_references (id, patient_id, document_id, document_page_id, parent_entity_type, parent_entity_id, source_section, source_text, source_type, confidence)
    VALUES 
        (demo_ev1_id, demo_patient_id, demo_doc_id, demo_page2_id, 'MEDICATION_CHANGE', demo_med_change_id, 'Discharge Medications', 'Atorvastatin increased to 40mg OD.', 'PDF_TEXT', 0.99)
    ON CONFLICT (id) DO NOTHING;

    -- 16. Drafts
    INSERT INTO drafts (id, patient_id, draft_type, title, content, status, created_by, generated_by_ai, model_name, model_version)
    VALUES 
        (demo_draft_id, demo_patient_id, 'REFERRAL', 'Referral to Cardiology Outpatient Service', 'Dear Colleague, Thank you for seeing Mr. Johnathan Doe (DOB 14/05/1968) for post-NSTEMI review and echocardiogram assessment.', 'DRAFT', demo_user_id, TRUE, 'gemini-1.5-pro', '002')
    ON CONFLICT (id) DO NOTHING;

    -- 17. Audit Events
    INSERT INTO audit_events (id, user_id, action, resource_type, resource_id, metadata_json)
    VALUES 
        (demo_audit_id, demo_user_id, 'PATIENT_VIEW', 'PATIENT', demo_patient_id::text, '{"ip": "127.0.0.1", "interface": "desktop_dashboard"}')
    ON CONFLICT (id) DO NOTHING;

END $$;
