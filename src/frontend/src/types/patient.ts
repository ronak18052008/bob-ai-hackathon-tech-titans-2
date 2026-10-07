/**
 * MedBrief AI — Patient Management TypeScript Contracts
 * Step 6: Patient Management
 *
 * Types for patient directory listing, pagination, creation, updating,
 * and clinical overview shell.
 */

export type PatientStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED' | 'DECEASED'

export interface PatientRecord {
  id: string
  mrn: string
  first_name: string
  last_name: string
  date_of_birth: string | null
  gender: string | null
  contact_phone: string | null
  status: PatientStatus
  created_by: string | null
  created_at: string
  updated_at: string
  access_role?: string
  document_count: number
  last_document_date: string | null
}

export interface PatientListResponse {
  items: PatientRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PatientFormData {
  first_name: string
  last_name: string
  mrn?: string
  date_of_birth?: string
  gender?: string
  contact_phone?: string
  status?: PatientStatus
}

export interface PatientFilters {
  search?: string
  status?: string
  page?: number
  pageSize?: number
}
