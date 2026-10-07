/**
 * MedBrief AI — Doctor Dashboard Types
 * Step 5: Doctor Dashboard UI
 */

export interface DashboardMetric {
  id: string
  label: string
  value: number | string
  subtext: string
  icon: string
  trend?: string
  statusType?: 'neutral' | 'attention' | 'positive' | 'warning'
}

export type AttentionCategory =
  | 'Pending investigation'
  | 'Follow-up due'
  | 'Medication change'
  | 'Record requires review'
  | 'Specialist follow-up'
  | 'Documentation / handoff'

export interface AttentionItem {
  id: string
  category: AttentionCategory
  title: string
  description: string
  patientName: string
  patientMrn: string
  date: string
  status: string
  actionLabel: string
}

export type ActivityType =
  | 'New record'
  | 'Document processed'
  | 'Clinical event detected'
  | 'Medication change'
  | 'Investigation updated'
  | 'Summary generated'

export interface RecentActivityItem {
  id: string
  type: ActivityType
  patientName: string
  patientMrn: string
  summary: string
  timestamp: string
  status: 'Ready' | 'In Review' | 'Processed' | 'Action Needed'
  icon: string
}

export type RecordStatus = 'Ready for review' | 'Processing' | 'Requires review' | 'Completed'

export interface RecentRecordItem {
  id: string
  patientName: string
  patientMrn: string
  recordTitle: string
  documentType: string
  pageCount: number
  lastUpdated: string
  status: RecordStatus
}

export interface QuickActionItem {
  id: string
  title: string
  description: string
  icon: string
  targetStep: string
}

export interface IntelligencePreviewItem {
  id: string
  title: string
  tagline: string
  description: string
  icon: string
  plannedStep: string
  badge: string
}

export interface ClinicalNotification {
  id: string
  title: string
  category: string
  patientRef: string
  timestamp: string
  isRead: boolean
}
