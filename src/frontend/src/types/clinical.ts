/**
 * MedBrief AI — TypeScript Domain Contracts
 * Step 2: System Architecture
 *
 * Establishes strict type safety mirroring backend domain schemas.
 */

export type UserRole = 'DOCTOR' | 'NURSE' | 'ADMIN'

export interface UserProfile {
  id: string
  email: string
  fullName: string
  role: UserRole
  medicalLicenseId?: string
  createdAt: string
}

export interface PatientDemographics {
  id: string
  mrn: string
  firstName: string
  lastName: string
  dateOfBirth: string
  gender: string
  contactPhone?: string
  assignedDoctorId?: string
  createdAt: string
}

export type EpistemicCategory =
  | 'DOCUMENTED_FACT'
  | 'AI_INTERPRETATION'
  | 'AI_SUGGESTION'
  | 'UNCERTAIN'
  | 'CONFLICTING'

export interface EvidenceReference {
  documentId: string
  documentTitle: string
  pageNumber: number
  section?: string
  exactSnippet: string
  characterOffset?: [number, number]
  confidenceScore: number
  category: EpistemicCategory
}

export type DocumentType =
  | 'DISCHARGE_SUMMARY'
  | 'CLINIC_CONSULTATION'
  | 'LAB_PATHOLOGY'
  | 'RADIOLOGY_REPORT'
  | 'PRESCRIPTION'
  | 'REFERRAL_LETTER'
  | 'OTHER'

export type JobStatus =
  | 'QUEUED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'PARTIAL'
  | 'REQUIRES_REVIEW'

export interface MedicalDocumentMeta {
  id: string
  patientId: string
  title: string
  documentType: DocumentType
  pageCount: number
  fileSizeBytes: number
  checksumSha256: string
  uploadedAt: string
}

export interface ProcessingJob {
  id: string
  documentId: string
  status: JobStatus
  progressPercentage: number
  totalPages: number
  processedPages: number
  errorMessage?: string
  startedAt?: string
  completedAt?: string
}

export type ClinicalEventType =
  | 'CONSULTATION'
  | 'ADMISSION'
  | 'DISCHARGE'
  | 'PROCEDURE'
  | 'DIAGNOSIS'
  | 'MEDICATION_CHANGE'
  | 'INVESTIGATION_RESULT'

export interface ClinicalEvent {
  id: string
  patientId: string
  eventType: ClinicalEventType
  eventDate?: string
  approximateDate?: string
  title: string
  description: string
  isConflict: boolean
  conflictNotes?: string
  evidence: EvidenceReference[]
}

export type MedicationChangeType =
  | 'STARTED'
  | 'STOPPED'
  | 'DOSE_INCREASED'
  | 'DOSE_DECREASED'
  | 'FREQUENCY_CHANGED'
  | 'SUBSTITUTED'

export interface MedicationItem {
  id: string
  patientId: string
  drugName: string
  dosage: string
  frequency: string
  route: string
  isActive: boolean
  evidence: EvidenceReference[]
}

export interface MedicationChangeRecord {
  id: string
  medicationId: string
  drugName: string
  changeType: MedicationChangeType
  previousDosage?: string
  newDosage?: string
  reason?: string
  recordedDate?: string
  evidence: EvidenceReference[]
}

export type InvestigationStatus =
  | 'COMPLETED'
  | 'ORDERED_PENDING'
  | 'RECOMMENDED_NEXT_STEP'
  | 'OVERDUE'

export interface InvestigationItem {
  id: string
  patientId: string
  testName: string
  category: string
  status: InvestigationStatus
  resultValue?: string
  referenceRange?: string
  isAbnormal?: boolean
  orderedDate?: string
  completedDate?: string
  clinicalUrgency: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL'
  evidence: EvidenceReference[]
}

export type SummaryMode =
  | 'QUICK_BRIEF'
  | 'DETAILED_SYSTEMIC'
  | 'MEDICATION_FOCUSED'
  | 'INVESTIGATIONS_FOCUSED'
  | 'HANDOFF_SBAR'

export interface ClinicalSummary {
  id: string
  patientId: string
  mode: SummaryMode
  generatedAt: string
  contentMarkdown: string
  doctorApproved: boolean
  reviewedBy?: string
  reviewedAt?: string
  evidenceCitations: EvidenceReference[]
}

export type DraftType =
  | 'SPECIALIST_REFERRAL'
  | 'DISCHARGE_SUMMARY'
  | 'CLINICAL_HANDOFF'

export interface ClinicalDraft {
  id: string
  patientId: string
  draftType: DraftType
  title: string
  aiGeneratedBody: string
  doctorEditedBody?: string
  isSignedOff: boolean
  signedBy?: string
  signedAt?: string
  evidenceCitations: EvidenceReference[]
}
