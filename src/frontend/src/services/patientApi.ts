/**
 * MedBrief AI — Patient Management API Client
 * Step 6: Patient Management
 *
 * REST API client interacting with /api/v1/patients endpoints.
 * Automatically attaches Authorization Bearer token from localStorage.
 */

import type {
  PatientRecord,
  PatientListResponse,
  PatientFormData,
  PatientFilters,
} from '../types/patient'

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

export async function fetchPatients(filters: PatientFilters = {}): Promise<PatientListResponse> {
  const params = new URLSearchParams()
  if (filters.search && filters.search.trim()) {
    params.append('search', filters.search.trim())
  }
  if (filters.status && filters.status !== 'ALL') {
    params.append('status', filters.status)
  }
  if (filters.page) {
    params.append('page', filters.page.toString())
  }
  if (filters.pageSize) {
    params.append('page_size', filters.pageSize.toString())
  }

  const queryString = params.toString() ? `?${params.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/patients${queryString}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch patients (${response.status})`)
  }

  return response.json()
}

export async function fetchPatientById(patientId: string): Promise<PatientRecord> {
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to fetch patient record (${response.status})`)
  }

  return response.json()
}

export async function createPatient(data: PatientFormData): Promise<PatientRecord> {
  const response = await fetch(`${API_URL}/api/v1/patients`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to create patient record (${response.status})`)
  }

  return response.json()
}

export async function updatePatient(
  patientId: string,
  data: Partial<PatientFormData>
): Promise<PatientRecord> {
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Failed to update patient record (${response.status})`)
  }

  return response.json()
}
