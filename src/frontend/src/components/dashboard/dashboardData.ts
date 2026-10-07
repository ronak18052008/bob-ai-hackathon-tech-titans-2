/**
 * MedBrief AI — Doctor Dashboard Fictional Demo Data
 * Step 5: Doctor Dashboard UI
 *
 * Isolated, strictly synthetic clinical data for UI presentation.
 * Contains NO real patient health information (PHI).
 */

import type {
  DashboardMetric,
  AttentionItem,
  RecentActivityItem,
  RecentRecordItem,
  QuickActionItem,
  IntelligencePreviewItem,
  ClinicalNotification,
} from '../../types/dashboard'

export const DEMO_METRICS: DashboardMetric[] = [
  {
    id: 'active-patients',
    label: 'Active Patients',
    value: 24,
    subtext: 'Assigned to your care team',
    icon: '👥',
    statusType: 'neutral',
  },
  {
    id: 'records-to-review',
    label: 'Records to Review',
    value: 7,
    subtext: 'Unstructured PDFs pending review',
    icon: '📄',
    statusType: 'attention',
  },
  {
    id: 'pending-investigations',
    label: 'Pending Investigations',
    value: 5,
    subtext: 'Ordered diagnostics outstanding',
    icon: '🔬',
    statusType: 'warning',
  },
  {
    id: 'medication-changes',
    label: 'Medication Changes',
    value: 12,
    subtext: 'Detected across latest admissions',
    icon: '💊',
    statusType: 'attention',
  },
  {
    id: 'followups-due',
    label: 'Follow-ups Due',
    value: 3,
    subtext: 'Due within next 7 days',
    icon: '📅',
    statusType: 'warning',
  },
]

export const DEMO_ATTENTION_ITEMS: AttentionItem[] = [
  {
    id: 'att-1',
    category: 'Pending investigation',
    title: 'Outpatient Transthoracic Echocardiogram',
    description: 'Post-NSTEMI left ventricular ejection fraction assessment requested at discharge.',
    patientName: 'Johnathan Doe',
    patientMrn: 'DEMO-MRN-2026-0042',
    date: 'Due in 14 days',
    status: 'Requires clinical review',
    actionLabel: 'Review Order',
  },
  {
    id: 'att-2',
    category: 'Medication change',
    title: 'High-Intensity Statin Up-Titration',
    description: 'Atorvastatin increased from 20mg OD to 40mg OD post-acute coronary event.',
    patientName: 'Johnathan Doe',
    patientMrn: 'DEMO-MRN-2026-0042',
    date: 'Updated 2 days ago',
    status: 'Requires clinical review',
    actionLabel: 'Verify Dosage',
  },
  {
    id: 'att-3',
    category: 'Record requires review',
    title: 'External Cardiology Consultation Note',
    description: '14-page multi-specialty transfer document ingested with 3 new clinical diagnoses.',
    patientName: 'Eleanor Vance',
    patientMrn: 'DEMO-MRN-2026-0089',
    date: 'Uploaded today',
    status: 'Ready for review',
    actionLabel: 'Open Record',
  },
  {
    id: 'att-4',
    category: 'Follow-up due',
    title: 'Post-Discharge Renal Panel & Electrolytes',
    description: 'Scheduled monitoring following ACE-inhibitor initiation during recent admission.',
    patientName: 'Marcus Bennett',
    patientMrn: 'DEMO-MRN-2026-0112',
    date: 'Due in 3 days',
    status: 'Requires clinical review',
    actionLabel: 'Schedule Lab',
  },
  {
    id: 'att-5',
    category: 'Specialist follow-up',
    title: 'Endocrinology Outpatient Referral',
    description: 'Referral drafted for HbA1c optimization following metformin dosage adjustment.',
    patientName: 'Sarah Jenkins',
    patientMrn: 'DEMO-MRN-2026-0056',
    date: 'Draft generated',
    status: 'Pending doctor sign-off',

    actionLabel: 'Review Draft',
  },
]

export const DEMO_RECENT_ACTIVITY: RecentActivityItem[] = [
  {
    id: 'act-1',
    type: 'Document processed',
    patientName: 'Johnathan Doe',
    patientMrn: 'DEMO-MRN-2026-0042',
    summary: 'Discharge Summary (City General Hospital) processed — 2 pages parsed.',
    timestamp: '25 mins ago',
    status: 'Ready',
    icon: '📑',
  },
  {
    id: 'act-2',
    type: 'Medication change',
    patientName: 'Johnathan Doe',
    patientMrn: 'DEMO-MRN-2026-0042',
    summary: 'Atorvastatin 40mg OD verified; Metformin 500mg BD continued.',
    timestamp: '1 hour ago',
    status: 'Processed',
    icon: '💊',
  },
  {
    id: 'act-3',
    type: 'Investigation updated',
    patientName: 'Marcus Bennett',
    patientMrn: 'DEMO-MRN-2026-0112',
    summary: 'Serum Creatinine & eGFR lab pathology result linked to clinical record.',
    timestamp: '3 hours ago',
    status: 'Action Needed',
    icon: '🔬',
  },
  {
    id: 'act-4',
    type: 'Clinical event detected',
    patientName: 'Eleanor Vance',
    patientMrn: 'DEMO-MRN-2026-0089',
    summary: 'Inpatient admission event mapped with primary diagnosis of Heart Failure.',
    timestamp: 'Yesterday',
    status: 'In Review',
    icon: '🏥',
  },
  {
    id: 'act-5',
    type: 'Summary generated',
    patientName: 'Johnathan Doe',
    patientMrn: 'DEMO-MRN-2026-0042',
    summary: 'Quick Clinical Brief drafted for post-NSTEMI review and handoff.',
    timestamp: 'Yesterday',
    status: 'Ready',
    icon: '✨',
  },
]

