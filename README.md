# 🩺 MedBrief AI

> Intelligent Medical Summarization — Problem Statement P3

**Current phase: Step 15 — Deployment Preparation + Final Browser QA (BUILD COMPLETE)**

---

## 🎯 Project Overview

**MedBrief AI** is an intelligent medical report summarisation assistant. The platform is designed to assist healthcare professionals by transforming complex, unstructured clinical documents into clear, verified, and structured clinical summaries with timeline tracking, investigation highlights, and verifiable source references.

---

## 🌟 Branded Intro Experience (Step 1)

MedBrief AI features a lightweight, high-performance, code-based cinematic introduction experience:

- **Visual Narrative**:
  $$\text{Medical Records} \longrightarrow \text{Medical Knowledge} \longrightarrow \text{AI Intelligence} \longrightarrow \text{MedBrief AI}$$
- **Zero Heavy Dependencies**: Rendered entirely through responsive SVG vector artwork, an HTML5 particle canvas, and CSS animations (no video files, no stock footage, no external heavy libraries).
- **Cinematic Sequence**:
  1. *Dark Environment*: Deep navy atmosphere with floating ambient particles and faint constellation networks.
  2. *DNA Helix & Medical Knowledge*: A rising double helix rooted within an open medical record book.
  3. *Medical Cross Emblem*: Crystallization of the golden medical cross / infinity emblem.
  4. *Intelligence Reveal*: Ambient radial halo and light aura expanding across the emblem.
  5. *Brand Reveal*: Luminous "MedBrief AI" typography.
  6. *Tagline*: "Intelligent Medical Summarization".
  7. *Final Brand Hold*: Complete clinical brand composition.
  8. *App Transition*: Dissolves smoothly into the application foundation.
- **Accessibility**: Automatically detects `prefers-reduced-motion: reduce` to display a static brand hold and transition quickly without flashing or aggressive motion. Includes keyboard/click skip capability.
- **Multi-Device Responsive Design**: Fully responsive and tested across desktop (1920px+), laptop (1024px–1366px), tablet (768px), mobile portrait, and mobile landscape orientations.

---

## 🛠️ Technology Stack

| Layer | Technology | Status / Note |
|---|---|---|
| **Frontend** | React 19 + TypeScript + Vite | Configured, styled, & runnable (Step 1) |
| **Intro Animation** | Custom SVG + HTML5 Canvas + CSS | Fully implemented & responsive (Step 1) |
| **Backend** | Python 3.14 + FastAPI + Uvicorn | Configured, health check verified (Step 1) |
| **Database** | PostgreSQL / Supabase (SQLAlchemy) | Implemented (17 Tables & Migrations) (Step 3) |
| **Authentication & RBAC** | Cryptographic JWT + DB Role Mapping | Implemented (Doctor, Admin, Patient Access) (Step 4) |
| **Doctor Dashboard UI** | Responsive Clinical Workspace + AI Previews | Implemented (Metrics, Attention, Feed, Records) (Step 5) |
| **Patient Management** | Caseload Directory, Demographics & Dossier | Implemented (MRN Indexing, Clinical Shells) (Step 6) |
| **Document Ingestion** | PDF Validation, Private Storage & Jobs | Implemented (Streaming, Magic Bytes, Checksum) (Step 7) |
| **AI Gateway** | Google Gemini API (`google-genai`) | Implemented (Backend-Only, Structured Output, Safety) (Step 8) |
| **Medical Extraction** | Page-Aware Clinical Entity Extraction | Implemented (6 Categories, Grounded Citations, Negation & Uncertainty Fidelity) (Step 9) |
| **Clinical Timeline** | Deterministic Chronological Engine | Implemented (Date Precision, Period Grouping, Grounded Evidence) (Step 10) |
| **Medication & Investigation Intelligence** | Change Intelligence & Status Engine | Implemented (Dose Evolution, Strict Pending Rules, Outstanding Items) (Step 11) |
| **AI Clinical Summaries & Evidence** | Gemini Grounded Multi-Mode Synthesizer | Implemented (Evidence Reference Linking, Uncertainty Flags) (Step 12) |
| **Clinical Composers & Drafts** | Editable Referral, Discharge & Handoff Suite | Implemented (Clinician Sign-off, Non-destructive Versions) (Step 13) |
| **Security, Testing & Reliability** | Zero-PHI Audit, Prompt-Injection Boundary, Automated Pytest Suite | Implemented & Hardened (222 Tests Passing, ErrorBoundary) (Step 14) |
| **Deployment & Production Ready** | Multi-Stage Docker, Nginx SPA, Orchestration, Health/Ready Probes | Complete & Verified (222 Tests Passing, Vite 6 Clean Build) (Step 15) |



---

## 📁 Repository Structure

