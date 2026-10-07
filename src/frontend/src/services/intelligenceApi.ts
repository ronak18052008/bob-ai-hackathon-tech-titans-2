/**
 * MedBrief AI — Clinical Intelligence API Client
 * Step 11: Medication + Investigation Intelligence
 *
 * REST API client interacting with /api/v1/patients/{patient_id} intelligence endpoints.
 * Automatically attaches Authorization Bearer token from localStorage.
 */

import type {
  PatientMedicationsResponse,
  PatientMedicationChangesResponse,
  PatientInvestigationsResponse,
  PatientOutstandingItemsResponse,
  PatientIntelligenceSummaryResponse,
} from '../types/intelligence'

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

export async function fetchPatientMedications(
  patientId: string,
  params: { status?: string; search?: string; sort?: string; page?: number; pageSize?: number } = {}
): Promise<PatientMedicationsResponse> {
  const query = new URLSearchParams()
  if (params.status && params.status !== 'ALL') query.append('status', params.status)
  if (params.search && params.search.trim()) query.append('search', params.search.trim())
  if (params.sort) query.append('sort', params.sort)
  if (params.page) query.append('page', params.page.toString())
  if (params.pageSize) query.append('page_size', params.pageSize.toString())

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/medications${qs}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch medications (${response.status})`)
  }
  return response.json()
}

export async function fetchPatientMedicationChanges(
  patientId: string,
  params: { changeType?: string; dateFrom?: string; dateTo?: string; sort?: string; page?: number; pageSize?: number } = {}
): Promise<PatientMedicationChangesResponse> {
  const query = new URLSearchParams()
  if (params.changeType && params.changeType !== 'ALL') query.append('change_type', params.changeType)
  if (params.dateFrom) query.append('date_from', params.dateFrom)
  if (params.dateTo) query.append('date_to', params.dateTo)
  if (params.sort) query.append('sort', params.sort)
  if (params.page) query.append('page', params.page.toString())
  if (params.pageSize) query.append('page_size', params.pageSize.toString())

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/medication-changes${qs}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch medication changes (${response.status})`)
  }
  return response.json()
}

export async function fetchPatientInvestigations(
  patientId: string,
  params: { status?: string; investigationType?: string; search?: string; sort?: string; page?: number; pageSize?: number } = {}
): Promise<PatientInvestigationsResponse> {
  const query = new URLSearchParams()
  if (params.status && params.status !== 'ALL') query.append('status', params.status)
  if (params.investigationType && params.investigationType !== 'ALL') query.append('investigation_type', params.investigationType)
  if (params.search && params.search.trim()) query.append('search', params.search.trim())
  if (params.sort) query.append('sort', params.sort)
  if (params.page) query.append('page', params.page.toString())
  if (params.pageSize) query.append('page_size', params.pageSize.toString())

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/investigations${qs}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch investigations (${response.status})`)
  }
  return response.json()
}

export async function fetchPatientOutstandingItems(
  patientId: string,
  params: { itemType?: string; status?: string; priority?: string; sort?: string; page?: number; pageSize?: number } = {}
): Promise<PatientOutstandingItemsResponse> {
  const query = new URLSearchParams()
  if (params.itemType && params.itemType !== 'ALL') query.append('item_type', params.itemType)
  if (params.status && params.status !== 'ALL') query.append('status', params.status)
  if (params.priority && params.priority !== 'ALL') query.append('priority', params.priority)
  if (params.sort) query.append('sort', params.sort)
  if (params.page) query.append('page', params.page.toString())
  if (params.pageSize) query.append('page_size', params.pageSize.toString())

  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/outstanding-items${qs}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch outstanding items (${response.status})`)
  }
  return response.json()
}

export async function fetchPatientIntelligenceSummary(
  patientId: string
): Promise<PatientIntelligenceSummaryResponse> {
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/intelligence/summary`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch intelligence summary (${response.status})`)
  }
  return response.json()
}
