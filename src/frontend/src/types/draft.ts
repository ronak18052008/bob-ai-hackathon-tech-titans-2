/**
 * MedBrief AI — Clinical Drafts Type Definitions
 * Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow
 */

export type DraftType = 'REFERRAL' | 'DISCHARGE' | 'HANDOFF'

export type DraftStatus = 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'ARCHIVED'

export interface DraftEvidenceCitation {
  document_id?: string | null
  document_name?: string | null
  page_number?: number | null
  document_page_id?: string | null
  source_snippet: string
  source_section?: string | null
}

export interface DraftStatement {
  statement: string
  citations: DraftEvidenceCitation[]
  is_uncertain: boolean
  uncertainty_note?: string | null
}

export interface StructuredDraftSection {
  section_key: string
  title: string
  content_text?: string | null
  bullet_points: DraftStatement[]
}

export interface StructuredClinicalDraftOutput {
  patient_id: string
  patient_name?: string | null
  draft_type: string
  title: string
  document_body: string
  sections: StructuredDraftSection[]
  overall_evidence_count: number
  has_insufficient_data: boolean
  clinical_notes?: string | null
}

export interface DraftEvidenceReferenceItem {
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

export interface DraftItem {
  id: string
  patient_id: string
  draft_type: string
  draft_type_label: string
  title: string
  status: DraftStatus
  is_ai_generated: boolean
  model_name?: string | null
  model_version?: string | null
  evidence_count: number
  created_at: string
  updated_at: string
}

export interface DraftDetail {
  id: string
  patient_id: string
  patient_name: string
  patient_mrn: string
  draft_type: DraftType
  draft_type_label: string
  title: string
  content: string
  structured_sections: StructuredDraftSection[]
  evidence_references: DraftEvidenceReferenceItem[]
  status: DraftStatus
  is_ai_generated: boolean
  model_name?: string | null
  model_version?: string | null
  created_by?: string | null
  reviewed_by?: string | null
  reviewed_at?: string | null
  created_at: string
  updated_at: string
}

export interface PatientDraftsListResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  items: DraftItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DraftGeneratePayload {
  draft_type: DraftType
  custom_instructions?: string
  recipient_info?: string
}

export interface DraftUpdatePayload {
  title?: string
  content?: string
  status?: DraftStatus
}
