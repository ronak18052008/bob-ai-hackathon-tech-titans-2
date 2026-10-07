# Setup Guide

> **MedBrief AI — Medical Report Summarisation Assistant**
> **Current phase: Step 15 — Deployment Preparation + Final Browser QA (BUILD COMPLETE)**

## Prerequisites

Before you begin, ensure you have the following installed:

- Node.js (v20+) & npm (v10+)
- Python (v3.11+) & pip
- Git

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Description | Default / Placeholder | Step |
|---|---|---|---|
| `APP_ENV` | Application runtime environment | `development` | Step 1 |
| `APP_PORT` | Backend server port | `8000` | Step 1 |
| `DATABASE_URL` | PostgreSQL connection string | *empty placeholder* | Step 3 |
| `SUPABASE_URL` | Supabase project URL | *empty placeholder* | Step 3 |
| `SUPABASE_ANON_KEY` | Supabase anon key | *empty placeholder* | Step 3 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | *empty placeholder* | Step 3 |
| `MAX_DOCUMENT_SIZE_MB` | Maximum document upload size | `25` | Step 7 |
| `STORAGE_DIR` | Private document storage path | `storage/documents` | Step 7 |
| `GEMINI_API_KEY` | Google Gemini API key (strictly backend-only) | *empty placeholder* | Step 8 |
| `GEMINI_MODEL` | Gemini AI model identifier | `gemini-2.5-flash` | Step 8 |
| `GEMINI_MAX_INPUT_CHARS` | Prompt character safety limit | `100000` | Step 8 |
| `GEMINI_MAX_OUTPUT_TOKENS` | Maximum model response tokens | `4096` | Step 8 |
| `GEMINI_TIMEOUT_SECONDS` | Maximum request timeout threshold | `30.0` | Step 8 |
| `GEMINI_MAX_RETRIES` | Transient error retry count | `3` | Step 8 |
| `VITE_API_URL` | Frontend API URL base | `http://localhost:8000` | Step 1 |

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/ronak18052008/bob-ai-hackathon-tech-titans-2.git
cd MedBrief-AI
```

### 2. Backend Installation
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r src/backend/requirements.txt
```

### 3. Frontend Installation
```bash
npm --prefix src/frontend install
```

## Running the Application

### Start the Backend
```bash
uvicorn src.backend.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Health Check: `http://localhost:8000/health`
- Interactive API Docs: `http://localhost:8000/docs`

### Start the Frontend
In a separate terminal:
```bash
npm --prefix src/frontend run dev
```
- Web Application: `http://localhost:5173`

## Running Tests

### Backend Unit Tests
```bash
pytest src/backend/tests -v
```

### Frontend Build & Type Check
```bash
npm --prefix src/frontend run build
```

## Gemini AI Integration (Step 8)

MedBrief AI incorporates a modular, secure backend AI Gateway using the official Google Gemini API (`google-genai`).

### Critical Security Principles
- **Backend-Only**: `GEMINI_API_KEY` exists strictly on the server and is never exposed to the frontend browser, client bundles, or log files.
- **Decision-Support Guardrails**: MedBrief AI is an assistive clinical documentation tool and does not replace clinician judgment.
- **Safe Telemetry**: PHI, full patient documents, and prompts are never recorded in application logs.

### Checking AI Health & Readiness
Verify the AI gateway configuration by querying the health endpoint (does not require authentication and never leaks keys):
```bash
curl http://localhost:8000/api/v1/ai/health
```
Response when configured:
```json
{
  "configured": true,
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "status": "ready"
}
```

### Running the Authenticated Test Ping
To test live end-to-end model inference without exposing patient data, send a synthetic test ping with a physician Bearer token:
```bash
# 1. Obtain token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.sarah.chen@demo-clinic.test","password":"MedBrief2026!"}' | jq -r .access_token)

# 2. Run test ping
curl -X POST http://localhost:8000/api/v1/ai/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_message": "Infrastructure verification ping"}'
```

### Troubleshooting
- **`status: unconfigured`**: Ensure `GEMINI_API_KEY` is defined in `src/backend/.env`.
- **`AI_RATE_LIMITED` (HTTP 429)**: The upstream quota is temporarily saturated; the gateway automatically retries with exponential backoff before returning a controlled error.
- **Model Availability**: Note that Gemini model availability, context windows, and quotas can change over time; configure `GEMINI_MODEL` as appropriate.

---

## Medical Information Extraction (Step 9)

Step 9 introduces page-aware structured clinical extraction from uploaded medical PDFs.

### Triggering Extraction via API

To trigger extraction for an authorized patient document:
```bash
# Obtain doctor token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.sarah.chen@demo-clinic.test","password":"MedBrief2026!"}' | jq -r .access_token)

# Trigger extraction
curl -X POST http://localhost:8000/api/v1/documents/{DOCUMENT_ID}/extract \
  -H "Authorization: Bearer $TOKEN"
```