```
├── .github/              # CI workflows and issue templates
├── demo/                 # Demo videos and screenshots
│   └── screenshots/      # App & brand screenshots
├── docs/                 # Documentation & architectural guides
│   ├── architecture.md
│   ├── problem-statement.md
│   ├── setup-guide.md
│   └── solution-overview.md
├── presentation/         # Presentation materials
├── src/                  # Source code
│   ├── backend/          # FastAPI backend service
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── tests/
│   │       └── test_health.py
│   └── frontend/         # React + TypeScript frontend
│       ├── src/
│       │   ├── components/
│       │   │   └── MedBriefIntro/   # Branded cinematic intro components
│       │   ├── App.tsx
│       │   └── main.tsx
│       ├── package.json
│       └── vite.config.ts
├── .env.example          # Environment variables template (placeholders only)
├── .gitignore            # Git exclusion rules
├── package.json          # Root convenience scripts
├── README.md             # Project documentation
└── submission.yaml       # Hackathon submission metadata
```

---

## ⚡ Getting Started (Local Development)

### 1. Prerequisites
- **Node.js** (v20+) and **npm** (v10+)
- **Python** (v3.11+) and `pip`

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Only placeholder values are present in Step 1; no external API keys or credentials are required to run the local foundation).*

### 3. Backend Setup
Create and activate a virtual environment, then install backend dependencies:
```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r src/backend/requirements.txt
```

Run backend tests:
```bash
pytest src/backend/tests -v
```

Start the FastAPI backend:
```bash
uvicorn src.backend.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000` (Health check: `http://localhost:8000/health`).

### 4. Frontend Setup
In a separate terminal, install dependencies and start the Vite dev server:
```bash
npm --prefix src/frontend install
npm --prefix src/frontend run dev
```
Frontend will be live at `http://localhost:5173`.

### 5. Medical Information Extraction (Step 9)
MedBrief AI extracts structured, verifiable medical facts across 6 standardized categories from uploaded PDF records:
- **Clinical Events**: Documented encounters, consultations, admissions, and observations with safe date precision (EXACT, MONTH_YEAR, YEAR_ONLY, APPROXIMATE, UNKNOWN).
- **Conditions & Problem List**: Diagnoses and clinical symptoms with explicit negation (`[Ruled Out / Denied]`) and uncertainty flags (`[Suspected]`, conflict details).
- **Medications**: Prescriptions with dosage, dose unit, route, frequency, and status (ACTIVE, STOPPED).
- **Diagnostic Investigations**: Lab tests and diagnostic imaging with numerical values, reference ranges, and abnormal indicators.
- **Procedures**: Documented interventional or surgical procedures with dates and documented outcomes.
- **Follow-up Instructions**: Specialist consultations and repeat test orders with priority and target dates.
- **Auditable Evidence Citations**: Every extracted entity is linked to an `EvidenceReference` containing page number, parent entity ID, and authentic verbatim source text.
- **Full Idempotency**: Re-running or retrying extraction safely replaces previous AI extractions for the document, preventing duplicate records.

### 6. Clinical Timeline (Step 10)
MedBrief AI reconstructs an authentic, chronological patient journey from extracted clinical events:
- **100% Deterministic Engine**: Built entirely in deterministic code (Zero LLM calls for sorting or timeline construction) to eliminate hallucinated chronology.
- **Strict Date Precision Fidelity**:
  - `EXACT`: Full date (and time when documented).
  - `MONTH_YEAR`: Preserves month and year; never invents missing day ("01").
  - `YEAR_ONLY`: Preserves year only; never invents missing month or day ("01 Jan").
  - `APPROXIMATE`: Displays `Approx.` prefix to maintain diagnostic honesty.
  - `UNKNOWN` / Undated: Isolated in a distinct "Date not documented" section.
- **Source Traceability**: Every timeline event displays the source document name, page number, and an expandable verbatim evidence excerpt.
- **Contradiction Alerting**: Flags conflicting dates or discordant facts across documents (`is_conflict`, `conflict_details`).
- **Interactive Clinical Controls**: Filter by event type, date range, keyword search, and toggle chronological ordering (newest first / oldest first).

### 7. Medication + Investigation Intelligence (Step 11)
MedBrief AI constructs a high-fidelity intelligence layer across medications, laboratory investigations, and outstanding clinical items:
- **Medication Change Intelligence**:
  - Automatically identifies drug starts, discontinuations (`STOPPED`), dose adjustments (`DOSE_CHANGED`), frequency changes, and route transitions.
  - **Deterministic Comparison**: Dose changes (`20 mg → 40 mg`) are synthesized only when both values exist in the record.
  - **No False Changes**: A drug mentioned for the first time without a prior dose never creates a false dose change.
  - **No Disappearing Drug Assumptions**: A drug omitted from a subsequent discharge note is never assumed stopped.
  - **Discordant Regimen Alerting**: Retains and highlights conflicting documented dosages across different medical records.
