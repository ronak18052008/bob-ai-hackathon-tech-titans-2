/**
 * MedBrief AI — Clinical Draft API Client
 * Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow
 *
 * REST API client interacting with:
 * - POST  /api/v1/patients/{patient_id}/drafts (Generate AI draft)
 * - GET   /api/v1/patients/{patient_id}/drafts (List patient drafts)
 * - GET   /api/v1/drafts/{draft_id}            (Get draft detail with sections & citations)
 * - PATCH /api/v1/drafts/{draft_id}            (Update draft content, title, or sign-off status)
 */

import type {
  DraftDetail,
  PatientDraftsListResponse,
  DraftGeneratePayload,
  DraftUpdatePayload,
} from '../types/draft'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'medbrief_clinical_token'

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export async function generatePatientDraft(
  patientId: string,
  payload: DraftGeneratePayload
): Promise<DraftDetail> {
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/drafts`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to generate draft (${response.status})`)
  }

  return response.json()
}

export async function fetchPatientDrafts(
  patientId: string,
  params: { draftType?: string; status?: string; page?: number; pageSize?: number } = {}
): Promise<PatientDraftsListResponse> {
  const query = new URLSearchParams()
  if (params.draftType && params.draftType !== 'ALL') query.append('draft_type', params.draftType)
  if (params.status && params.status !== 'ALL') query.append('status', params.status)
  if (params.page) query.append('page', params.page.toString())
  if (params.pageSize) query.append('page_size', params.pageSize.toString())

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/drafts${qs}`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch drafts (${response.status})`)
  }

  return response.json()
}

export async function fetchDraftById(draftId: string): Promise<DraftDetail> {
  const response = await fetch(`${API_URL}/api/v1/drafts/${draftId}`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch draft detail (${response.status})`)
  }

  return response.json()
}

export async function updateDraft(
  draftId: string,
  payload: DraftUpdatePayload
): Promise<DraftDetail> {
  const response = await fetch(`${API_URL}/api/v1/drafts/${draftId}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to update draft (${response.status})`)
  }

  return response.json()
}
