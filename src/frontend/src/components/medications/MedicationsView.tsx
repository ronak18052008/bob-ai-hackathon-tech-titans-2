/**
 * MedBrief AI — Medication Intelligence Workspace
 * Step 11: Medication + Investigation Intelligence
 *
 * Clinical medication intelligence:
 * - Active prescriptions, drug names, doses, routes, frequencies, and statuses
 * - Deterministic medication change tracking (STARTED, STOPPED, DOSE_CHANGED, etc.)
 * - Dose comparison (Previous → New) strictly when supported by documented evidence
 * - Detection of conflicting regimens across records
 * - Clear distinction: DOCUMENTED vs DERIVED intelligence
 * - Source traceability with expandable verbatim snippets
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord } from '../../types/patient'
import type {
  MedicationItem,
  MedicationChangeItem,
  MedicationSummaryStats,
  MedicationChangeSummaryStats,
} from '../../types/intelligence'
import { fetchPatients } from '../../services/patientApi'
import {
  fetchPatientMedications,
  fetchPatientMedicationChanges,
} from '../../services/intelligenceApi'
import { useDebounce } from '../../hooks/useDebounce'
import './MedicationsView.css'

interface MedicationsViewProps {
  targetPatient?: PatientRecord
  patients?: PatientRecord[]
  onPatientChange?: (patient: PatientRecord) => void
  onSelectPatient?: () => void
  onInspectDocument?: (documentId: string) => void
  onInspectTimeline?: () => void
}

type MedTab = 'prescriptions' | 'changes'

export const MedicationsView: React.FC<MedicationsViewProps> = ({
  targetPatient,
  patients: propPatients,
  onPatientChange,
  onInspectDocument,
  onInspectTimeline,
}) => {
  const [patients, setPatients] = useState<PatientRecord[]>(propPatients || [])
  const [selectedPatientId, setSelectedPatientId] = useState<string>(targetPatient?.id || '')
  const [currentPatient, setCurrentPatient] = useState<PatientRecord | null>(targetPatient || null)

  const [activeTab, setActiveTab] = useState<MedTab>('prescriptions')

  // Medications state
  const [meds, setMeds] = useState<MedicationItem[]>([])
  const [medSummary, setMedSummary] = useState<MedicationSummaryStats | null>(null)
  const [medLoading, setMedLoading] = useState<boolean>(true)
  const [medError, setMedError] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const debouncedSearch = useDebounce(searchQuery, 300)

  // Medication Changes state
  const [changes, setChanges] = useState<MedicationChangeItem[]>([])
  const [changeSummary, setChangeSummary] = useState<MedicationChangeSummaryStats | null>(null)
  const [changesLoading, setChangesLoading] = useState<boolean>(true)
  const [selectedChangeType, setSelectedChangeType] = useState<string>('ALL')

  // Expanded snippet state
  const [expandedSnippetId, setExpandedSnippetId] = useState<string | null>(null)

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

  // 2. Fetch Medications
  const loadMedications = useCallback(async () => {
    if (!selectedPatientId) return
    setMedLoading(true)
    setMedError(null)

    try {
      const data = await fetchPatientMedications(selectedPatientId, {
        status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        search: debouncedSearch.trim() || undefined,
        pageSize: 100,
      })
      setMeds(data.items)
      setMedSummary(data.summary)
    } catch (err: any) {
      setMedError(err.message || 'Failed to load medication records')
    } finally {
      setMedLoading(false)
    }
  }, [selectedPatientId, selectedStatus, debouncedSearch])

  // 3. Fetch Medication Changes
  const loadChanges = useCallback(async () => {
    if (!selectedPatientId) return
    setChangesLoading(true)

    try {
      const data = await fetchPatientMedicationChanges(selectedPatientId, {
        changeType: selectedChangeType !== 'ALL' ? selectedChangeType : undefined,
        pageSize: 100,
      })
      setChanges(data.items)
      setChangeSummary(data.summary)
    } catch (err: any) {
      console.error('Failed to load medication changes:', err)
    } finally {
      setChangesLoading(false)
    }
  }, [selectedPatientId, selectedChangeType])

  useEffect(() => {
    loadMedications()
    loadChanges()
  }, [loadMedications, loadChanges])

  const handlePatientChange = (pId: string) => {
    setSelectedPatientId(pId)
    const match = patients.find((p) => p.id === pId)
    if (match) {
      setCurrentPatient(match)
      if (onPatientChange) {
        onPatientChange(match)
      }
    }
    setExpandedSnippetId(null)
  }

  const toggleSnippet = (id: string) => {
    setExpandedSnippetId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="medications-view-container" role="main" aria-label="Medication Intelligence Workspace">
      {/* ── Patient Context Header ── */}
      <header className="med-header-card">
        <div className="med-header-top">
          <div className="med-patient-info">
            <div className="patient-avatar-pill" aria-hidden="true">💊</div>
            <div className="patient-details-col">
              <div className="timeline-patient-name-row">
                <h1 className="timeline-patient-name">
                  {currentPatient
                    ? `${currentPatient.first_name} ${currentPatient.last_name}`
                    : 'Select Patient'}
                </h1>
                <span className="patient-mrn-badge">
                  MRN: {currentPatient?.mrn || 'N/A'}
                </span>
              </div>
              <div className="timeline-patient-meta">
                <span>{currentPatient?.gender || 'Gender unrecorded'}</span>
                <span>•</span>
                <span>DOB: {currentPatient?.date_of_birth || 'Unrecorded'}</span>
                <span>•</span>
                <span>Status: {currentPatient?.status || 'ACTIVE'}</span>
              </div>
            </div>
          </div>

          <div className="med-header-actions">
            {patients.length > 1 && (
              <select
                className="patient-dropdown"
                value={selectedPatientId}
                onChange={(e) => handlePatientChange(e.target.value)}
                aria-label="Switch patient"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name} ({p.mrn})
                  </option>
                ))}
              </select>
            )}

            {onInspectTimeline && (
              <button
                type="button"
                className="btn-med-refresh"
                onClick={onInspectTimeline}
                title="View full clinical timeline"
              >
                <span>⏳</span> View Timeline
              </button>
            )}

            <button
              type="button"
              className="btn-med-refresh"
              onClick={() => {
                loadMedications()
                loadChanges()
              }}
              title="Refresh medication records"
            >
              <span>🔄</span> Refresh
            </button>
          </div>
        </div>

        {/* ── Summary Ribbon ── */}
        <div className="med-stats-ribbon" aria-label="Medication Statistics">
          <div className="med-stat-box">
            <span className="med-stat-label">Active Regimens</span>
            <span className="med-stat-val" style={{ color: '#16a34a' }}>
              {medSummary?.active_count ?? 0}
            </span>
            <span className="med-stat-sub">Currently Documented</span>
          </div>

          <div className="med-stat-box">
            <span className="med-stat-label">Documented Changes</span>
            <span className="med-stat-val" style={{ color: '#0284c7' }}>
              {changeSummary?.total_changes ?? 0}
            </span>
            <span className="med-stat-sub">
              {changeSummary?.dose_changes_count ?? 0} dose • {changeSummary?.started_count ?? 0} started
            </span>
          </div>

          <div className="med-stat-box">
            <span className="med-stat-label">Discontinued / Stopped</span>
            <span className="med-stat-val" style={{ color: '#dc2626' }}>
              {medSummary?.stopped_count ?? 0}
            </span>
            <span className="med-stat-sub">Explicit Cessations</span>
          </div>

          <div className="med-stat-box">
            <span className="med-stat-label">Total Documented</span>
            <span className="med-stat-val">
              {medSummary?.total_medications ?? 0}
            </span>
            <span className="med-stat-sub">Across All Records</span>
          </div>
        </div>
      </header>

      {/* ── Tab Switcher ── */}
      <nav className="med-tab-bar" aria-label="Medication View Sub-navigation">
        <button
          type="button"
          className={`med-tab-btn ${activeTab === 'prescriptions' ? 'active' : ''}`}
          onClick={() => setActiveTab('prescriptions')}
        >
          <span>💊 Prescriptions &amp; Regimens</span>
          <span className="tab-count-badge">{medSummary?.total_medications ?? 0}</span>
        </button>
        <button
          type="button"
          className={`med-tab-btn ${activeTab === 'changes' ? 'active' : ''}`}
          onClick={() => setActiveTab('changes')}
        >
          <span>🔄 Medication Changes &amp; Timeline</span>
          <span className="tab-count-badge">{changeSummary?.total_changes ?? 0}</span>
        </button>
      </nav>

      {/* ── TAB 1: PRESCRIPTIONS & REGIMENS ── */}
      {activeTab === 'prescriptions' && (
        <>
          <div className="med-controls-card">
            <div className="med-search-wrap">
              <span style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }}>🔍</span>
              <input
                type="text"
                className="med-search-input"
                placeholder="Search medication name, generic name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search medications"
              />
            </div>

            <div className="med-status-pills" role="tablist" aria-label="Medication status filter">
              {['ALL', 'ACTIVE', 'STOPPED', 'HISTORICAL', 'UNKNOWN'].map((st) => (
                <button
                  key={st}
                  type="button"
                  className={`med-filter-pill ${selectedStatus === st ? 'active' : ''}`}
                  onClick={() => setSelectedStatus(st)}
                  role="tab"
                  aria-selected={selectedStatus === st}
                >
                  {st === 'ALL' ? 'All Records' : st}
                </button>
              ))}
            </div>
          </div>

          {medLoading ? (
            <div className="timeline-skeleton" aria-busy="true"><div className="skeleton-item" /><div className="skeleton-item" /></div>
          ) : medError ? (
            <div className="timeline-error-card">
              <div className="error-icon">⚠️</div>
              <h2 className="error-title">Unable to Load Medication Information</h2>
              <p className="error-desc">{medError}</p>
              <button type="button" className="btn-retry" onClick={loadMedications}>Retry</button>
            </div>
          ) : meds.length === 0 ? (
            <div className="med-empty-card">
              <div className="med-empty-icon">💊</div>
              <h2 className="med-empty-title">No Documented Medications Found</h2>
              <p className="med-empty-desc">
                {searchQuery || selectedStatus !== 'ALL'
                  ? 'No medications matched your filter. Try adjusting your search query.'
                  : 'No documented medications found in the available record for this patient.'}
              </p>
            </div>
          ) : (
            <div className="med-list-container">
              {meds.map((m) => (
                <article key={m.id} className={`med-item-card ${m.is_conflict ? 'conflict-flagged' : ''}`}>
                  <div className="med-card-top">
                    <div className="med-name-group">
                      <h3 className="med-brand-name">{m.medication_name}</h3>
                      {m.generic_name && m.generic_name !== m.medication_name && (
                        <span className="med-generic-name">({m.generic_name})</span>
                      )}
                    </div>

                    <div className="badge-row">
                      <span className={`origin-chip ${m.origin.toLowerCase()}`}>
                        {m.origin === 'DERIVED' ? 'AI-Derived' : 'Documented Fact'}
                      </span>
                      <span className={`status-chip ${m.status.toLowerCase()}`}>
                        {m.status}
                      </span>
                    </div>
                  </div>

                  {/* Regimen Details */}
                  <div className="med-regimen-row">
                    <div className="regimen-item">
                      <span>Dose: </span>
                      <strong>{m.dosage ? `${m.dosage} ${m.dose_unit || ''}` : 'Not documented'}</strong>
                    </div>
                    <div className="regimen-item">
                      <span>Route: </span>
                      <strong>{m.route || 'Oral'}</strong>
                    </div>
                    <div className="regimen-item">
                      <span>Frequency: </span>
                      <strong>{m.frequency || 'Not documented'}</strong>
                    </div>
                    <div className="regimen-item">
                      <span>Start Date: </span>
                      <strong>{m.display_start_date}</strong>
                    </div>
                    {m.display_end_date && (
                      <div className="regimen-item">
                        <span>Stopped Date: </span>
                        <strong style={{ color: '#dc2626' }}>{m.display_end_date}</strong>
                      </div>
                    )}
                  </div>

                  {/* Conflict Flag */}
                  {m.is_conflict && (
                    <div className="med-conflict-alert" role="alert">
                      <span>⚠️</span>
                      <div>
                        <strong>Conflicting Documented Regimen: </strong>
                        {m.conflict_details}
                      </div>
                    </div>
                  )}

                  {/* Source Footer */}
                  <div className="med-source-footer">
                    <div>
                      {m.source.document_name && (
                        <span className="source-doc-pill">📄 {m.source.document_name}</span>
                      )}
                      {m.source.page_number && (
                        <span className="source-page-pill" style={{ marginLeft: '0.4rem' }}>
                          Page {m.source.page_number}
                        </span>
                      )}
                      {m.source.document_id && onInspectDocument && (
                        <button
                          type="button"
                          className="btn-text-snippet"
                          style={{ marginLeft: '0.5rem' }}
                          onClick={() => onInspectDocument(m.source.document_id!)}
                        >
                          Inspect Doc ↗
                        </button>
                      )}
                    </div>

                    {m.source.source_snippet && (
                      <button
                        type="button"
                        className="btn-text-snippet"
                        onClick={() => toggleSnippet(m.id)}
                        aria-expanded={expandedSnippetId === m.id}
                      >
                        {expandedSnippetId === m.id ? 'Hide Source Snippet ▲' : 'View Source Snippet ▼'}
                      </button>
                    )}
                  </div>

                  {expandedSnippetId === m.id && m.source.source_snippet && (
                    <div className="snippet-drawer">
                      <span className="snippet-tag">Authentic Record Citation:</span>
                      "{m.source.source_snippet}"
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── TAB 2: MEDICATION CHANGES & TIMELINE ── */}
      {activeTab === 'changes' && (
        <>
          <div className="med-controls-card">
            <div className="med-status-pills" role="tablist" aria-label="Change type filter">
              {['ALL', 'STARTED', 'STOPPED', 'DOSE_CHANGED', 'FREQUENCY_CHANGED', 'ROUTE_CHANGED'].map((ct) => (
                <button
                  key={ct}
                  type="button"
                  className={`med-filter-pill ${selectedChangeType === ct ? 'active' : ''}`}
                  onClick={() => setSelectedChangeType(ct)}
                  role="tab"
                  aria-selected={selectedChangeType === ct}
                >
                  {ct === 'ALL' ? 'All Changes' : ct.replace('_', ' ').toLowerCase()}
                </button>
              ))}
            </div>
          </div>

          {changesLoading ? (
            <div className="timeline-skeleton"><div className="skeleton-item" /><div className="skeleton-item" /></div>
          ) : changes.length === 0 ? (
            <div className="med-empty-card">
              <div className="med-empty-icon">🔄</div>
              <h2 className="med-empty-title">No Documented Medication Changes Found</h2>
              <p className="med-empty-desc">
                No medication starts, cessations, or dose transitions found in the available patient records.
              </p>
            </div>
          ) : (
            <div className="changes-table-card">
              <table className="changes-table" aria-label="Medication Change History">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Medication</th>
                    <th>Change Type</th>
                    <th>Transition (Previous → New)</th>
                    <th>Clinical Rationale / Notes</th>
                    <th>Classification</th>
                    <th>Source Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((c) => (
                    <tr key={c.id}>
                      <td style={{ whiteSpace: 'nowrap', fontWeight: 600 }}>{c.display_date}</td>
                      <td>
                        <strong>{c.medication_name}</strong>
                      </td>
                      <td>
                        <span className={`change-type-pill ${c.change_type.toLowerCase()}`}>
                          {c.change_type_label}
                        </span>
                      </td>
                      <td>
                        {c.change_type === 'DOSE_CHANGED' && c.previous_value && c.new_value ? (
                          <span className="dose-transition-row">
                            <span className="dose-prev">{c.previous_value}</span>
                            <span className="dose-arrow">→</span>
                            <span className="dose-next">{c.new_value}</span>
                          </span>
                        ) : c.new_value ? (
                          <span>{c.new_value}</span>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>—</span>
                        )}
                      </td>
                      <td style={{ maxWidth: '280px', color: '#475569' }}>
                        {c.description}
                      </td>
                      <td>
                        <span className={`origin-chip ${c.origin.toLowerCase()}`}>
                          {c.origin === 'DERIVED' ? 'AI-Derived' : 'Documented'}
                        </span>
                      </td>
                      <td>
                        {c.source.document_name ? (
                          <div style={{ fontSize: '0.8rem' }}>
                            {onInspectDocument && c.source.document_id ? (
                              <button
                                type="button"
                                style={{ background: 'none', border: 'none', padding: 0, color: '#2563eb', cursor: 'pointer', textDecoration: 'underline', font: 'inherit' }}
                                onClick={() => onInspectDocument(c.source.document_id!)}
                              >
                                📄 {c.source.document_name}
                              </button>
                            ) : (
                              <span>📄 {c.source.document_name}</span>
                            )}
                            {c.source.page_number && <span> (p. {c.source.page_number})</span>}
                          </div>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>Derived from sequential notes</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