- **Investigation Intelligence & Diagnostic Tracking**:
  - Classifies lab tests and imaging into `ORDERED`, `PENDING`, `COMPLETED`, `CANCELLED`, or `UNKNOWN`.
  - **Strict Pending Rule**: An investigation is only marked `PENDING` if the source explicitly supports it (e.g., *"pending"*, *"awaiting results"*). Missing results never automatically infer pending status.
  - Highlights abnormal findings, reference ranges, and critical clinical urgencies.
- **Outstanding Clinical Actions & Follow-ups**:
  - Catalogs pending investigations, required clinical follow-ups, medication reviews, specialist consults, and monitoring directives with explicit timeframes and priority flags.
- **Documented vs. Derived Distinction**: Explicit tagging distinguishing documented source facts from chronological comparison transitions.
- **Zero-PHI Audit Logging**: Dedicated auditable REST endpoints logging accesses with zero PHI in compliance with patient safety principles.

### 8. AI Clinical Summary & Evidence Reference Layer (Step 12)
MedBrief AI provides doctor-in-the-loop synthesized clinical summaries powered by Gemini AI with complete, auditable evidence citations:
- **Multi-Mode Summarization**:
  - `QUICK_CLINICAL`: High-yield executive summary covering active conditions, current medications, key changes, investigations, and outstanding items.
  - `DETAILED_CLINICAL`: Exhaustive narrative clinical synthesis across inpatient admissions, outpatient consults, complete pharmacotherapy history, and diagnostic timelines.
  - `MEDICATION`: Focused intelligence on active medications, dose adjustments, discontinuations, and conflicting regimens.
  - `INVESTIGATION`: Diagnostic workup review, abnormal value tracking, and strictly verified pending tests.
- **Traceability > Completeness > Fluency (Zero Hallucination Guarantee)**:
  - Every clinical statement maps directly to persistent `EvidenceReference` records containing document ID, page number, and authentic verbatim quotes.
  - Post-generation **Hallucination Guard**: Validates all generated document IDs and page numbers against the patient's database records; ungrounded statements are automatically flagged as uncertain (`is_uncertain=True`).
  - **No Treatment Recommendations**: Strict negative prompts and regex guards neutralize unsolicited prescribing or triage advice ("We recommend...", "Should initiate...").
  - **Insufficient Information Handling**: When records are empty or lacking evidence, the system deterministically outputs *"Insufficient information in the uploaded record."*
- **Non-Destructive Version History**: Multiple summaries per patient can be generated, cataloged, and retrieved with full historical versioning.
- **Interactive Grounded Evidence UI**: Clinicians can click any citation pill across the Clinical Brief or dedicated Summaries view to inspect the verbatim source quote in a dedicated verification drawer.

### 9. Clinical Composers & Editable Draft Workflow (Step 13)
MedBrief AI delivers a dedicated clinician-in-the-loop correspondence composer and draft review workflow:
- **3 Purpose-Built Clinical Document Types**:
  - `REFERRAL`: Specialist referral letters detailing reason for consult, background medical history, active medications, key investigation findings, and explicit questions for the consultant.
  - `DISCHARGE`: Inpatient discharge summaries featuring admission circumstances, hospital course, confirmed diagnoses, completed procedures, reconciled discharge medications, and structured follow-up care plans. *(Strictly zero invented discharge dates or hospital stays)*.
  - `HANDOFF`: Structured shift handoff and inter-unit transfer summaries organizing active clinical problems, critical events, recent medication adjustments, pending diagnostic studies, and prioritized monitoring tasks.
- **Safety & Grounded Hallucination Guard**:
  - 100% grounded in verified patient medical facts from earlier extraction and intelligence phases.
  - Foreign, unverified, or hallucinated citations are stripped and flagged by the backend Hallucination Guard.
  - Zero treatment/prescribing directives: Unsolicited prescribing advice is automatically neutralized to preserve physician autonomy.
  - Missing data is never invented; sections without recorded evidence state *"Not documented in the available record."*
- **Doctor Sign-Off & Approval Lifecycle**:
  - All generated drafts initialize in `DRAFT` status and are never automatically marked as approved.
  - Prominent visual safety banner: `AI GENERATED DRAFT — CLINICIAN REVIEW REQUIRED`.
  - Full clinician editing suite: Physicians can edit titles, amend narrative body text, redact sentences, or save revisions (`IN_REVIEW`).
  - Formal sign-off commits status to `APPROVED`, immutably recording the reviewing clinician and timestamp.
  - Non-destructive version history: Multiple drafts per patient can be generated, cataloged, and retrieved with full historical versioning.
- **Verifiable Citation Drawer**:
  - Clickable citation pills throughout structured draft sections and grounded evidence grids open an authentic verification modal displaying the exact document name, page number, and verbatim record excerpt.

