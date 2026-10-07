/**
 * MedBrief AI — Document Ingestion API Client
 * Step 7: PDF / Medical Document Upload & Ingestion Foundation
 *
 * Provides REST interactions for:
 * - Multipart PDF uploads with genuine progress tracking (XHR upload event)
 * - Document directory queries (scoped to patient or caseload)
 * - Document metadata resolution
 * - Authenticated PDF blob streaming for private preview & download
 * - Processing job retry execution
 */

import type {
  DocumentRecord,
  DocumentListResponse,
  DocumentFilters,
  DocumentExtractionSummary,
  DocumentExtractionTriggerResult,
} from '../types/document'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'medbrief_clinical_token'

function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export function uploadDocument(
  patientId: string,
  file: File,
  documentType: string,
  onProgress?: (percent: number) => void
): Promise<DocumentRecord> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const url = `${API_URL}/api/v1/patients/${patientId}/documents`

    xhr.open('POST', url)

    const token = getAuthToken()
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100)
          onProgress(percentComplete)
        }
      }
    }

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText || '{}')
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as DocumentRecord)
        } else {
          const errorMsg = body.detail || `Upload failed (HTTP ${xhr.status})`
          reject(new Error(errorMsg))
        }
      } catch {
        reject(new Error(`Server error during upload (HTTP ${xhr.status})`))
      }
    }

    xhr.onerror = () => {
      reject(new Error('Network error occurred while transmitting document.'))
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', documentType)

    xhr.send(formData)
  })
}

export async function fetchPatientDocuments(patientId: string): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_URL}/api/v1/patients/${patientId}/documents`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to fetch patient documents (${response.status})`)
  }

  return response.json()
}

export async function fetchAllDocuments(filters: DocumentFilters = {}): Promise<DocumentListResponse> {
  const params = new URLSearchParams()
  if (filters.patient_id) params.append('patient_id', filters.patient_id)
  if (filters.document_type && filters.document_type !== 'ALL') params.append('document_type', filters.document_type)
  if (filters.status && filters.status !== 'ALL') params.append('status', filters.status)
  if (filters.search && filters.search.trim()) params.append('search', filters.search.trim())
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString() ? `?${params.toString()}` : ''
  const response = await fetch(`${API_URL}/api/v1/documents${queryString}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to fetch documents directory (${response.status})`)
  }

  return response.json()
}

export async function fetchDocumentDetails(documentId: string): Promise<DocumentRecord> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to fetch document metadata (${response.status})`)
  }

  return response.json()
}

export async function streamDocumentBlob(documentId: string): Promise<{ blob: Blob; filename: string }> {
  const token = getAuthToken()
  const headers: HeadersInit = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/file`, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Unable to access medical file binary (${response.status})`)
  }

  const disposition = response.headers.get('Content-Disposition') || ''
  let filename = 'document.pdf'
  const match = disposition.match(/filename="?([^"]+)"?/)
  if (match && match[1]) {
    filename = match[1]
  }

  const blob = await response.blob()
  return { blob, filename }
}

export async function retryDocumentProcessing(documentId: string): Promise<DocumentRecord> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/retry`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to retry document processing (${response.status})`)
  }

  const data = await response.json()
  return data.document
}

export async function triggerDocumentExtraction(documentId: string): Promise<DocumentExtractionTriggerResult> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/extract`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    const detail = typeof err.detail === 'string' ? err.detail : err.detail?.message || 'Extraction failed'
    throw new Error(detail || `Failed to initiate medical extraction (${response.status})`)
  }

  return response.json()
}

export async function fetchDocumentExtraction(documentId: string): Promise<DocumentExtractionSummary> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/extraction`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    const detail = typeof err.detail === 'string' ? err.detail : err.detail?.message || 'Failed to fetch extraction'
    throw new Error(detail || `Failed to retrieve extraction dossier (${response.status})`)
  }

  return response.json()
}
