/**
 * MedBrief AI — AI Clinical Summary & Evidence Type Definitions
 * Step 12: AI Clinical Summary + Evidence/Source Reference Layer
 */

export type SummaryType = 'QUICK_CLINICAL' | 'DETAILED_CLINICAL' | 'MEDICATION' | 'INVESTIGATION'

export type SummaryStatus = 'DRAFT' | 'GENERATED' | 'REVIEWED' | 'APPROVED' | 'ARCHIVED'

export interface SummaryEvidenceCitation {
  document_id?: string | null
  document_name?: string | null
  page_number?: number | null
  document_page_id?: string | null
  source_snippet: string
  source_section?: string | null
}

export interface SummaryStatement {
  statement: string
  citations: SummaryEvidenceCitation[]
  is_uncertain: boolean
  uncertainty_note?: string | null
}

export interface StructuredSummarySection {
  section_key: string
  title: string
  summary_text?: string | null
  bullet_points: SummaryStatement[]
}

export interface StructuredClinicalSummaryOutput {
  patient_id: string
  patient_name?: string | null
  summary_type: string
  title: string
  overview: string
  sections: StructuredSummarySection[]
  overall_evidence_count: number
  has_insufficient_data: boolean
  generation_notes?: string | null
}

export interface EvidenceReferenceItem {
  id: string
  patient_id: string
  document_id: string
  document_name?: string | null
  document_page_id?: string | null
  page_number?: number | null
  parent_entity_type: string
  parent_entity_id: string
  source_section?: string | null
  source_text: string
  source_type: string
  confidence?: number | null
  created_at: string
}

export interface SummaryItem {
  id: string
  patient_id: string
  summary_type: string
  summary_type_label: string
  title: string
  status: string
  is_ai_generated: boolean
  model_name?: string | null
  model_version?: string | null
  evidence_count: number
  created_at: string
  updated_at: string
}

export interface SummaryDetail {
  id: string
  patient_id: string
  patient_name: string
  patient_mrn: string
  summary_type: string
  summary_type_label: string
  title: string
  overview: string
  structured_content: StructuredClinicalSummaryOutput
  evidence_references: EvidenceReferenceItem[]
  status: string
  is_ai_generated: boolean
  model_name?: string | null
  model_version?: string | null
  created_at: string
  updated_at: string
}

export interface PatientSummariesListResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  items: SummaryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
