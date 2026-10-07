/**
 * MedBrief AI — Clinical Timeline API Client
 * Step 10: Clinical Timeline
 *
 * REST API client interacting with /api/v1/patients/{patient_id}/timeline endpoints.
 * Automatically attaches Authorization Bearer token from localStorage.
 */

import type {
  PatientTimelineResponse,
  PatientTimelineSummaryResponse,
  TimelineFilterParams,
} from '../types/timeline'

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

export async function fetchPatientTimeline(
  patientId: string,
  params: TimelineFilterParams = {}
): Promise<PatientTimelineResponse> {
  const query = new URLSearchParams()
  if (params.event_type && params.event_type !== 'ALL') {
    query.append('event_type', params.event_type)
  }
  if (params.date_from) {
    query.append('date_from', params.date_from)
  }
  if (params.date_to) {
    query.append('date_to', params.date_to)
  }
  if (params.search && params.search.trim()) {
    query.append('search', params.search.trim())
  }
  if (params.sort) {
    query.append('sort', params.sort)
  }
  if (params.page) {
    query.append('page', params.page.toString())
  }
  if (params.page_size) {
    query.append('page_size', params.page_size.toString())
  }

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/timeline${qs}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch clinical timeline (${response.status})`)
  }

  return response.json()
}

export async function fetchPatientTimelineSummary(
  patientId: string
): Promise<PatientTimelineSummaryResponse> {
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/timeline/summary`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch timeline summary (${response.status})`)
  }

  return response.json()
}
