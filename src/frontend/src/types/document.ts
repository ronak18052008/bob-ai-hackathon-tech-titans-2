/**
 * MedBrief AI — Document Ingestion TypeScript Contracts
 * Step 7: PDF / Medical Document Upload & Ingestion Foundation
 */

export type DocumentStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'PROCESSED'
  | 'FAILED'
  | 'PARTIAL'
  | 'REQUIRES_REVIEW'
  | 'ARCHIVED'

export type ClinicalDocumentType =
  | 'DISCHARGE_SUMMARY'
  | 'CLINIC_CONSULTATION'
  | 'LAB_PATHOLOGY'
  | 'RADIOLOGY_REPORT'
  | 'PRESCRIPTION'
  | 'REFERRAL_LETTER'
  | 'OTHER'

export interface DocumentRecord {
  id: string
  patient_id: string
  patient_name?: string | null
  patient_mrn?: string | null
  uploaded_by?: string | null
  uploader_name?: string | null
  file_name: string
  file_type: string
  document_type: ClinicalDocumentType
  file_size: number
  page_count: number
  checksum_sha256?: string | null
  status: DocumentStatus
  uploaded_at: string
  created_at: string
  updated_at: string
  job_id?: string | null
  job_status?: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | null
  job_progress?: number
  job_error?: string | null
}

export interface DocumentListResponse {
  items: DocumentRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DocumentFilters {
  patient_id?: string
  document_type?: string
  status?: string
  search?: string
  page?: number
  page_size?: number
}

// ── Step 9: Medical Extraction Contracts ──────────────────────────────────────

export interface ExtractionCountSummary {
  events: number
  conditions: number
  medications: number
  investigations: number
  procedures: number
  follow_ups: number
  total: number
}

export interface ExtractedEventItem {
  id: string
  event_type: string
  event_date?: string | null
  event_date_precision: string
  title: string
  description: string
  confidence?: number | null
  is_conflict: boolean
  conflict_details?: string | null
  source_page_id?: string | null
  evidence_snippet?: string | null
}

export interface ExtractedMedicationItem {
  id: string
  medication_name: string
  generic_name?: string | null
  dosage?: string | null
  dose_unit?: string | null
  route?: string | null
  frequency?: string | null
  status: string
  start_date?: string | null
  end_date?: string | null
  source_page_id?: string | null
  evidence_snippet?: string | null
}

export interface ExtractedInvestigationItem {
  id: string
  investigation_name: string
  investigation_type: string
  ordered_date?: string | null
  completed_date?: string | null
  status: string
  result_summary?: string | null
  reference_range?: string | null
  is_abnormal?: boolean | null
  clinical_urgency: string
  source_page_id?: string | null
  evidence_snippet?: string | null
}

export interface ExtractedFollowUpItem {
  id: string
  item_type: string
  title: string
  description?: string | null
  priority: string
  status: string
  due_date?: string | null
  source_page_id?: string | null
  evidence_snippet?: string | null
}

export interface DocumentExtractionSummary {
  document_id: string
  patient_id: string
  document_status: string
  job_id?: string | null
  job_status?: string | null
  job_progress: number
  job_error?: string | null
  counts: ExtractionCountSummary
  events: ExtractedEventItem[]
  conditions: ExtractedEventItem[]
  procedures: ExtractedEventItem[]
  medications: ExtractedMedicationItem[]
  investigations: ExtractedInvestigationItem[]
  follow_ups: ExtractedFollowUpItem[]
}

export interface DocumentExtractionTriggerResult {
  status: string
  message: string
  document_id: string
  patient_id: string
  job_id: string
  job_status: string
  processed_pages: number
  total_pages: number
  failed_pages: number[]
  extracted_counts: Record<string, number>
}
