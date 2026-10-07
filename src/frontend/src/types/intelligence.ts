/**
 * MedBrief AI — Clinical Intelligence TypeScript Contracts
 * Step 11: Medication + Investigation Intelligence
 *
 * Types for structured medications, medication change detection,
 * diagnostic investigations, and outstanding clinical items.
 */

export interface IntelligenceSourceReference {
  document_id?: string | null
  document_name?: string | null
  document_type?: string | null
  page_id?: string | null
  page_number?: number | null
  source_snippet?: string | null
  source_section?: string | null
}

// 1. Medication Types
export type MedicationStatus = 'ACTIVE' | 'STOPPED' | 'HISTORICAL' | 'UNKNOWN'
export type MedicationChangeType =
  | 'STARTED'
  | 'STOPPED'
  | 'DOSE_CHANGED'
  | 'FREQUENCY_CHANGED'
  | 'ROUTE_CHANGED'
  | 'OTHER'

export interface MedicationItem {
  id: string
  patient_id: string
  medication_name: string
  generic_name?: string | null
  dosage?: string | null
  dose_unit?: string | null
  route?: string | null
  frequency?: string | null
  status: MedicationStatus | string
  start_date?: string | null
  end_date?: string | null
  display_start_date: string
  display_end_date?: string | null
  source: IntelligenceSourceReference
  origin: 'DOCUMENTED' | 'DERIVED' | string
  is_conflict: boolean
  conflict_details?: string | null
  changes_count: number
  created_at: string
}

export interface MedicationSummaryStats {
  total_medications: number
  active_count: number
  stopped_count: number
  historical_count: number
  unknown_count: number
}

export interface PatientMedicationsResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  summary: MedicationSummaryStats
  items: MedicationItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  message?: string | null
}

// 2. Medication Changes Types
export interface MedicationChangeItem {
  id: string
  medication_id: string
  medication_name: string
  generic_name?: string | null
  change_type: MedicationChangeType | string
  change_type_label: string
  previous_value?: string | null
  new_value?: string | null
  change_date?: string | null
  display_date: string
  description: string
  reason?: string | null
  origin: 'DOCUMENTED' | 'DERIVED' | string
  is_conflict: boolean
  conflict_details?: string | null
  is_ai_generated: boolean
  source: IntelligenceSourceReference
  created_at: string
}

export interface MedicationChangeSummaryStats {
  total_changes: number
  started_count: number
  stopped_count: number
  dose_changes_count: number
  frequency_changes_count: number
  route_changes_count: number
}

export interface PatientMedicationChangesResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  summary: MedicationChangeSummaryStats
  items: MedicationChangeItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  message?: string | null
}

// 3. Investigation Types
export type InvestigationStatus = 'ORDERED' | 'PENDING' | 'COMPLETED' | 'CANCELLED' | 'UNKNOWN'
export type ClinicalUrgency = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL'

export interface InvestigationItem {
  id: string
  patient_id: string
  investigation_name: string
  investigation_type: string
  ordered_date?: string | null
  completed_date?: string | null
  display_date: string
  status: InvestigationStatus | string
  result_summary?: string | null
  reference_range?: string | null
  is_abnormal: boolean
  clinical_urgency: ClinicalUrgency | string
  origin: 'DOCUMENTED' | 'DERIVED' | string
  is_conflict: boolean
  conflict_details?: string | null
  source: IntelligenceSourceReference
  created_at: string
}

export interface InvestigationSummaryStats {
  total_investigations: number
  completed_count: number
  pending_count: number
  ordered_count: number
  cancelled_count: number
  unknown_count: number
  abnormal_count: number
}

export interface PatientInvestigationsResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  summary: InvestigationSummaryStats
  items: InvestigationItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  message?: string | null
}

// 4. Outstanding Items Types
export type OutstandingItemType =
  | 'PENDING_INVESTIGATION'
  | 'FOLLOW_UP'
  | 'MEDICATION_REVIEW'
  | 'SPECIALIST_FOLLOW_UP'
  | 'MONITORING'
  | 'DOCUMENTATION'
  | 'OTHER'

export type OutstandingStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'DISMISSED'

export interface OutstandingItem {
  id: string
  patient_id: string
  item_type: OutstandingItemType | string
  item_type_label: string
  title: string
  description?: string | null
  priority: ClinicalUrgency | string
  status: OutstandingStatus | string
  due_date?: string | null
  display_due_date: string
  origin: 'DOCUMENTED' | 'AI_EXTRACTED' | string
  is_ai_generated: boolean
  review_status: string
  source: IntelligenceSourceReference
  created_at: string
}

export interface OutstandingSummaryStats {
  total_outstanding: number
  open_count: number
  high_priority_count: number
  type_counts: Record<string, number>
}

export interface PatientOutstandingItemsResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  summary: OutstandingSummaryStats
  items: OutstandingItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  message?: string | null
}

// 5. Combined Overview Summary Type
export interface PatientIntelligenceSummaryResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  medications: {
    total_count: number
    active_count: number
    changes_count: number
    recent_changes: MedicationChangeItem[]
  }
  investigations: {
    total_count: number
    completed_count: number
    pending_count: number
    abnormal_count: number
    recent_pending: InvestigationItem[]
  }
  outstanding_items: {
    open_count: number
    recent_items: OutstandingItem[]
  }
}
