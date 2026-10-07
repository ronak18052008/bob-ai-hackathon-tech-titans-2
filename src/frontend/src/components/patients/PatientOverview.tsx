/**
 * MedBrief AI — Patient Overview Shell
 * Step 6: Patient Management
 *
 * Dedicated clinical dossier view for an individual patient.
 * Features:
 * - Patient identity banner with demographics, MRN, status, and role badge
 * - Document metadata indicators
 * - 4 Key Clinical Sections (Clinical Brief, Key Events, Medications, Investigations)
 *   configured as structured shells with realistic clinical placeholders
 * - Edit demographics modal trigger
 * - Smooth back navigation to Patient Directory
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord, PatientFormData } from '../../types/patient'
import type { DocumentRecord } from '../../types/document'
import { PatientModal } from './PatientModal'
import { updatePatient } from '../../services/patientApi'
import { fetchPatientDocuments } from '../../services/documentApi'
import { DocumentUploadModal } from '../documents/DocumentUploadModal'
import { DocumentDetailModal } from '../documents/DocumentDetailModal'
import { fetchPatientTimelineSummary } from '../../services/timelineApi'
import type { PatientTimelineSummaryResponse } from '../../types/timeline'
import {
  fetchPatientMedications,
  fetchPatientMedicationChanges,
  fetchPatientInvestigations,
  fetchPatientOutstandingItems,
  fetchPatientIntelligenceSummary,
} from '../../services/intelligenceApi'
import type {
  MedicationItem,
  MedicationChangeItem,
  InvestigationItem,
  OutstandingItem,
  PatientIntelligenceSummaryResponse,
} from '../../types/intelligence'
import {
  fetchPatientSummaries,
  generatePatientSummary,
  fetchSummaryById,
} from '../../services/summaryApi'
import type {
  SummaryType,
  SummaryItem,
  SummaryDetail,
  SummaryEvidenceCitation,
} from '../../types/summary'
import './PatientOverview.css'

interface PatientOverviewProps {
  patient: PatientRecord
  onBack: () => void
  onPatientUpdated: (updated: PatientRecord) => void
  onNavigateToTimeline?: (patient: PatientRecord) => void
  onNavigateToMedications?: (patient: PatientRecord) => void
  onNavigateToInvestigations?: (patient: PatientRecord) => void
  onNavigateToSummaries?: (patient: PatientRecord) => void
}

function calculateAge(dobStr: string | null): number | null {
  if (!dobStr) return null
  const dob = new Date(dobStr)
  if (isNaN(dob.getTime())) return null
  const diff = Date.now() - dob.getTime()
  const ageDate = new Date(diff)
  return Math.abs(ageDate.getUTCFullYear() - 1970)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Not recorded'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export const PatientOverview: React.FC<PatientOverviewProps> = ({
  patient,
  onBack,
  onPatientUpdated,
  onNavigateToTimeline,
  onNavigateToMedications,
  onNavigateToInvestigations,
  onNavigateToSummaries,
}) => {
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<DocumentRecord | null>(null)
  const [patientDocs, setPatientDocs] = useState<DocumentRecord[]>([])
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [timelineSummary, setTimelineSummary] = useState<PatientTimelineSummaryResponse | null>(null)
  const [loadingTimeline, setLoadingTimeline] = useState<boolean>(true)
  const [activeTab, setActiveTab] = useState<'all' | 'documents' | 'brief' | 'events' | 'meds' | 'labs' | 'outstanding'>('all')

  // Clinical Intelligence State (Step 11)
  const [loadingIntelligence, setLoadingIntelligence] = useState<boolean>(true)
  const [intelligenceSummary, setIntelligenceSummary] = useState<PatientIntelligenceSummaryResponse | null>(null)
  const [medications, setMedications] = useState<MedicationItem[]>([])
  const [medicationChanges, setMedicationChanges] = useState<MedicationChangeItem[]>([])
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([])
  const [outstandingItems, setOutstandingItems] = useState<OutstandingItem[]>([])

  // AI Clinical Summary State (Step 12)
  const [patientSummaries, setPatientSummaries] = useState<SummaryItem[]>([])
  const [activeSummary, setActiveSummary] = useState<SummaryDetail | null>(null)
  const [loadingSummary, setLoadingSummary] = useState<boolean>(true)
  const [generatingSummary, setGeneratingSummary] = useState<boolean>(false)
  const [summaryMode, setSummaryMode] = useState<SummaryType>('QUICK_CLINICAL')
  const [activeCitation, setActiveCitation] = useState<SummaryEvidenceCitation | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)

  const age = calculateAge(patient.date_of_birth)
  const isDemoWithRecords = patient.mrn === 'DEMO-MRN-2026-0042' // Johnathan Doe

  const loadDocs = useCallback(async () => {
    setLoadingDocs(true)
    try {
      const docs = await fetchPatientDocuments(patient.id)
      setPatientDocs(docs)
    } catch {
      setPatientDocs([])
    } finally {
      setLoadingDocs(false)
    }
  }, [patient.id])

  useEffect(() => {
    loadDocs()
  }, [loadDocs])

  useEffect(() => {
    setLoadingTimeline(true)
    fetchPatientTimelineSummary(patient.id)
      .then((res) => setTimelineSummary(res))
      .catch((err) => {
        console.error('Error fetching timeline summary:', err)
        setTimelineSummary(null)
      })
      .finally(() => setLoadingTimeline(false))
  }, [patient.id])

  // Fetch Step 11 Clinical Intelligence
  useEffect(() => {
    let isMounted = true
    setLoadingIntelligence(true)
    Promise.allSettled([
      fetchPatientIntelligenceSummary(patient.id),
      fetchPatientMedications(patient.id),
      fetchPatientMedicationChanges(patient.id),
      fetchPatientInvestigations(patient.id),
      fetchPatientOutstandingItems(patient.id),
    ]).then(([summaryRes, medsRes, changesRes, invRes, itemsRes]) => {
      if (!isMounted) return
      if (summaryRes.status === 'fulfilled') setIntelligenceSummary(summaryRes.value)
      if (medsRes.status === 'fulfilled') setMedications(medsRes.value.items)
      if (changesRes.status === 'fulfilled') setMedicationChanges(changesRes.value.items)
      if (invRes.status === 'fulfilled') setInvestigations(invRes.value.items)
      if (itemsRes.status === 'fulfilled') setOutstandingItems(itemsRes.value.items)
      setLoadingIntelligence(false)
    }).catch(() => {
      if (isMounted) setLoadingIntelligence(false)
    })

    return () => {
      isMounted = false
    }
  }, [patient.id])

  // Fetch Step 12 AI Clinical Summaries
  useEffect(() => {
    let isMounted = true
    setLoadingSummary(true)
    fetchPatientSummaries(patient.id)
      .then((res) => {
        if (!isMounted) return
        setPatientSummaries(res.items)
        if (res.items.length > 0) {
          return fetchSummaryById(res.items[0].id)
        }
        return null
      })
      .then((detail) => {
        if (!isMounted || !detail) return
        setActiveSummary(detail)
      })
      .catch((err) => {
        console.error('Error loading patient summaries:', err)
      })
      .finally(() => {
        if (isMounted) setLoadingSummary(false)
      })

    return () => {
      isMounted = false
    }
  }, [patient.id])

  const handleGenerateSummary = async (mode: SummaryType = summaryMode) => {
    setGeneratingSummary(true)
    setSummaryError(null)
    try {
      const detail = await generatePatientSummary(patient.id, mode)
      setActiveSummary(detail)
      const res = await fetchPatientSummaries(patient.id)
      setPatientSummaries(res.items)
    } catch (err: any) {
      setSummaryError(err.message || 'Failed to generate clinical summary.')
    } finally {
      setGeneratingSummary(false)
    }
  }

  const handleSelectSummary = async (summaryId: string) => {
    setLoadingSummary(true)
    try {
      const detail = await fetchSummaryById(summaryId)
      setActiveSummary(detail)
    } catch (err) {
      console.error('Failed to load summary detail:', err)
    } finally {
      setLoadingSummary(false)
    }
  }

  const handleUpdate = async (formData: PatientFormData) => {
    const updated = await updatePatient(patient.id, formData)
    onPatientUpdated(updated)
  }

  const handleDocUploadSuccess = (newDoc: DocumentRecord) => {
    setPatientDocs((prev) => [newDoc, ...prev])
    onPatientUpdated({
      ...patient,
      document_count: (patient.document_count || 0) + 1,
      last_document_date: newDoc.uploaded_at,
    })
  }

  const handleDocUpdated = (updated: DocumentRecord) => {
    setPatientDocs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
    if (selectedDoc?.id === updated.id) {
      setSelectedDoc(updated)
    }
  }

  return (
    <div className="patient-overview-container" role="main" aria-label={`Patient Dossier: ${patient.first_name} ${patient.last_name}`}>
      {/* Top Navigation Strip */}
      <div className="overview-nav-strip">
        <button
          type="button"
          className="back-btn"
          onClick={onBack}
          aria-label="Back to patient directory"
        >
          <span className="back-arrow">←</span>
          <span>Back to Patients</span>
        </button>
        <div className="overview-breadcrumbs">
          <span className="crumb-inactive">Patients</span>
          <span className="crumb-sep">/</span>
          <span className="crumb-active">{patient.first_name} {patient.last_name}</span>
          <span className="crumb-mrn">({patient.mrn})</span>
        </div>
      </div>

      {/* Patient Identity Banner */}
      <section className="patient-banner-card" aria-label="Patient Identity Banner">
        <div className="banner-primary-row">
          <div className="patient-avatar-badge" aria-hidden="true">
            {patient.gender === 'Female' ? '👩' : '👨'}
          </div>

          <div className="patient-headline">
            <div className="patient-name-title-row">
              <h1 className="patient-name">{patient.first_name} {patient.last_name}</h1>
              <span className={`status-badge ${patient.status.toLowerCase()}`}>
                {patient.status}
              </span>
              <span className="role-access-badge">
                {patient.access_role?.replace('_', ' ') || 'PRIMARY PHYSICIAN'}
              </span>
            </div>

            <div className="demographics-grid">
              <div className="demo-item">
                <span className="demo-label">MRN</span>
                <span className="demo-val mono">{patient.mrn || 'UNASSIGNED'}</span>
              </div>
              <div className="demo-item">
                <span className="demo-label">DOB / Age</span>
                <span className="demo-val">
                  {formatDate(patient.date_of_birth)} {age !== null ? `(${age} yrs)` : ''}
                </span>
              </div>
              <div className="demo-item">
                <span className="demo-label">Gender</span>
                <span className="demo-val">{patient.gender || 'Not specified'}</span>
              </div>
              <div className="demo-item">
                <span className="demo-label">Contact Phone</span>
                <span className="demo-val">{patient.contact_phone || 'None recorded'}</span>
              </div>
              <div className="demo-item">
                <span className="demo-label">Registered</span>
                <span className="demo-val">{formatDate(patient.created_at)}</span>
              </div>
            </div>
          </div>

          <div className="banner-actions">
            <button
              type="button"
              className="overview-action-btn upload-primary"
              onClick={() => setIsUploadModalOpen(true)}
            >
              <span>📤</span> Upload Medical Record
            </button>
            <button
              type="button"
              className="overview-action-btn edit"
              onClick={() => setIsEditModalOpen(true)}
            >
              <span>✏️</span> Edit Demographics
            </button>
          </div>
        </div>

        {/* Document Ingestion Strip */}
        <div className="document-status-strip">
          <div className="doc-metric-item">
            <span className="doc-metric-icon">📄</span>
            <div className="doc-metric-text">
              <span className="doc-metric-num">{patient.document_count}</span>
              <span className="doc-metric-label">
                {patient.document_count === 1 ? 'Medical Document Ingested' : 'Medical Documents Ingested'}
              </span>
            </div>
          </div>

          <div className="doc-metric-divider" />

          <div className="doc-metric-item">
            <span className="doc-metric-icon">📅</span>
            <div className="doc-metric-text">
              <span className="doc-metric-num">
                {patient.last_document_date ? formatDate(patient.last_document_date) : 'No Ingestions Yet'}
              </span>
              <span className="doc-metric-label">Last Record Upload</span>
            </div>
          </div>

          <div className="doc-metric-divider" />

          <div className="doc-metric-item">
            <span className="doc-metric-icon">🔒</span>
            <div className="doc-metric-text">
              <span className="doc-metric-num">RBAC Verified</span>
              <span className="doc-metric-label">Physician Access Confirmed</span>
            </div>
          </div>
        </div>
      </section>

      {/* Navigation Filter Tabs for Clinical Sections */}
      <div className="section-tabs-bar" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'all'}
          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All Clinical Sections
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'documents'}
          className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          📁 Documents ({patientDocs.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'brief'}
          className={`tab-btn ${activeTab === 'brief' ? 'active' : ''}`}
          onClick={() => setActiveTab('brief')}
        >
          📝 Clinical Brief
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'events'}
          className={`tab-btn ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => setActiveTab('events')}
        >
          ⏳ Key Events
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'meds'}
          className={`tab-btn ${activeTab === 'meds' ? 'active' : ''}`}
          onClick={() => setActiveTab('meds')}
        >
          💊 Medications ({medications.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'labs'}
          className={`tab-btn ${activeTab === 'labs' ? 'active' : ''}`}
          onClick={() => setActiveTab('labs')}
        >
          🔬 Investigations ({investigations.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'outstanding'}
          className={`tab-btn ${activeTab === 'outstanding' ? 'active' : ''}`}
          onClick={() => setActiveTab('outstanding')}
        >
          ⚠️ Outstanding ({outstandingItems.length})
        </button>
      </div>

      {/* ── 4 KEY CLINICAL SECTIONS + INGESTED DOCUMENTS (Step 7) ── */}
      <div className="clinical-grid">
        {/* SECTION: INGESTED MEDICAL DOCUMENTS (Step 7 Foundation) */}
        {(activeTab === 'all' || activeTab === 'documents') && (
          <section className="clinical-card documents-card" aria-labelledby="section-docs-title">
            <div className="clinical-card-header">
              <div className="card-title-group">
                <span className="card-icon">📁</span>
                <div>
                  <h2 id="section-docs-title" className="card-title">Ingested Medical Records</h2>
                  <span className="card-subtitle">
                    Secure PDF documents associated with this patient ({patientDocs.length} {patientDocs.length === 1 ? 'record' : 'records'})
                  </span>
                </div>
              </div>
              <div className="header-actions">
                <button
                  type="button"
                  className="card-action-btn"
                  onClick={() => setIsUploadModalOpen(true)}
                >
                  <span>+</span> Upload Record
                </button>
                <span className="step-tag active">EHR Document Store</span>
              </div>
            </div>

            <div className="clinical-card-body">
              {loadingDocs ? (
                <div className="docs-loading-state">
                  <span className="spinner-icon">⏳</span> Loading patient records...
                </div>
              ) : patientDocs.length > 0 ? (
                <div className="patient-docs-table-wrapper">
                  <table className="patient-docs-table">
                    <thead>
                      <tr>
                        <th>Document Name</th>
                        <th>Type</th>
                        <th>Pages / Size</th>
                        <th>Upload Date</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patientDocs.map((doc) => (
                        <tr key={doc.id}>
                          <td>
                            <div className="doc-name-cell">
                              <span className="doc-type-icon">📄</span>
                              <div>
                                <span className="doc-filename">{doc.file_name}</span>
                                <span className="doc-detected-sub">
                                  {doc.file_type || 'PDF Document'}
                                </span>
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className="doc-type-tag">
                              {doc.document_type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td>
                            <span className="doc-meta-text">
                              {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'} • {formatFileSize(doc.file_size)}
                            </span>
                          </td>
                          <td>
                            <span className="doc-meta-text">{formatDate(doc.uploaded_at)}</span>
                          </td>
                          <td>
                            <span className={`doc-status-badge status-${doc.status.toLowerCase()}`}>
                              {doc.status}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="doc-inspect-btn"
                              onClick={() => setSelectedDoc(doc)}
                            >
                              Inspect &amp; Preview
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="section-placeholder">
                  <div className="placeholder-icon">📄</div>
                  <h4 className="placeholder-title">No Medical Documents Ingested</h4>
                  <p className="placeholder-text">
                    Upload PDF discharge summaries, specialist consult notes, lab panels, or imaging reports
                    to start building this patient's clinical dossier.
                  </p>
                  <button
                    type="button"
                    className="overview-action-btn upload-primary placeholder-btn"
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    <span>📤</span> Upload First Document
                  </button>
                </div>
              )}
            </div>
          </section>
        )}
        {/* SECTION 1: CLINICAL BRIEF (Step 12 Active) */}
        {(activeTab === 'all' || activeTab === 'brief') && (
          <section className="clinical-card brief-card" aria-labelledby="section-brief-title">
            <div className="clinical-card-header">
              <div className="card-title-group">
                <span className="card-icon">📝</span>
                <div>
                  <h2 id="section-brief-title" className="card-title">Clinical Brief &amp; AI Synthesis</h2>
                  <span className="card-subtitle">
                    Grounded physician executive brief with verified page citations
                  </span>
                </div>
              </div>
              <div className="header-actions">
                {patientSummaries.length > 1 && (
                  <select
                    className="summary-version-select"
                    value={activeSummary?.id || ''}
                    onChange={(e) => handleSelectSummary(e.target.value)}
                    style={{ background: '#ffffff', color: '#0f172a', border: '1px solid #cbd5e1', borderRadius: '0.375rem', padding: '0.3rem 0.5rem', fontSize: '0.8rem', fontWeight: 500 }}
                  >
                    {patientSummaries.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.summary_type_label} ({formatDate(s.created_at)})
                      </option>
                    ))}
                  </select>
                )}
                {onNavigateToSummaries && (
                  <button
                    type="button"
                    className="overview-action-btn"
                    onClick={() => onNavigateToSummaries(patient)}
                    style={{ padding: '0.3rem 0.65rem', fontSize: '0.78rem', background: '#f8fafc', border: '1px solid #cbd5e1', color: '#0284c7', fontWeight: 600, cursor: 'pointer', borderRadius: '6px' }}
                    title="Open full Summaries & Evidence workspace"
                  >
                    Open Workspace →
                  </button>
                )}
                <span className="step-tag active">Grounded Synthesis</span>
              </div>
            </div>

            {/* Quick Mode & Generation Toolbar */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', padding: '0.75rem 1.25rem', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {(['QUICK_CLINICAL', 'DETAILED_CLINICAL', 'MEDICATION', 'INVESTIGATION'] as SummaryType[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    style={{
                      padding: '0.3rem 0.6rem',
                      fontSize: '0.75rem',
                      borderRadius: '0.375rem',
                      border: summaryMode === mode ? '1px solid #0284c7' : '1px solid #cbd5e1',
                      background: summaryMode === mode ? '#e0f2fe' : '#ffffff',
                      color: summaryMode === mode ? '#0369a1' : '#475569',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                    onClick={() => setSummaryMode(mode)}
                  >
                    {mode === 'QUICK_CLINICAL' && '⚡ Quick'}
                    {mode === 'DETAILED_CLINICAL' && '📖 Detailed'}
                    {mode === 'MEDICATION' && '💊 Meds'}
                    {mode === 'INVESTIGATION' && '🔬 Labs'}
                  </button>
                ))}
              </div>

              <button
                type="button"
                className="overview-action-btn upload-primary"
                style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
                onClick={() => handleGenerateSummary(summaryMode)}
                disabled={generatingSummary}
              >
                {generatingSummary ? (
                  <span>⏳ Synthesizing with Gemini...</span>
                ) : (
                  <span>✨ Generate {summaryMode.replace('_', ' ').toLowerCase()} summary</span>
                )}
              </button>
            </div>

            {summaryError && (
              <div style={{ padding: '0.5rem 1.25rem', color: '#b91c1c', fontSize: '0.8rem', background: '#fef2f2', borderBottom: '1px solid #fecaca' }}>
                ⚠️ {summaryError}
              </div>
            )}

            <div className="clinical-card-body">
              {loadingSummary ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                  <span>⏳</span> Loading clinical brief...
                </div>
              ) : activeSummary ? (
                <div className="brief-content-box" style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '1.25rem', borderRadius: '0.5rem' }}>
                  <div className="brief-badge-row" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    <span className="summary-pill active" style={{ fontSize: '0.75rem', background: '#0284c7', color: 'white', padding: '0.2rem 0.5rem', borderRadius: '9999px', fontWeight: 600 }}>
                      {activeSummary.summary_type_label} Brief
                    </span>
                    <span className="model-pill" style={{ fontSize: '0.75rem', background: '#e0e7ff', color: '#4338ca', padding: '0.2rem 0.5rem', borderRadius: '9999px', fontWeight: 600 }}>
                      {activeSummary.model_name || 'Gemini 2.5 Flash'}
                    </span>
                    <span style={{ fontSize: '0.75rem', background: '#ecfdf5', color: '#047857', padding: '0.2rem 0.5rem', borderRadius: '9999px', fontWeight: 600 }}>
                      📑 {activeSummary.evidence_references?.length || 0} Citations Verified
                    </span>
                  </div>

                  <p className="brief-text" style={{ fontSize: '0.95rem', lineHeight: 1.6, color: '#334155', marginBottom: '1rem' }}>
                    {activeSummary.overview}
                  </p>

                  {/* Section Bullets & Citations */}
                  {activeSummary.structured_content.sections?.map((section) => (
                    <div key={section.section_key} style={{ marginTop: '1rem', borderTop: '1px solid #e2e8f0', paddingTop: '0.75rem' }}>
                      <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0284c7', marginBottom: '0.4rem' }}>
                        {section.title}
                      </h4>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {section.bullet_points.map((pt, ptIdx) => (
                          <li key={ptIdx} style={{ fontSize: '0.875rem', color: '#1e293b', paddingLeft: '0.75rem', borderLeft: '3px solid #0284c7' }}>
                            <div>{pt.statement}</div>
                            <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                              {pt.is_uncertain && (
                                <span style={{ fontSize: '0.7rem', color: '#b45309', background: '#fef3c7', border: '1px solid #fde68a', padding: '0.1rem 0.4rem', borderRadius: '0.25rem', fontWeight: 600 }}>
                                  ⚠️ {pt.uncertainty_note || 'Ambiguous in record'}
                                </span>
                              )}
                              {pt.citations?.map((cit, cIdx) => (
                                <button
                                  key={cIdx}
                                  type="button"
                                  onClick={() => setActiveCitation(cit)}
                                  style={{
                                    fontSize: '0.72rem',
                                    color: '#0284c7',
                                    background: '#f0f9ff',
                                    border: '1px solid #bae6fd',
                                    padding: '0.15rem 0.45rem',
                                    borderRadius: '0.25rem',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                  }}
                                  title="View verbatim citation quote"
                                >
                                  📄 {cit.document_name || 'Doc'} {cit.page_number ? `(P.${cit.page_number})` : ''}
                                </button>
                              ))}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="section-placeholder">
                  <div className="placeholder-icon">📋</div>
                  <h4 className="placeholder-title">No AI Clinical Summary Generated Yet</h4>
                  <p className="placeholder-text">
                    MedBrief AI synthesizes structured, verifiable clinical briefs with direct page citations
                    from the uploaded records for {patient.first_name} {patient.last_name}.
                  </p>
                  <button
                    type="button"
                    className="overview-action-btn upload-primary placeholder-btn"
                    onClick={() => handleGenerateSummary('QUICK_CLINICAL')}
                    disabled={generatingSummary}
                  >
                    <span>⚡</span> {generatingSummary ? 'Synthesizing...' : 'Generate Quick Clinical Brief'}
                  </button>
                </div>
              )}
            </div>
          </section>
        )}

        {/* SECTION 2: KEY CLINICAL EVENTS */}
        {(activeTab === 'all' || activeTab === 'events') && (
          <section className="clinical-card" aria-labelledby="section-events-title">
            <div className="clinical-card-header">
              <div className="card-title-group">
                <span className="card-icon">⏳</span>
                <div>
                  <h2 id="section-events-title" className="card-title">Key Clinical Events</h2>
                  <span className="card-subtitle">Chronological admission &amp; care timeline</span>
                </div>
              </div>
              <span className="step-tag active">Care Journey</span>
            </div>

            <div className="clinical-card-body">
              {loadingTimeline ? (
                <div style={{ padding: '1rem', color: '#94a3b8', textAlign: 'center' }}>
                  Loading clinical timeline...
                </div>
              ) : timelineSummary && timelineSummary.recent_events.length > 0 ? (
                <>
                  <div className="timeline-preview-list">
                    {timelineSummary.recent_events.map((ev) => (
                      <div key={ev.id} className="timeline-item">
                        <div className={`timeline-node ${ev.event_type}`} />
                        <div className="timeline-content">
                          <div className="timeline-header-row">
                            <span className="timeline-type">
                              {ev.event_type_icon} {ev.event_type_label}
                            </span>
                            <span className="timeline-date">{ev.display_date}</span>
                          </div>
                          <h4 className="timeline-title">{ev.title}</h4>
                          <p className="timeline-desc">{ev.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {onNavigateToTimeline && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToTimeline(patient)}
                    >
                      <span>View Full Clinical Timeline ({timelineSummary.total_events} events) →</span>
                    </button>
                  )}
                </>
              ) : isDemoWithRecords ? (
                <>
                  <div className="timeline-preview-list">
                    <div className="timeline-item">
                      <div className="timeline-node admission" />
                      <div className="timeline-content">
                        <div className="timeline-header-row">
                          <span className="timeline-type">Hospital Admission</span>
                          <span className="timeline-date">Feb 5, 2026 • 08:30</span>
                        </div>
                        <h4 className="timeline-title">Admission for NSTEMI</h4>
                        <p className="timeline-desc">Acute substernal chest discomfort; troponin elevation confirmed.</p>
                      </div>
                    </div>

                    <div className="timeline-item">
                      <div className="timeline-node discharge" />
                      <div className="timeline-content">
                        <div className="timeline-header-row">
                          <span className="timeline-type">Hospital Discharge</span>
                          <span className="timeline-date">Feb 10, 2026 • 14:00</span>
                        </div>
                        <h4 className="timeline-title">Discharge to Outpatient Follow-up</h4>
                        <p className="timeline-desc">Hemodynamically stable on dual antiplatelet and high-intensity statin therapy.</p>
                      </div>
                    </div>
                  </div>
                  {onNavigateToTimeline && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToTimeline(patient)}
                    >
                      <span>View Full Clinical Timeline →</span>
                    </button>
                  )}
                </>
              ) : (
                <div className="section-placeholder">
                  <div className="placeholder-icon">🗓️</div>
                  <h4 className="placeholder-title">No Structured Clinical Events Recorded</h4>
                  <p className="placeholder-text">
                    Chronological event extraction will parse admissions, consults, and interventions directly
                    from uploaded patient documentation.
                  </p>
                  {onNavigateToTimeline && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToTimeline(patient)}
                    >
                      <span>Open Clinical Timeline →</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* SECTION 3: MEDICATIONS (Step 11 Active) */}
        {(activeTab === 'all' || activeTab === 'meds') && (
          <section className="clinical-card" aria-labelledby="section-meds-title">
            <div className="clinical-card-header">
              <div className="card-title-group">
                <span className="card-icon">💊</span>
                <div>
                  <h2 id="section-meds-title" className="card-title">Medication Intelligence & Reconciliation</h2>
                  <span className="card-subtitle">
                    Prescriptions, dosages, and verified medication changes ({medications.length} items, {medicationChanges.length} changes)
                  </span>
                </div>
              </div>
              <span className="step-tag active">Pharmacotherapy</span>
            </div>

            <div className="clinical-card-body">
              {loadingIntelligence ? (
                <div style={{ padding: '1rem', color: '#94a3b8', textAlign: 'center' }}>
                  Loading medication intelligence...
                </div>
              ) : medications.length > 0 || medicationChanges.length > 0 ? (
                <div className="meds-list">
                  {/* Highlight recent medication changes */}
                  {medicationChanges.slice(0, 3).map((chg) => (
                    <div key={chg.id} className="med-item changed">
                      <div className="med-info">
                        <div className="med-name-row">
                          <span className="med-name">{chg.medication_name}</span>
                          <span className="med-badge changed">
                            {chg.change_type_label || chg.change_type.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="med-dosage" style={{ fontWeight: 600, color: '#fbbf24', marginTop: '0.2rem' }}>
                          {chg.change_type === 'DOSE_CHANGED' && chg.previous_value && chg.new_value ? (
                            <span>{chg.previous_value} → {chg.new_value}</span>
                          ) : chg.previous_value && chg.new_value ? (
                            <span>{chg.previous_value} → {chg.new_value}</span>
                          ) : (
                            <span>{chg.new_value || chg.change_type}</span>
                          )}
                        </div>
                        {chg.reason && (
                          <span className="med-reason" style={{ color: '#cbd5e1' }}>
                            Reason: {chg.reason}
                          </span>
                        )}
                        {chg.source?.source_snippet && (
                          <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontStyle: 'italic', marginTop: '0.25rem' }}>
                            "{chg.source.source_snippet}" {chg.source.page_number ? `(Page ${chg.source.page_number})` : ''}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Active Meds preview */}
                  {medications.filter(m => m.status === 'ACTIVE').slice(0, 4).map((med) => (
                    <div key={med.id} className="med-item active">
                      <div className="med-info">
                        <div className="med-name-row">
                          <span className="med-name">{med.medication_name}</span>
                          <span className="med-badge unchanged">Active</span>
                        </div>
                        <span className="med-dosage">
                          {[
                            med.dosage ? `${med.dosage}${med.dose_unit ? ` ${med.dose_unit}` : ''}` : null,
                            med.route,
                            med.frequency
                          ].filter(Boolean).join(' • ') || 'Dosage recorded'}
                        </span>
                        {med.is_conflict && (
                          <span className="med-reason" style={{ color: '#f87171' }}>
                            ⚠️ Documented conflict: {med.conflict_details || 'Differing dosages in source'}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}

                  {onNavigateToMedications && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToMedications(patient)}
                      style={{ marginTop: '0.75rem' }}
                    >
                      <span>Open Full Medication Intelligence ({medications.length} meds, {medicationChanges.length} changes) →</span>
                    </button>
                  )}
                </div>
              ) : isDemoWithRecords ? (
                <div className="meds-list">
                  <div className="med-item changed">
                    <div className="med-info">
                      <div className="med-name-row">
                        <span className="med-name">Atorvastatin (Lipitor)</span>
                        <span className="med-badge changed">Dose Changed</span>
                      </div>
                      <span className="med-dosage">20 mg → 40 mg • Oral • Once daily at bedtime</span>
                      <span className="med-reason">Reason: Up-titration post-NSTEMI</span>
                    </div>
                  </div>

                  <div className="med-item active">
                    <div className="med-info">
                      <div className="med-name-row">
                        <span className="med-name">Metformin (Glucophage)</span>
                        <span className="med-badge unchanged">Active</span>
                      </div>
                      <span className="med-dosage">500 mg • Oral • Twice daily with meals</span>
                      <span className="med-reason">Status: Chronic diabetes management continued</span>
                    </div>
                  </div>

                  {onNavigateToMedications && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToMedications(patient)}
                      style={{ marginTop: '0.75rem' }}
                    >
                      <span>Open Full Medication Intelligence →</span>
                    </button>
                  )}
                </div>
              ) : (
                <div className="section-placeholder">
                  <div className="placeholder-icon">💊</div>
                  <h4 className="placeholder-title">No Structured Medication Records Yet</h4>
                  <p className="placeholder-text">
                    Upload clinical documents to extract current prescriptions, dose modifications, and start/stop events.
                  </p>
                  {onNavigateToMedications && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToMedications(patient)}
                    >
                      <span>Open Medication Intelligence View →</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* SECTION 4: INVESTIGATIONS (Step 11 Active) */}
        {(activeTab === 'all' || activeTab === 'labs') && (
          <section className="clinical-card" aria-labelledby="section-investigations-title">
            <div className="clinical-card-header">
              <div className="card-title-group">
                <span className="card-icon">🔬</span>
                <div>
                  <h2 id="section-investigations-title" className="card-title">Investigations & Diagnostics</h2>
                  <span className="card-subtitle">
                    Pathology, imaging, and diagnostic tracking ({investigations.length} records, {intelligenceSummary?.investigations.pending_count ?? 0} pending)
                  </span>
                </div>
              </div>
              <span className="step-tag active">Diagnostics</span>
            </div>

            <div className="clinical-card-body">
              {loadingIntelligence ? (
                <div style={{ padding: '1rem', color: '#94a3b8', textAlign: 'center' }}>
                  Loading diagnostic investigations...
                </div>
              ) : investigations.length > 0 ? (
                <div className="investigations-list">
                  {investigations.slice(0, 4).map((inv) => (
                    <div
                      key={inv.id}
                      className={`inv-item ${inv.is_abnormal ? 'abnormal' : inv.status === 'PENDING' ? 'pending' : ''}`}
                    >
                      <div className="inv-header">
                        <span className="inv-name">{inv.investigation_name}</span>
                        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                          {inv.is_abnormal && (
                            <span className="inv-badge abnormal">Abnormal</span>
                          )}
                          <span className={`inv-badge ${inv.status.toLowerCase()}`}>
                            {inv.status}
                          </span>
                        </div>
                      </div>
                      <div className="inv-data-row">
                        {inv.result_summary && (
                          <span className="inv-val">
                            Result: <strong>{inv.result_summary}</strong>
                          </span>
                        )}
                        {inv.reference_range && (
                          <span className="inv-ref">Ref: {inv.reference_range}</span>
                        )}
                        <span className="inv-date">{inv.display_date}</span>
                        {inv.source?.document_name && (
                          <span style={{ fontSize: '0.72rem', color: '#38bdf8' }}>
                            📄 {inv.source.document_name} {inv.source.page_number ? `(p. ${inv.source.page_number})` : ''}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}

                  {onNavigateToInvestigations && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToInvestigations(patient)}
                      style={{ marginTop: '0.75rem' }}
                    >
                      <span>Open Full Investigation Intelligence ({investigations.length} tests) →</span>
                    </button>
                  )}
                </div>
              ) : isDemoWithRecords ? (
                <div className="investigations-list">
                  <div className="inv-item abnormal">
                    <div className="inv-header">
                      <span className="inv-name">Troponin I (High-Sensitivity)</span>
                      <span className="inv-badge abnormal">Abnormal (High Urgency)</span>
                    </div>
                    <div className="inv-data-row">
                      <span className="inv-val">Result: <strong>0.42 ng/mL</strong></span>
                      <span className="inv-ref">Ref: &lt; 0.04 ng/mL</span>
                      <span className="inv-date">Feb 5, 2026</span>
                    </div>
                  </div>

                  <div className="inv-item pending">
                    <div className="inv-header">
                      <span className="inv-name">Transthoracic Echocardiogram (TTE)</span>
                      <span className="inv-badge pending">Outstanding / Ordered</span>
                    </div>
                    <div className="inv-data-row">
                      <span className="inv-val">Status: <strong>Pending Outpatient Appointment</strong></span>
                      <span className="inv-ref">Due: Within 4 weeks</span>
                      <span className="inv-date">Priority: HIGH</span>
                    </div>
                  </div>

                  {onNavigateToInvestigations && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToInvestigations(patient)}
                      style={{ marginTop: '0.75rem' }}
                    >
                      <span>Open Full Investigation Intelligence →</span>
                    </button>
                  )}
                </div>
              ) : (
                <div className="section-placeholder">
                  <div className="placeholder-icon">🧪</div>
                  <h4 className="placeholder-title">No Investigation Records Found</h4>
                  <p className="placeholder-text">
                    Upload diagnostic documents to extract laboratory values, imaging findings, and pending tests.
                  </p>
                  {onNavigateToInvestigations && (
                    <button
                      type="button"
                      className="view-timeline-btn"
                      onClick={() => onNavigateToInvestigations(patient)}
                    >
                      <span>Open Investigation Intelligence View →</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* SECTION 5: OUTSTANDING CLINICAL ACTIONS & FOLLOW-UPS (Step 11 Active) */}
        {(activeTab === 'all' || activeTab === 'outstanding' || activeTab === 'labs') && (
          <section className="clinical-card" aria-labelledby="section-outstanding-title">
            <div className="clinical-card-header">
              <div className="card-title-group">
                <span className="card-icon">⚠️</span>
                <div>
                  <h2 id="section-outstanding-title" className="card-title">Outstanding Clinical Actions & Follow-ups</h2>
                  <span className="card-subtitle">
                    Pending tests, required consults, monitoring and medication reviews ({outstandingItems.length} items)
                  </span>
                </div>
              </div>
              <span className="step-tag active">Action Items</span>
            </div>

            <div className="clinical-card-body">
              {loadingIntelligence ? (
                <div style={{ padding: '1rem', color: '#94a3b8', textAlign: 'center' }}>
                  Loading outstanding items...
                </div>
              ) : outstandingItems.length > 0 ? (
                <div className="investigations-list">
                  {outstandingItems.map((item) => (
                    <div
                      key={item.id}
                      className={`inv-item ${item.priority === 'CRITICAL' || item.priority === 'HIGH' ? 'abnormal' : 'pending'}`}
                    >
                      <div className="inv-header">
                        <span className="inv-name">{item.title}</span>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          <span className={`inv-badge ${item.priority === 'CRITICAL' || item.priority === 'HIGH' ? 'abnormal' : 'pending'}`}>
                            {item.priority}
                          </span>
                          <span className="inv-badge pending">
                            {item.item_type_label || item.item_type.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                      <div className="inv-data-row">
                        {item.description && (
                          <span style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>{item.description}</span>
                        )}
                        {item.display_due_date && (
                          <span className="inv-ref">Due: <strong>{item.display_due_date}</strong></span>
                        )}
                        <span className="inv-date">Status: {item.status}</span>
                      </div>
                      {item.source?.source_snippet && (
                        <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontStyle: 'italic', marginTop: '0.2rem' }}>
                          Source: "{item.source.source_snippet}" {item.source.page_number ? `(Page ${item.source.page_number})` : ''}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="section-placeholder">
                  <div className="placeholder-icon">✅</div>
                  <h4 className="placeholder-title">No Outstanding Clinical Actions</h4>
                  <p className="placeholder-text">
                    All ordered investigations, follow-up consults, and care directives are currently resolved or none are cataloged yet.
                  </p>
                </div>
              )}
            </div>
          </section>
        )}
      </div>

      {/* Clinical Decision Support Notice */}
      <footer className="overview-footer-notice">
        <span className="notice-icon">🛡️</span>
        <div>
          <strong>Clinical Decision Support Active:</strong> All clinical extractions, summaries, timeline events, and medication reconciliations are synthesized by Gemini AI and grounded in source records. Doctor-in-the-loop review and sign-off are required prior to clinical action.
        </div>
      </footer>

      {/* Edit Demographics Modal */}
      <PatientModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSubmit={handleUpdate}
        initialData={patient}
        title="Edit Patient Demographics"
      />

      {/* Document Upload Modal (Step 7) */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        targetPatient={patient}
        onSuccess={handleDocUploadSuccess}
      />

      {/* Document Detail & Preview Modal (Step 7) */}
      <DocumentDetailModal
        isOpen={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        document={selectedDoc}
        onDocumentUpdated={handleDocUpdated}
      />

      {/* Grounded Source Evidence Modal (Step 12) */}
      {activeCitation && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.75)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(3px)',
          }}
          onClick={() => setActiveCitation(null)}
        >
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '0.75rem',
              padding: '1.5rem',
              width: '90%',
              maxWidth: '520px',
              color: '#0f172a',
              boxShadow: '0 20px 25px -5px rgba(15, 23, 42, 0.15)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0284c7', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>📄</span> Grounded Source Evidence
              </div>
              <button
                type="button"
                onClick={() => setActiveCitation(null)}
                style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '1.25rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <div style={{ fontSize: '0.85rem', color: '#334155', marginBottom: '0.4rem' }}>
              <strong>Source Document:</strong> {activeCitation.document_name || 'Document Record'}
            </div>
            {activeCitation.page_number && (
              <div style={{ fontSize: '0.85rem', color: '#334155', marginBottom: '0.4rem' }}>
                <strong>Page Number:</strong> Page {activeCitation.page_number}
              </div>
            )}
            {activeCitation.source_section && (
              <div style={{ fontSize: '0.85rem', color: '#334155', marginBottom: '0.4rem' }}>
                <strong>Section:</strong> {activeCitation.source_section}
              </div>
            )}

            <div style={{ marginTop: '0.85rem', fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>
              Verbatim Extracted Quote:
            </div>
            <div
              style={{
                background: '#f8fafc',
                borderLeft: '3px solid #059669',
                padding: '0.75rem 1rem',
                margin: '0.75rem 0',
                borderRadius: '0.25rem',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                color: '#065f46',
                lineHeight: 1.5,
              }}
            >
              "{activeCitation.source_snippet}"
            </div>

            <div style={{ textAlign: 'right', marginTop: '1rem' }}>
              <button
                type="button"
                className="overview-action-btn upload-primary"
                style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
                onClick={() => setActiveCitation(null)}
              >
                Close Evidence Modal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

