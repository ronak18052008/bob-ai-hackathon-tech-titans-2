/**
 * MedBrief AI — Clinical Timeline Domain Types
 * Step 10: Clinical Timeline
 *
 * Types for deterministic chronological timeline, date precision,
 * period grouping, source traceability, and filtering.
 */

export type TimelineDatePrecision =
  | 'EXACT'
  | 'MONTH_YEAR'
  | 'YEAR_ONLY'
  | 'APPROXIMATE'
  | 'UNKNOWN'

export type TimelineEventType =
  | 'consultation'
  | 'diagnosis'
  | 'admission'
  | 'discharge'
  | 'procedure'
  | 'investigation'
  | 'result'
  | 'medication_start'
  | 'medication_stop'
  | 'medication_change'
  | 'follow_up'
  | 'referral'
  | 'other'

export interface TimelineSourceReference {
  document_id?: string | null
  document_name?: string | null
  document_type?: string | null
  page_id?: string | null
  page_number?: number | null
  source_snippet?: string | null
  source_section?: string | null
}

export interface TimelineEventItem {
  id: string
  patient_id: string
  event_type: TimelineEventType | string
  event_type_label: string
  event_type_icon: string
  badge_class: string
  event_date?: string | null
  display_date: string
  date_precision: TimelineDatePrecision | string
  title: string
  description: string
  source: TimelineSourceReference
  confidence?: number | null
  is_conflict: boolean
  conflict_details?: string | null
  is_ai_generated: boolean
  review_status: string
  created_at: string
}

export interface TimelinePeriodGroup {
  period_key: string
  year: number
  month_name?: string | null
  period_label: string
  event_count: number
  events: TimelineEventItem[]
}

export interface TimelineSummaryStats {
  total_events: number
  dated_events_count: number
  undated_events_count: number
  first_event_date?: string | null
  last_event_date?: string | null
  event_types: Record<string, number>
}

export interface PatientTimelineResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  summary: TimelineSummaryStats
  groups: TimelinePeriodGroup[]
  undated_events: TimelineEventItem[]
  items: TimelineEventItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  sort: 'desc' | 'asc' | string
}

export interface RecentTimelineItem {
  id: string
  title: string
  event_type: string
  event_type_label: string
  event_type_icon: string
  display_date: string
  date_precision: string
  description: string
}

export interface PatientTimelineSummaryResponse {
  patient_id: string
  patient_name: string
  patient_mrn: string
  total_events: number
  recent_events: RecentTimelineItem[]
}

export interface TimelineFilterParams {
  event_type?: string
  date_from?: string
  date_to?: string
  search?: string
  sort?: 'desc' | 'asc'
  page?: number
  page_size?: number
}