### 10. Demo Clinical Accounts (Step 4 Authentication)
The local development database automatically seeds the following fictional accounts:

| Role | Email | Password | Scope & Privileges |
|---|---|---|---|
| **Doctor** | `dr.sarah.chen@demo-clinic.test` *(or `doctor.demo@medbrief.local`)* | `MedBrief2026!` | Access to clinical workspace & assigned patient `Johnathan Doe` |
| **Admin** | `admin@demo-clinic.test` *(or `admin.demo@medbrief.local`)* | `MedBriefAdmin2026!` | Access to system administration & audit shell (No direct unassigned clinical access) |

---

### 11. Security Hardening, AI Safety & Automated Testing (Step 14)
MedBrief AI implements comprehensive clinical security hardening, AI guardrails, and test coverage:

- **Zero-PHI Audit Logging**:
  - All audit events (`AuditEvent`) record purely non-identifying operational metadata (`patient_id`, `action`, `user_id`, `resource_type`).
  - Patient names, MRNs, phone numbers, and full clinical texts are strictly excluded from audit payloads, URLs, and console logs.
- **Strict Prompt-Injection Defense**:
  - Medical document inputs and physician custom instructions are categorized as **Untrusted Data** and wrapped in `<untrusted_medical_data>` boundary delimiters.
  - Clinical safety guardrails explicitly instruct the LLM to ignore embedded system overrides, role reversals, or prompts such as *"Ignore previous instructions"*.
- **Authoritative Server-Side RBAC & Patient Access Control**:
  - Roles are dynamically queried from database relationships on every authenticated request; client-supplied role claims in JWT or headers are ignored.
  - Every clinical endpoint enforces patient-level access via `can_user_access_patient(user_id, patient_id)` and fails closed with HTTP 403 Forbidden.
- **Mass-Assignment & Input Validation**:
  - Pydantic models strictly validate mutable fields; immutable attributes (`id`, `created_by`, `created_at`) cannot be modified via PATCH/PUT requests.
  - Path traversal attempts, negative page numbers, and invalid UUID formats are safely rejected with 403/404/422 without triggering 500 server errors.
- **Frontend Clinical ErrorBoundary**:
  - React `ErrorBoundary` wraps protected views, isolating rendering issues and preventing white-screen crashes while preserving physician session integrity.
- **Automated Test Matrix (222 Tests Passing)**:
  - 13 comprehensive backend test modules covering authentication, RBAC, access matrices, document ingestion, Gemini AI gateway, entity extraction, timeline engine, clinical intelligence, summaries, drafts, prompt injection defense, and health/readiness endpoints.

---

### 12. Production Deployment & Verification (Step 15)
MedBrief AI is packaged with a complete containerized production deployment stack:

- **Multi-Stage Container Architecture**:
  - **Backend Container (`src/backend/Dockerfile`)**: Python 3.11-slim base, unprivileged `medbrief` system user, healthcheck probe, and dynamic port binding (`$PORT` / `$APP_PORT`).
  - **Frontend Container (`src/frontend/Dockerfile`)**: Node 20-alpine builder compiling optimized Vite/React bundles, served by Nginx Alpine with SPA fallback routing, gzip compression, and security headers.
  - **Full-Stack Orchestration (`docker-compose.yml`)**: Single-command container deployment binding frontend (port 3000), backend (port 8000), and private volume-mounted medical document storage.
- **Production Health & Readiness Probes**:
  - `GET /health`: Liveness probe verifying service availability and database connectivity without leaking credentials.
  - `GET /ready`: Readiness probe for Kubernetes / cloud container orchestrators confirming startup readiness.
- **21-Step End-to-End Clinical QA Validation**:
  - 100% pass rate across the full clinical journey: Auth → Caseload → Dossier → PDF Upload → Streaming → Timeline → Meds → Invs → Summary → Evidence → Referral/Discharge/Handoff Drafts → Approval → Logout.
- **Responsive & Accessibility Verified**:
  - Responsive layouts audited across Desktop (1440px), Laptop (1280px), Tablet (768px), and Mobile (390px).
  - 149 ARIA attributes and semantic clinical structures, respecting `prefers-reduced-motion: reduce`.

---

## 🔒 Security & Healthcare Data Principles
- All test/sample data used during development is strictly synthetic and fictional.
- Server-side RBAC: Client-supplied roles are never trusted. Roles are resolved dynamically from database relationships.
- Secrets and API credentials are kept in `.env` (excluded by `.gitignore`) and never exposed in client code.
- Zero PHI in logs, URLs, error messages, and browser local storage.
- Fails closed on unauthorized access attempts with auditable event tracking.
- All Gemini calls strictly backend-controlled; keys never present in frontend bundles.