export const DEMO_RECENT_RECORDS: RecentRecordItem[] = [
  {
    id: 'rec-1',
    patientName: 'Johnathan Doe',
    patientMrn: 'DEMO-MRN-2026-0042',
    recordTitle: 'Discharge_Summary_CityGeneral_20260210.pdf',
    documentType: 'Discharge Summary',
    pageCount: 2,
    lastUpdated: 'Feb 10, 2026',
    status: 'Ready for review',
  },
  {
    id: 'rec-2',
    patientName: 'Eleanor Vance',
    patientMrn: 'DEMO-MRN-2026-0089',
    recordTitle: 'Cardiology_Consult_StMarys_20260208.pdf',
    documentType: 'Consultation Note',
    pageCount: 14,
    lastUpdated: 'Feb 08, 2026',
    status: 'Requires review',
  },
  {
    id: 'rec-3',
    patientName: 'Marcus Bennett',
    patientMrn: 'DEMO-MRN-2026-0112',
    recordTitle: 'Pathology_Comprehensive_Metabolic_20260207.pdf',
    documentType: 'Lab Pathology',
    pageCount: 4,
    lastUpdated: 'Feb 07, 2026',
    status: 'Processing',
  },
  {
    id: 'rec-4',
    patientName: 'Sarah Jenkins',
    patientMrn: 'DEMO-MRN-2026-0056',
    recordTitle: 'Outpatient_Diabetic_Review_20260129.pdf',
    documentType: 'Prescription & Plan',
    pageCount: 6,
    lastUpdated: 'Jan 29, 2026',
    status: 'Completed',
  },
]


export const DEMO_QUICK_ACTIONS: QuickActionItem[] = [
  {
    id: 'qa-patients',
    title: 'View Patients',
    description: 'Browse assigned clinical caseload & patient demographics.',
    icon: '👥',
    targetStep: 'Patient Caseload',
  },
  {
    id: 'qa-upload',
    title: 'Upload Medical Record',
    description: 'Ingest multi-page PDF records, lab reports, or discharge briefs.',
    icon: '📤',
    targetStep: 'EHR Ingestion',
  },
  {
    id: 'qa-investigations',
    title: 'Review Investigations',
    description: 'Audit outstanding labs, imaging orders, and pending diagnostics.',
    icon: '🔬',
    targetStep: 'Diagnostics',
  },
  {
    id: 'qa-medications',
    title: 'Review Medication Changes',
    description: 'Inspect dosage adjustments, new starts, and discontinued drugs.',
    icon: '💊',
    targetStep: 'Medication Intel',
  },
  {
    id: 'qa-summaries',
    title: 'Generate Clinical Summary',
    description: 'Synthesize complex multi-document histories with Gemini AI.',
    icon: '✨',
    targetStep: 'AI Briefings',
  },
]

export const DEMO_INTELLIGENCE_PREVIEWS: IntelligencePreviewItem[] = [
  {
    id: 'prev-timeline',
    title: 'Clinical Timeline',
    tagline: 'Longitudinal Patient Journey',
    description:
      'See the patient’s chronological story across admissions, investigations, diagnoses, and treatment changes on an interactive timeline.',
    icon: '⏳',
    plannedStep: 'Longitudinal Care',
    badge: 'Chronological Context',
  },
  {
    id: 'prev-meds',
    title: 'Medication Changes',
    tagline: 'Drug Reconciliation Intelligence',
    description:
      'Track starts, stops, and dosage modifications across hospital admissions with explicit clinical rationale extracted from notes.',
    icon: '💊',
    plannedStep: 'Pharmacotherapy',
    badge: 'Reconciliation',
  },
  {
    id: 'prev-inv',
    title: 'Outstanding Investigations',
    tagline: 'Proactive Diagnostic Safety',
    description:
      'Identify critical lab investigations, pathology tests, and imaging studies that remain pending, ordered, or require physician follow-up.',
    icon: '🔬',
    plannedStep: 'Diagnostics',
    badge: 'Diagnostic Safety',
  },
  {
    id: 'prev-summary',
    title: 'AI Clinical Summary',
    tagline: 'Doctor-in-the-Loop Briefings',
    description:
      'Generate concise, high-yield clinical briefings from 200+ pages of unstructured medical records, reviewed and signed off by the physician.',
    icon: '✨',
    plannedStep: 'Gemini AI',
    badge: 'Grounded Briefs',
  },
  {
    id: 'prev-evidence',
    title: 'Evidence & Sources',
    tagline: 'Verifiable Document Citations',
    description:
      'Trace every single AI-highlighted diagnosis, medication change, and clinical finding back to the exact source document and page number.',
    icon: '🔍',
    plannedStep: 'Traceability',
    badge: 'Zero Hallucination',
  },
]


export const DEMO_NOTIFICATIONS: ClinicalNotification[] = [
  {
    id: 'notif-1',
    title: 'New record uploaded for Johnathan Doe',
    category: 'Document Ingestion',
    patientRef: 'DEMO-MRN-2026-0042',
    timestamp: '15m ago',
    isRead: false,
  },
  {
    id: 'notif-2',
    title: 'Medication change detected: Atorvastatin up-titrated',
    category: 'Medication Safety',
    patientRef: 'DEMO-MRN-2026-0042',
    timestamp: '1h ago',
    isRead: false,
  },
  {
    id: 'notif-3',
    title: 'Outpatient echocardiogram order pending verification',
    category: 'Investigation Order',
    patientRef: 'DEMO-MRN-2026-0042',
    timestamp: '3h ago',
    isRead: true,
  },
]
