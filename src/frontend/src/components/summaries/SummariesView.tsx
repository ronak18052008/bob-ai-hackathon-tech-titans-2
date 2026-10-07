/**
 * MedBrief AI — AI Clinical Summaries & Evidence Workspace
 * Step 12: AI Clinical Summary + Evidence/Source Reference Layer
 *
 * Dedicated physician workspace for generating and reviewing:
 * - Multi-mode AI clinical summaries (Quick Clinical, Detailed Clinical, Medication, Investigation)
 * - Complete version history (non-destructive persistence)
 * - Grounded evidence citations linking clinical statements to exact source document pages
 * - Verification drawer displaying verbatim record quotes
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord } from '../../types/patient'
import type {
  SummaryType,
  SummaryItem,
  SummaryDetail,
  SummaryEvidenceCitation,
} from '../../types/summary'
import { fetchPatients } from '../../services/patientApi'
import {
  fetchPatientSummaries,
  generatePatientSummary,
  fetchSummaryById,
} from '../../services/summaryApi'
import { useToast } from '../../context/ToastContext'
import './SummariesView.css'

interface SummariesViewProps {
  targetPatient?: PatientRecord
  patients?: PatientRecord[]
  onPatientChange?: (patient: PatientRecord) => void
  onSelectPatient?: () => void
}

const MODES: { type: SummaryType; label: string; desc: string; icon: string }[] = [
  {
    type: 'QUICK_CLINICAL',
    label: 'Quick Clinical',
    desc: 'High-yield executive brief of conditions, meds & pending items',
    icon: '⚡',
  },
  {
    type: 'DETAILED_CLINICAL',
    label: 'Detailed Clinical',
    desc: 'Comprehensive narrative synthesis of inpatient/outpatient course',
    icon: '📖',
  },
  {
    type: 'MEDICATION',
    label: 'Medications',
    desc: 'Pharmacotherapy review, titrations, starts/stops & conflicts',
    icon: '💊',
  },
  {
    type: 'INVESTIGATION',
    label: 'Investigations',
    desc: 'Diagnostic workup, abnormal values & verified pending tests',
    icon: '🔬',
  },
]

export const SummariesView: React.FC<SummariesViewProps> = ({
  targetPatient,
  patients: propPatients,
  onPatientChange,
}) => {
  const { showToast } = useToast()
  const [patients, setPatients] = useState<PatientRecord[]>(propPatients || [])
  const [selectedPatientId, setSelectedPatientId] = useState<string>(targetPatient?.id || '')
  const [currentPatient, setCurrentPatient] = useState<PatientRecord | null>(targetPatient || null)

  const [selectedMode, setSelectedMode] = useState<SummaryType>('QUICK_CLINICAL')
  const [customInstructions, setCustomInstructions] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [generationError, setGenerationError] = useState<string | null>(null)

  // Summaries list and selected summary
  const [summariesList, setSummariesList] = useState<SummaryItem[]>([])
  const [selectedSummaryId, setSelectedSummaryId] = useState<string | null>(null)
  const [activeSummaryDetail, setActiveSummaryDetail] = useState<SummaryDetail | null>(null)
  const [loadingList, setLoadingList] = useState<boolean>(false)
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false)

  // Citation modal state
  const [activeCitation, setActiveCitation] = useState<SummaryEvidenceCitation | null>(null)

  // 1. Initial Load of Patients
  useEffect(() => {
    if (propPatients && propPatients.length > 0) {
      setPatients(propPatients)
    } else if (!targetPatient) {
      fetchPatients({ pageSize: 50 })
        .then((res) => {
          if (res.items.length > 0) {
            setPatients(res.items)
            setSelectedPatientId((prev) => prev || res.items[0].id)
            setCurrentPatient((prev) => prev || res.items[0])
          }
        })
        .catch((err) => console.error('Failed to load patient caseload:', err))
    }
  }, [propPatients, targetPatient])

  useEffect(() => {
    if (targetPatient) {
      setSelectedPatientId(targetPatient.id)
      setCurrentPatient(targetPatient)
    }
  }, [targetPatient])

  // 2. Load Patient Summaries
  const loadSummaries = useCallback(async (patientId: string) => {
    if (!patientId) return
    setLoadingList(true)
    try {
      const res = await fetchPatientSummaries(patientId)
      setSummariesList(res.items)
      if (res.items.length > 0) {
        setSelectedSummaryId(res.items[0].id)
      } else {
        setSelectedSummaryId(null)
        setActiveSummaryDetail(null)
      }
    } catch (err) {
      console.error('Error fetching summaries list:', err)
      setSummariesList([])
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    if (selectedPatientId) {
      loadSummaries(selectedPatientId)
    }
  }, [selectedPatientId, loadSummaries])

  // 3. Load Selected Summary Detail
  useEffect(() => {
    if (!selectedSummaryId) {
      setActiveSummaryDetail(null)
      return
    }
    setLoadingDetail(true)
    fetchSummaryById(selectedSummaryId)
      .then((detail) => setActiveSummaryDetail(detail))
      .catch((err) => {
        console.error('Error fetching summary detail:', err)
        setActiveSummaryDetail(null)
      })
      .finally(() => setLoadingDetail(false))
  }, [selectedSummaryId])

  // 4. Handle Patient Change
  const handlePatientSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value
    setSelectedPatientId(id)
    const found = patients.find((p) => p.id === id) || null
    setCurrentPatient(found)
    if (onPatientChange && found) {
      onPatientChange(found)
    }
  }

  // 5. Handle Summary Generation
  const handleGenerate = async () => {
    if (!selectedPatientId || isGenerating) return
    setIsGenerating(true)
    setGenerationError(null)

    try {
      const generated = await generatePatientSummary(
        selectedPatientId,
        selectedMode,
        customInstructions
      )
      // Refresh list and set active detail
      await loadSummaries(selectedPatientId)
      setSelectedSummaryId(generated.id)
      setActiveSummaryDetail(generated)
      setCustomInstructions('')
      showToast('AI clinical summary generated successfully.', 'success')
    } catch (err: any) {
      console.error('Failed to generate clinical summary:', err)
      const msg = err.message || 'Error communicating with AI synthesis service.'
      setGenerationError(msg)
      showToast(msg, 'error')
    } finally {
      setIsGenerating(false)
    }
  }

  const formatDate = (isoString?: string) => {
    if (!isoString) return ''
    try {
      const d = new Date(isoString)
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="summaries-container">
      {/* ── Top Header ── */}
      <header className="summaries-header">
        <div className="summaries-title-group">
          <span className="summaries-icon">📝</span>
          <div>
            <h1 className="summaries-title">AI Clinical Summaries &amp; Evidence</h1>
            <p className="summaries-subtitle">
              Synthesized medical briefs with 100% grounded document citations and hallucination guards.
              {currentPatient && (
                <span> &bull; Active: <strong>{currentPatient.first_name} {currentPatient.last_name}</strong> ({currentPatient.mrn})</span>
              )}
            </p>
          </div>
        </div>

        <div className="patient-picker">
          <label htmlFor="summary-patient-select">Patient:</label>
          <select
            id="summary-patient-select"
            value={selectedPatientId}
            onChange={handlePatientSelect}
            disabled={Boolean(targetPatient)}
          >
            {targetPatient ? (
              <option value={targetPatient.id}>
                {targetPatient.first_name} {targetPatient.last_name} ({targetPatient.mrn})
              </option>
            ) : (
              patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name} ({p.mrn})
                </option>
              ))
            )}
          </select>
        </div>
      </header>

      {/* ── Generator Control Panel ── */}
      <section className="summary-generator-panel" aria-label="Summary Generation Controls">
        <div className="panel-header">
          <div className="panel-title">
            <span>✨</span> Generate Structured Clinical Brief
          </div>
          <span className="badge-pill model">Gemini AI Synthesis Gateway</span>
        </div>

        <div className="mode-selector">
          {MODES.map((m) => (
            <button
              key={m.type}
              type="button"
              className={`mode-btn ${selectedMode === m.type ? 'active' : ''}`}
              onClick={() => setSelectedMode(m.type)}
            >
              <div className="mode-name">
                {m.icon} {m.label}
              </div>
              <div className="mode-desc">{m.desc}</div>
            </button>
          ))}
        </div>

        <div className="generator-actions-row">
          <input
            type="text"
            className="custom-prompt-input"
            placeholder="Optional clinician instruction (e.g. 'Focus on post-discharge follow-up')..."
            value={customInstructions}
            onChange={(e) => setCustomInstructions(e.target.value)}
            disabled={isGenerating}
          />
          <button
            type="button"
            className="generate-btn"
            onClick={handleGenerate}
            disabled={isGenerating || !selectedPatientId}
          >
            {isGenerating ? (
              <>
                <span>⏳</span> Synthesizing with Gemini AI...
              </>
            ) : (
              <>
                <span>🚀</span> Generate Summary
              </>
            )}
          </button>
        </div>

        {generationError && (
          <div style={{ color: '#ef4444', marginTop: '0.75rem', fontSize: '0.85rem' }}>
            ⚠️ {generationError}
          </div>
        )}
      </section>

      {/* ── Main Workspace: History List + Active Document View ── */}
      <div className="summary-workspace-layout">
        {/* Left History Column */}
        <aside className="history-sidebar">
          <h2 className="history-title">Summary History</h2>
          {loadingList ? (
            <div style={{ color: '#94a3b8', fontSize: '0.85rem', textAlign: 'center', padding: '1rem' }}>
              Loading history...
            </div>
          ) : summariesList.length > 0 ? (
            <div className="history-list">
              {summariesList.map((item) => (
                <div
                  key={item.id}
                  className={`history-card ${selectedSummaryId === item.id ? 'selected' : ''}`}
                  onClick={() => setSelectedSummaryId(item.id)}
                >
                  <div className="history-card-header">
                    <span className="history-type-badge">{item.summary_type_label}</span>
                    <span className="history-date">{formatDate(item.created_at)}</span>
                  </div>
                  <div className="history-card-title">{item.title}</div>
                  <div className="history-evidence-count">
                    <span>📑</span> {item.evidence_count} evidence {item.evidence_count === 1 ? 'citation' : 'citations'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.85rem', textAlign: 'center', padding: '1rem' }}>
              No summaries generated yet. Choose a mode above to synthesize your first summary.
            </div>
          )}
        </aside>

        {/* Right Active Summary View */}
        <main className="summary-document-view">
          {loadingDetail ? (
            <div style={{ color: '#94a3b8', textAlign: 'center', padding: '3rem' }}>
              <span>⏳</span> Loading summary details and verified evidence...
            </div>
          ) : activeSummaryDetail ? (
            <>
              {/* Meta Banner */}
              <div className="summary-meta-banner">
                <div>
                  <h2 className="summary-heading">{activeSummaryDetail.title}</h2>
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '0.2rem' }}>
                    Generated {formatDate(activeSummaryDetail.created_at)} for {activeSummaryDetail.patient_name} (MRN: {activeSummaryDetail.patient_mrn})
                  </div>
                </div>

                <div className="summary-badges">
                  <span className="badge-pill status">{activeSummaryDetail.status}</span>
                  <span className="badge-pill model">{activeSummaryDetail.model_name || 'Gemini 2.5 Flash'}</span>
                  <span className="badge-pill evidence-total">
                    📑 {activeSummaryDetail.evidence_references?.length || 0} Citations Verified
                  </span>
                </div>
              </div>

              {/* Insufficient Data Alert if flagged */}
              {activeSummaryDetail.structured_content.has_insufficient_data && (
                <div style={{ background: '#7f1d1d', border: '1px solid #b91c1c', padding: '0.75rem 1rem', borderRadius: '0.5rem', color: '#fecaca', fontSize: '0.9rem' }}>
                  ⚠️ <strong>Insufficient Documentation:</strong> {activeSummaryDetail.overview}
                </div>
              )}

              {/* Executive Overview */}
              <div className="summary-overview-box">
                <div className="overview-label">Clinical Overview</div>
                <p className="overview-text">{activeSummaryDetail.overview}</p>
              </div>

              {/* Structured Sections */}
              <div className="summary-sections-container">
                {activeSummaryDetail.structured_content.sections?.map((section) => (
                  <div key={section.section_key} className="summary-section-card">
                    <h3 className="section-card-title">{section.title}</h3>
                    {section.summary_text && (
                      <div className="section-summary-narrative">{section.summary_text}</div>
                    )}

                    <ul className="bullet-points-list">
                      {section.bullet_points.map((pt, idx) => (
                        <li key={idx} className="bullet-point-item">
                          <div className="statement-text">{pt.statement}</div>

                          <div className="citations-row">
                            {pt.is_uncertain && (
                              <span className="uncertainty-badge">
                                ⚠️ {pt.uncertainty_note || 'Ambiguous in record'}
                              </span>
                            )}

                            {pt.citations?.map((cit, cIdx) => (
                              <button
                                key={cIdx}
                                type="button"
                                className="citation-pill"
                                onClick={() => setActiveCitation(cit)}
                                title="Click to view verbatim evidence citation"
                              >
                                <span>📄</span>
                                {cit.document_name || 'Document'} {cit.page_number ? `(P.${cit.page_number})` : ''}
                              </button>
                            ))}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-summary-state">
              <div className="empty-icon">📝</div>
              <h3 className="empty-title">No AI Summary Selected</h3>
              <p className="empty-text">
                Select a mode above and click "Generate Summary" to synthesize a doctor-in-the-loop clinical brief
                backed by verifiable document citations.
              </p>
            </div>
          )}
        </main>
      </div>

      {/* ── Grounded Evidence Modal ── */}
      {activeCitation && (
        <div className="citation-modal-overlay" onClick={() => setActiveCitation(null)}>
          <div className="citation-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <span>📄</span> Grounded Source Evidence
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setActiveCitation(null)}
              >
                &times;
              </button>
            </div>

            <div className="citation-meta-item">
              <strong>Source Document:</strong> {activeCitation.document_name || 'Document Record'}
            </div>
            {activeCitation.page_number && (
              <div className="citation-meta-item">
                <strong>Page Number:</strong> Page {activeCitation.page_number}
              </div>
            )}
            {activeCitation.source_section && (
              <div className="citation-meta-item">
                <strong>Document Section:</strong> {activeCitation.source_section}
              </div>
            )}

            <div style={{ marginTop: '1rem', fontSize: '0.85rem', color: '#94a3b8' }}>
              Verbatim Extracted Quote:
            </div>
            <div className="citation-quote-box">"{activeCitation.source_snippet}"</div>

            <div style={{ textAlign: 'right', marginTop: '1rem' }}>
              <button
                type="button"
                className="generate-btn"
                style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
                onClick={() => setActiveCitation(null)}
              >
                Close Verification Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