### Retrieving Extracted Dossier

To view all extracted events, conditions, medications, investigations, procedures, and follow-ups:
```bash
curl http://localhost:8000/api/v1/documents/{DOCUMENT_ID}/extraction \
  -H "Authorization: Bearer $TOKEN"
```

### Running Extraction Tests

Run the dedicated test suite covering all 25 extraction requirements:
```bash
pytest src/backend/tests/test_extraction.py -v
```

---

## Clinical Timeline (Step 10)

Step 10 introduces a deterministic, chronological care journey reconstructed from structured clinical events.

### Core Architectural Principles
- **100% Deterministic Engine**: ZERO LLM calls for sorting, grouping, or organizing events. The timeline is assembled deterministically in code from `clinical_events`, `documents`, and `evidence_references`.
- **Strict Date Precision Fidelity**:
  - `EXACT`: Rendered with day, month, year (and time if recorded).
  - `MONTH_YEAR`: Rendered as `Mon YYYY` (e.g. `Feb 2026`). Never invents a missing day ("01").
  - `YEAR_ONLY`: Rendered as `YYYY` (e.g. `2024`). Never invents missing month or day ("01 Jan").
  - `APPROXIMATE`: Rendered with `Approx.` prefix to maintain diagnostic honesty.
  - `UNKNOWN` / `None`: Segregated into a distinct "Date not documented" drawer to prevent timeline hallucination.
- **Source Traceability**: Every clinical event links directly to the source document name, page number, and authentic verbatim text excerpt.
- **Conflict & Uncertainty Alerting**: Preserves contradictory notes across source records (`is_conflict`, `conflict_details`).

### Timeline REST API Endpoints

```bash
# Obtain doctor token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.sarah.chen@demo-clinic.test","password":"MedBrief2026!"}' | jq -r .access_token)

# 1. Fetch full patient clinical timeline (supports sorting, filters, search, and pagination)
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/timeline?sort=desc&event_type=ALL" \
  -H "Authorization: Bearer $TOKEN"

# 2. Fetch lightweight summary widget for Patient Overview cards
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/timeline/summary" \
  -H "Authorization: Bearer $TOKEN"
```

### Running Timeline Automated Tests
```bash
pytest src/backend/tests/test_timeline.py -v
```

---

## 💊 Clinical Intelligence Layer (Step 11)

### API Endpoints
All clinical intelligence endpoints require clinician authorization (JWT Bearer token) and record zero-PHI audit logs:

```bash
# Obtain doctor token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.sarah.chen@demo-clinic.test","password":"MedBrief2026!"}' | jq -r .access_token)

# 1. Fetch patient medications (supports status filter, search, sort, pagination)
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/medications?status=ACTIVE" \
  -H "Authorization: Bearer $TOKEN"

# 2. Fetch verified medication changes (started, stopped, dose/freq/route changes)
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/medication-changes?sort=desc" \
  -H "Authorization: Bearer $TOKEN"

# 3. Fetch diagnostic investigations (pathology, imaging, abnormal indicators)
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/investigations?status=ALL" \
  -H "Authorization: Bearer $TOKEN"

# 4. Fetch outstanding clinical items & follow-ups (pending tests, consults, monitoring)
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/outstanding-items?status=OPEN" \
  -H "Authorization: Bearer $TOKEN"

# 5. Fetch combined intelligence summary dossier for patient dashboard
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/intelligence/summary" \
  -H "Authorization: Bearer $TOKEN"
```

### Running Intelligence Automated Tests
```bash
pytest src/backend/tests/test_intelligence.py -v
```

---

## 📝 AI Clinical Summary & Evidence Layer (Step 12)

### API Endpoints
All summary generation and retrieval endpoints require clinician authorization (JWT Bearer token) and record zero-PHI audit logs:

```bash
# Obtain doctor token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.sarah.chen@demo-clinic.test","password":"MedBrief2026!"}' | jq -r .access_token)

# 1. Generate an AI Clinical Summary (QUICK_CLINICAL, DETAILED_CLINICAL, MEDICATION, or INVESTIGATION)
curl -X POST "http://localhost:8000/api/v1/patients/{PATIENT_ID}/summaries" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary_type": "QUICK_CLINICAL",
    "custom_instructions": "Focus on post-discharge cardiology follow-up"
  }'

# 2. List patient summaries with pagination and mode filtering
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/summaries?summary_type=QUICK_CLINICAL&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# 3. Retrieve full summary detail and backed evidence citations
curl "http://localhost:8000/api/v1/summaries/{SUMMARY_ID}" \
  -H "Authorization: Bearer $TOKEN"
```

### Running Summary Automated Tests
```bash
pytest src/backend/tests/test_summaries.py -v
```

---

## 📋 Clinical Composers & Editable Draft Workflow (Step 13)

### API Endpoints
All clinical draft composer and approval endpoints enforce physician authorization (JWT Bearer token), patient access verification, and zero-PHI audit logging:

