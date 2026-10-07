# Solution Overview — MedBrief AI

> **MedBrief AI**: Intelligent Medical Summarization  
> **Problem Statement P3**: Medical Report Summarisation Assistant  

## What We Built
**MedBrief AI** is a clinical intelligence platform designed to assist healthcare professionals in processing, understanding, and summarizing extensive patient medical records. Built with an **evidence-first, clinician-in-the-loop philosophy**, the system digests multi-source PDF documents (up to 200+ pages), extracts structured clinical data, reconstructs a chronological clinical timeline, tracks medication adjustments, detects outstanding investigations, and generates verifiable clinical summaries with exact page-level source references.

## How It Works
The end-to-end mechanism consists of five coordinated stages:

1. **Secure Ingestion & Validation**: The clinician uploads multi-page medical records (discharge notes, lab reports, clinic letters). The backend validates PDF integrity, stores files in encrypted storage, and launches an asynchronous processing job.
2. **Page-Level Extraction & Segmentation**: Documents are parsed page-by-page using high-fidelity text extraction with OCR fallback for scanned pages, segmented into clinical sections, and batched using a sliding-window token chunker.
3. **Structured Server-Side AI Inference**: Batches are processed by server-side Google Gemini models to extract structured entities (diagnoses, procedures, vitals, medications, tests) validated against Pydantic schemas.
4. **Clinical Synthesis & Discrepancy Detection**: The engine builds a chronological clinical timeline, maps pharmacotherapy titrations, identifies pending/overdue investigations, and flags conflicting information across sources without overwriting.
5. **Auditable Clinical Presentation & Draft Generation**: The doctor reviews the synthesized dossier on a multi-device responsive web dashboard. Clicking any clinical fact highlights the exact source document, page, and snippet. The clinician can generate and edit referral/discharge letter drafts with formal sign-off.

## Architecture Diagram

```
[Clinician / Browser] 
       │ (Responsive React + TS Web App / PWA Ready)
       ▼
[FastAPI Backend Gateway] 
       ├── (RBAC / Auth / Input Validation / Rate Limiter)
       ▼
[Application Services Layer]
       ├── Document Ingestion & PyMuPDF/OCR Chunker
       ├── Server-Side Gemini AI Engine (Google GenAI SDK)
       ├── Evidence Linker & Conflict Preservation Service
       └── Timeline & Pharmacotherapy Synthesizer
       ▼
[Persistence Layer]
       ├── PostgreSQL / Supabase (Relational Clinical Dossier)
       ├── Encrypted Document Storage (Source PDFs)
       └── Immutable Audit Log (Compliance & Security)
```

## Key Architectural Decisions

| Decision | Rationale |
|---|---|
| **Server-Side AI Isolation** | Gemini API keys and prompts are strictly maintained on the FastAPI backend to prevent credential exposure and enforce access control. |
| **Evidence-First Traceability** | Every extracted clinical event, medication, and test links back to its exact document ID, page number, and source snippet. |
| **Conflict Preservation** | Contradictory medical information (e.g. conflicting medication doses) is explicitly flagged for physician review rather than arbitrarily resolved by AI. |
| **Doctor-in-the-Loop Sign-Off** | All AI summaries and generated referral/discharge letters are treated as drafts until explicitly approved by an authorized clinician. |
| **Single Responsive Web Application** | One codebase seamlessly supporting Desktop, Laptop, Tablet, and Mobile devices without separate native apps. |
| **Zero Insecure Offline Medical Caching** | Patient health data is never cached in service workers or local browser storage to guarantee shared-workstation security. |
