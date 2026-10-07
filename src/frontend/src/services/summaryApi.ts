/**
 * MedBrief AI — AI Clinical Summary API Client
 * Step 12: AI Clinical Summary + Evidence/Source Reference Layer
 *
 * REST API client interacting with:
 * - POST /api/v1/patients/{patient_id}/summaries
 * - GET  /api/v1/patients/{patient_id}/summaries
 * - GET  /api/v1/summaries/{summary_id}
 */

import type {
  SummaryType,
  SummaryDetail,
  PatientSummariesListResponse,
} from '../types/summary'

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

export async function generatePatientSummary(
  patientId: string,
  summaryType: SummaryType = 'QUICK_CLINICAL',
  customInstructions?: string
): Promise<SummaryDetail> {
  const payload: { summary_type: SummaryType; custom_instructions?: string } = {
    summary_type: summaryType,
  }
  if (customInstructions && customInstructions.trim()) {
    payload.custom_instructions = customInstructions.trim()
  }

  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/summaries`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to generate summary (${response.status})`)
  }

  return response.json()
}

export async function fetchPatientSummaries(
  patientId: string,
  params: { summaryType?: string; status?: string; page?: number; pageSize?: number } = {}
): Promise<PatientSummariesListResponse> {
  const query = new URLSearchParams()
  if (params.summaryType && params.summaryType !== 'ALL') query.append('summary_type', params.summaryType)
  if (params.status && params.status !== 'ALL') query.append('status', params.status)
  if (params.page) query.append('page', params.page.toString())
  if (params.pageSize) query.append('page_size', params.pageSize.toString())

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/summaries${qs}`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch summaries (${response.status})`)
  }

  return response.json()
}

export async function fetchSummaryById(summaryId: string): Promise<SummaryDetail> {
  const response = await fetch(`${API_URL}/api/v1/summaries/${summaryId}`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch summary detail (${response.status})`)
  }

  return response.json()
}