```bash
# Obtain doctor token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.sarah.chen@demo-clinic.test","password":"MedBrief2026!"}' | jq -r .access_token)

# 1. Compose an AI Clinical Draft (REFERRAL, DISCHARGE, or HANDOFF)
curl -X POST "http://localhost:8000/api/v1/patients/{PATIENT_ID}/drafts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_type": "REFERRAL",
    "recipient_info": "Dr. Sarah Jenkins, Dept of Cardiology",
    "custom_instructions": "Focus on post-PCI dual antiplatelet therapy and echocardiogram follow-up"
  }'

# 2. List patient drafts with non-destructive version history
curl "http://localhost:8000/api/v1/patients/{PATIENT_ID}/drafts?draft_type=REFERRAL&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# 3. Retrieve draft detail with editable body, structured sections, and grounded citations
curl "http://localhost:8000/api/v1/drafts/{DRAFT_ID}" \
  -H "Authorization: Bearer $TOKEN"

# 4. Save clinician edits (updates status to IN_REVIEW)
curl -X PATCH "http://localhost:8000/api/v1/drafts/{DRAFT_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Amended Cardiology Referral Letter",
    "content": "Dear Dr. Jenkins, I am referring Mr. Johnathan Doe...",
    "status": "IN_REVIEW"
  }'

# 5. Formally approve and sign off draft (commits status to APPROVED and records reviewed_by)
curl -X PATCH "http://localhost:8000/api/v1/drafts/{DRAFT_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "APPROVED"
  }'
```

### Running Draft Automated Tests
```bash
pytest src/backend/tests/test_drafts.py -v
```

---

## 🔒 Security Hardening, AI Safety & Automated Testing (Step 14)

### Security Hardening Measures
1. **Zero-PHI Audit Logging**:
   - `log_auth_audit_event` strips patient names, medical record numbers (MRNs), phone numbers, and full clinical documents from database audit records.
   - Resource access logs contain only entity IDs (UUIDs) and non-identifying operational metadata.
   - Error responses and database health checks sanitize internal connection strings and credentials to avoid leakage.
2. **Untrusted Data Isolation & Prompt-Injection Defense**:
   - Clinical documents and user instructions are treated as **Untrusted Data** and enclosed in `<untrusted_medical_data>` boundary tags.
   - Prompt templates across extraction, summarization, and draft generation explicitly forbid the LLM from executing commands embedded in records (e.g. *"Ignore previous instructions"*, *"System prompt override"*).
3. **Fail-Closed Patient Access Control**:
   - Every patient-level endpoint verifies clinician assignment via `can_user_access_patient(user_id, patient_id, db)` before reading or mutating records.
   - Unauthorized attempts immediately return HTTP 403 Forbidden with audit logging.
4. **Mass-Assignment & Input Sanitization**:
   - Update models strictly limit mutable fields. Primary keys (`id`), foreign keys (`patient_id`), and system timestamps (`created_at`) cannot be modified by client requests.
   - Path traversal attempts (`..%2F..%2Fetc%2Fpasswd`) and invalid UUID formats are safely intercepted without causing internal 500 errors.
5. **Frontend Clinical ErrorBoundary**:
   - Top-level and protected route error boundaries prevent UI crashes, enabling clinicians to retry component rendering or safely reload without losing authentication state.

### Running Security & AI Safety Automated Tests

```bash
# 1. Run access control and security matrix tests (21 tests)
pytest src/backend/tests/test_security_access_matrix.py -v

# 2. Run AI safety, prompt injection, and hallucination guard tests (16 tests)
pytest src/backend/tests/test_ai_safety_and_injection.py -v

# 3. Run the complete backend test suite (222 tests across 13 modules)
pytest src/backend/tests -v
```

---

## 🚀 Production Deployment & Containerization (Step 15)

MedBrief AI provides Docker containerization for both backend and frontend, as well as full-stack orchestration via Docker Compose.

### Option A: Full-Stack Docker Compose (Recommended)

1. Configure environment variables in `.env` based on `.env.example`.
2. Build and launch all services:
```bash
docker compose up --build -d
```
3. Verify running containers:
```bash
docker compose ps
```
4. Access applications:
- **Frontend SPA**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`
- **Readiness Probe**: `http://localhost:8000/ready`

### Option B: Standalone Container Builds

```bash
# 1. Build and run backend container
docker build -t medbrief-backend -f src/backend/Dockerfile .
docker run -d -p 8000:8000 --env-file .env medbrief-backend

# 2. Build and run frontend container
docker build -t medbrief-frontend --build-arg VITE_API_URL=http://localhost:8000 -f src/frontend/Dockerfile .
docker run -d -p 3000:80 medbrief-frontend
```

### Production Readiness Verification

```bash
# Verify backend liveness
curl http://localhost:8000/health

# Verify backend readiness
curl http://localhost:8000/ready

# Verify frontend Nginx liveness
curl http://localhost:3000/healthz
```





