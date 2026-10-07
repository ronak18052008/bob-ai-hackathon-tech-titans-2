"""
MedBrief AI — Database Initialization & Migration Helper
Step 3: Database Foundation

Applies table schemas to the configured database and optionally inserts
fictional demo/test records.
"""

import sys
import uuid
from datetime import datetime, date
from src.backend.db.connection import engine, SessionLocal, Base
from src.backend.db.models import (
    Role,
    User,
    UserRole,
    Patient,
    PatientUserAccess,
    Document,
    DocumentPage,
    ProcessingJob,
    ClinicalEvent,
    Medication,
    MedicationChange,
    Investigation,
    OutstandingItem,
    Summary,
    EvidenceReference,
    Draft,
    AuditEvent,
    UserPreference,
)


from sqlalchemy import inspect, text

def init_database():
    """Create all tables in the database."""
    print("Creating MedBrief AI database tables...")
    Base.metadata.create_all(bind=engine)
    print(f"Successfully verified/created {len(Base.metadata.tables)} tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  [OK] {table_name}")

    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            if "users" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("users")]
                if "password_hash" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                    conn.commit()
                    print("  [OK] Added password_hash column to users table.")
    except Exception as e:
        print(f"  [INFO] Column migration notice: {e}")



def _seed_additional_patients(db, doc_id: str):
    """Seed additional synthetic demo patients for caseload search, filtering, and authorization testing."""
    additional_patients = [
        {
            "id": "22222222-2222-4000-8000-222222222223",
            "mrn": "DEMO-MRN-2026-0087",
            "first_name": "Eleanor",
            "last_name": "Vance",
            "date_of_birth": date(1952, 11, 20),
            "gender": "Female",
            "contact_phone": "+1-555-0143",
            "status": "ACTIVE",
            "created_by": doc_id,
            "access_role": "PRIMARY_PHYSICIAN",
            "has_doc": True,
            "doc_id": "33333333-3333-4000-8000-333333333334",
            "doc_title": "Cardiology_Consultation_20260214.pdf",
        },
        {
            "id": "22222222-2222-4000-8000-222222222224",
            "mrn": "DEMO-MRN-2026-0105",
            "first_name": "Marcus",
            "last_name": "Bennett",
            "date_of_birth": date(1984, 3, 8),
            "gender": "Male",
            "contact_phone": "+1-555-0178",
            "status": "ACTIVE",
            "created_by": doc_id,
            "access_role": "PRIMARY_PHYSICIAN",
            "has_doc": False,
        },
        {
            "id": "22222222-2222-4000-8000-222222222225",
            "mrn": "DEMO-MRN-2026-0211",
            "first_name": "Sarah",
            "last_name": "Jenkins",
            "date_of_birth": date(1976, 9, 17),
            "gender": "Female",
            "contact_phone": "+1-555-0122",
            "status": "INACTIVE",
            "created_by": doc_id,
            "access_role": "CONSULTANT",
            "has_doc": False,
        },
        {
            "id": "22222222-2222-4000-8000-222222222299",
            "mrn": "DEMO-MRN-2026-0999",
            "first_name": "Arthur",
            "last_name": "Pendelton",
            "date_of_birth": date(1945, 7, 4),
            "gender": "Male",
            "contact_phone": "+1-555-0188",
            "status": "ACTIVE",
            "created_by": None,
            "access_role": None,  # Unassigned - tests 403 authorization rejection
            "has_doc": False,
        },
    ]

    for p_data in additional_patients:
        existing = db.query(Patient).filter(Patient.mrn == p_data["mrn"]).first()
        if not existing:
            p = Patient(
                id=p_data["id"],
                mrn=p_data["mrn"],
                first_name=p_data["first_name"],
                last_name=p_data["last_name"],
                date_of_birth=p_data["date_of_birth"],
                gender=p_data["gender"],
                contact_phone=p_data["contact_phone"],
                status=p_data["status"],
                created_by=p_data["created_by"],
            )
            db.add(p)
            db.flush()

            if p_data["access_role"] and doc_id:
                acc = PatientUserAccess(
                    id=str(uuid.uuid4()),
                    patient_id=p.id,
                    user_id=doc_id,
                    access_role=p_data["access_role"],
                )
                db.add(acc)

            if p_data.get("has_doc"):
                doc = Document(
                    id=p_data["doc_id"],
                    patient_id=p.id,
                    uploaded_by=doc_id,
                    file_name=p_data["doc_title"],
                    file_type="application/pdf",
                    storage_path=f"/demo/docs/{p_data['doc_title']}",
                    document_type="CLINIC_CONSULTATION",
                    file_size=98400,
                    page_count=1,
                    status="PROCESSED",
                )
                db.add(doc)
    db.commit()


