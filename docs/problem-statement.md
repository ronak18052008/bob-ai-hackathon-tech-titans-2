# Problem Statement — P3: Medical Report Summarisation Assistant

## Background
In modern clinical healthcare settings, physicians, specialists, and care teams routinely encounter patients with extensive, fragmented medical histories. Patients presenting for acute admissions, specialty referrals, or routine consultations often arrive with dozens to hundreds of pages of unstructured clinical documentation spanning prior hospital discharge summaries, specialist consultation notes, outpatient clinic letters, pathology and laboratory reports, radiology scans, and medication administration records.

## The Problem
Doctors spend an estimated 30–45% of their working day manually reviewing, cross-referencing, and synthesizing disparate paper and electronic medical records. Critical medical information—including active medication changes, pending diagnostic investigations, conflicting diagnoses, and historical interventions—is frequently buried across dense multi-page documents (ranging from 50 to 200+ pages). This cognitive overload leads to:
1. **Clinical Oversights**: Overlooked pending investigations, delayed diagnoses, and failure to recognize medication discontinuations.
2. **Physician Burnout**: Substantial administrative fatigue and time diverted away from direct patient examination and bedside care.
3. **Delayed Clinical Workflows**: Extended delays in drafting discharge summaries and specialist referral handoffs.

## Who is Affected
- **Hospitalists and Inpatient Physicians**: Admitting patients with complex multi-morbid histories under strict time constraints.
- **General Practitioners and Outpatient Clinicians**: Conducting 15-minute consultations requiring rapid assimilation of multi-year patient records.
- **Specialists and Surgeons**: Reviewing multi-source referral packages before procedures or tertiary consultations.
- **Patients**: Subject to duplicated tests, adverse drug reactions from uncoordinated regimens, and fragmented transitions of care.

## Why It Matters
Medical record documentation review errors directly jeopardize patient safety. Unrecognized adverse drug interactions and missed critical laboratory findings are major contributors to preventable hospital readmissions and clinical incidents. Furthermore, physician administrative burden is a leading driver of clinical attrition globally.

## Why Existing Solutions Fall Short
- **Generic AI Chatbots**: Lack medical grounding, produce unreferenced statements prone to hallucination, and fail to provide auditable source citations.
- **Standard OCR Tools**: Output flat, unorganized text without clinical context, chronological timeline reconstruction, or pharmacotherapy change detection.
- **Electronic Health Record (EHR) Native Viewers**: Present isolated document repositories requiring clinicians to open and manually read individual PDF attachments without cross-document synthesis or discrepancy detection.