def seed_demo_data():
    """Insert strictly fictional demo medical data for development verification."""
    print("\nSeeding fictional DEMO/TEST data...")
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_doc = db.query(User).filter_by(email="dr.sarah.chen@demo-clinic.test").first()
        existing_admin = db.query(User).filter_by(email="admin@demo-clinic.test").first()

        if existing_doc and existing_admin:
            print("Database contains Doctor and Admin. Checking/seeding additional caseload patients...")
            _seed_additional_patients(db, existing_doc.id)
            return

        # If admin is missing but doctor exists, insert admin
        if existing_doc and not existing_admin:
            role_admin = db.query(Role).filter_by(name="admin").first()
            if not role_admin:
                role_admin = Role(
                    id="00000000-0000-4000-8000-000000000002",
                    name="admin",
                    description="System administrator with audit and user management privileges",
                )
                db.add(role_admin)
                db.flush()
            admin_user = User(
                id="00000000-0000-4000-8000-000000000099",
                email="admin@demo-clinic.test",
                display_name="Alex Rivera",
                role_title="Lead Systems Administrator",
                is_active=True,
            )
            db.add(admin_user)
            db.flush()
            db.add(UserRole(user_id=admin_user.id, role_id=role_admin.id))
            db.commit()
            print("[OK] Seeded demo Admin account.")
            return

        # 1. Roles
        role_doctor = Role(
            id="00000000-0000-4000-8000-000000000001",
            name="doctor",
            description="Licensed clinical physician with patient management and sign-off authority",
        )
        role_admin = Role(
            id="00000000-0000-4000-8000-000000000002",
            name="admin",
            description="System administrator with audit and user management privileges",
        )
        db.add_all([role_doctor, role_admin])

        # 2. Demo User (Doctor)
        demo_user = User(
            id="11111111-1111-4000-8000-111111111111",
            email="dr.sarah.chen@demo-clinic.test",
            display_name="Dr. Sarah Chen, MD",
            role_title="Attending Physician",
            medical_license_id="MED-LIC-98421",
            is_active=True,
        )
        # 2b. Demo User (Admin)
        admin_user = User(
            id="00000000-0000-4000-8000-000000000099",
            email="admin@demo-clinic.test",
            display_name="Alex Rivera",
            role_title="Lead Systems Administrator",
            is_active=True,
        )
        db.add_all([demo_user, admin_user])

        # 3. User Roles
        user_role_doc = UserRole(
            user_id=demo_user.id,
            role_id=role_doctor.id,
        )
        user_role_admin = UserRole(
            user_id=admin_user.id,
            role_id=role_admin.id,
        )
        db.add_all([user_role_doc, user_role_admin])

        # 4. Demo Patient (Strictly Synthetic)
        demo_patient = Patient(
            id="22222222-2222-4000-8000-222222222222",
            mrn="DEMO-MRN-2026-0042",
            first_name="Johnathan",
            last_name="Doe",
            date_of_birth=date(1968, 5, 14),
            gender="Male",
            contact_phone="+1-555-0199",
            status="ACTIVE",
            created_by=demo_user.id,
        )
        db.add(demo_patient)

        # 5. Patient User Access
        access = PatientUserAccess(
            patient_id=demo_patient.id,
            user_id=demo_user.id,
            access_role="PRIMARY_PHYSICIAN",
        )
        db.add(access)

        # 6. Demo Document
        demo_doc = Document(
            id="33333333-3333-4000-8000-333333333333",
            patient_id=demo_patient.id,
            uploaded_by=demo_user.id,
            file_name="Discharge_Summary_CityGeneral_20260210.pdf",
            file_type="application/pdf",
            storage_path="/demo/docs/demo_discharge_summary.pdf",
            document_type="DISCHARGE_SUMMARY",
            file_size=148200,
            page_count=2,
            status="PROCESSED",
        )
        db.add(demo_doc)

        # 7. Document Pages
        page1 = DocumentPage(
            id="44444444-4444-4000-8000-444444444441",
            document_id=demo_doc.id,
            page_number=1,
            extracted_text="City General Hospital. Patient: Johnathan Doe, DOB: 14/05/1968. Admitted with acute coronary syndrome. Diagnosed with NSTEMI.",
            ocr_applied=False,
            processing_status="EXTRACTED",
        )
        page2 = DocumentPage(
            id="44444444-4444-4000-8000-444444444442",
            document_id=demo_doc.id,
            page_number=2,
            extracted_text="Discharge medications: Atorvastatin increased to 40mg OD. Metformin 500mg BD continued. Plan: Outpatient transthoracic echocardiogram in 4 weeks.",
            ocr_applied=False,
            processing_status="EXTRACTED",
        )
        db.add_all([page1, page2])

        # 8. Processing Job
        job = ProcessingJob(
            id="55555555-5555-4000-8000-555555555555",
            document_id=demo_doc.id,
            job_type="FULL_DOCUMENT_PROCESSING",
            status="COMPLETED",
            progress=100,
            total_pages=2,
            processed_pages=2,
        )
        db.add(job)

        # 9. Clinical Events
        event1 = ClinicalEvent(
            id="66666666-6666-4000-8000-666666666661",
            patient_id=demo_patient.id,
            event_type="ADMISSION",
            event_date=datetime(2026, 2, 5, 8, 30),
            event_date_precision="EXACT",
            title="Hospital Admission for NSTEMI",
            description="Patient admitted with acute substernal chest discomfort. Troponin I elevated at 0.42 ng/mL.",
            source_document_id=demo_doc.id,
            source_page_id=page1.id,
            confidence=0.98,
            is_ai_generated=True,
            review_status="VERIFIED",
        )
        event2 = ClinicalEvent(
            id="66666666-6666-4000-8000-666666666662",
            patient_id=demo_patient.id,
            event_type="DISCHARGE",
            event_date=datetime(2026, 2, 10, 14, 0),
            event_date_precision="EXACT",
            title="Hospital Discharge",
            description="Hemodynamically stable discharge on dual antiplatelet and high-intensity statin therapy.",
            source_document_id=demo_doc.id,
            source_page_id=page2.id,
            confidence=0.99,
            is_ai_generated=True,
            review_status="VERIFIED",
        )
        db.add_all([event1, event2])

        # 10. Medications
        med1 = Medication(
            id="77777777-7777-4000-8000-777777777771",
            patient_id=demo_patient.id,
            medication_name="Lipitor",
            generic_name="Atorvastatin",
            dosage="40",
            dose_unit="mg",
            route="Oral",
            frequency="Once daily at bedtime",
            status="ACTIVE",
            start_date=date(2026, 2, 9),
            source_document_id=demo_doc.id,
            source_page_id=page2.id,
        )
        med2 = Medication(
            id="77777777-7777-4000-8000-777777777772",
            patient_id=demo_patient.id,
            medication_name="Glucophage",
            generic_name="Metformin",
            dosage="500",
            dose_unit="mg",
            route="Oral",
            frequency="Twice daily with meals",
            status="ACTIVE",
            start_date=date(2020, 3, 12),
            source_document_id=demo_doc.id,
            source_page_id=page2.id,
        )
        db.add_all([med1, med2])

        # 11. Medication Change
        med_change = MedicationChange(
            id="88888888-8888-4000-8000-888888888888",
            medication_id=med1.id,
            change_type="DOSE_CHANGED",
            previous_value="20mg OD",
            new_value="40mg OD",
            change_date=date(2026, 2, 9),
            reason="Up-titration to high-intensity statin therapy post-NSTEMI",
            source_document_id=demo_doc.id,
            source_page_id=page2.id,
            is_ai_generated=True,
            review_status="VERIFIED",
        )
        db.add(med_change)

        # 12. Investigations
        inv1 = Investigation(
            id="99999999-9999-4000-8000-999999999991",
            patient_id=demo_patient.id,
            investigation_name="Troponin I",
            investigation_type="LAB",
            completed_date=date(2026, 2, 5),
            status="COMPLETED",
            result_summary="0.42 ng/mL",
            reference_range="< 0.04 ng/mL",
            is_abnormal=True,
            clinical_urgency="HIGH",
            source_document_id=demo_doc.id,
            source_page_id=page1.id,
        )
        inv2 = Investigation(
            id="99999999-9999-4000-8000-999999999992",
            patient_id=demo_patient.id,
            investigation_name="Transthoracic Echocardiogram",
            investigation_type="IMAGING",
            status="ORDERED",
            result_summary="Pending outpatient appointment",
            reference_range="N/A",
            clinical_urgency="HIGH",
            source_document_id=demo_doc.id,
            source_page_id=page2.id,
        )
        db.add_all([inv1, inv2])

        # 13. Outstanding Items
        item = OutstandingItem(
            id="aaaaaaaa-aaaa-4000-8000-aaaaaaaaaaaa",
            patient_id=demo_patient.id,
            item_type="PENDING_INVESTIGATION",
            title="Follow-up Transthoracic Echocardiogram",
            description="Outpatient TTE ordered at discharge to assess post-infarct left ventricular ejection fraction.",
            priority="HIGH",
            status="OPEN",
            due_date=date(2026, 3, 10),
            source_document_id=demo_doc.id,
            source_page_id=page2.id,
            is_ai_generated=True,
            review_status="VERIFIED",
        )
        db.add(item)

        # 14. Summary
        summary = Summary(
            id="bbbbbbbb-bbbb-4000-8000-bbbbbbbbbbbb",
            patient_id=demo_patient.id,
            summary_type="QUICK_CLINICAL",
            title="Clinical Brief — Post-NSTEMI Admission",
            content="57M admitted Feb 2026 with NSTEMI. Successfully stabilized. Statin dose increased to Atorvastatin 40mg OD. Outstanding outpatient echocardiogram required.",
            status="DRAFT",
            generated_by=demo_user.id,
            is_ai_generated=True,
            model_name="gemini-1.5-flash",
            model_version="002",
        )
        db.add(summary)

        # 15. Evidence Reference
        evidence = EvidenceReference(
            id="cccccccc-cccc-4000-8000-cccccccccccc",
            patient_id=demo_patient.id,
            document_id=demo_doc.id,
            document_page_id=page2.id,
            parent_entity_type="MEDICATION_CHANGE",
            parent_entity_id=med_change.id,
            source_section="Discharge Medications",
            source_text="Atorvastatin increased to 40mg OD.",
            source_type="PDF_TEXT",
            confidence=0.99,
        )
        db.add(evidence)

        # 16. Draft
        draft = Draft(
            id="dddddddd-dddd-4000-8000-dddddddddddd",
            patient_id=demo_patient.id,
            draft_type="REFERRAL",
            title="Referral to Cardiology Outpatient Service",
            content="Dear Colleague, Thank you for seeing Mr. Johnathan Doe (DOB 14/05/1968) for post-NSTEMI review and echocardiogram assessment.",
            status="DRAFT",
            created_by=demo_user.id,
            generated_by_ai=True,
            model_name="gemini-1.5-pro",
            model_version="002",
        )
        db.add(draft)

        # 17. Audit Event
        audit = AuditEvent(
            id="eeeeeeee-eeee-4000-8000-eeeeeeeeeeee",
            user_id=demo_user.id,
            action="PATIENT_VIEW",
            resource_type="PATIENT",
            resource_id=demo_patient.id,
            metadata_json='{"ip": "127.0.0.1", "interface": "desktop_dashboard"}',
        )
        db.add(audit)

        db.commit()
        print("[OK] Successfully seeded 17 demo entity records (labeled DEMO/TEST).")
    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
    if "--seed" in sys.argv:
        seed_demo_data()
