/**
 * MedBrief AI — Diagnostic Investigation & Outstanding Items Workspace
 * Step 11: Medication + Investigation Intelligence
 *
 * Clinical investigation intelligence:
 * - Structured diagnostic tests, lab panels, and imaging reports
 * - Strict status rules: Only mark PENDING when explicitly supported in documentation
 * - Doctor-facing Outstanding Items (Pending tests, Follow-up consults, Monitoring)
 * - Highlights abnormal values & clinical urgencies without alarming the clinician
 * - Source traceability with expandable verbatim snippets
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord } from '../../types/patient'
import type {
  InvestigationItem,
  InvestigationSummaryStats,
  OutstandingItem,
  OutstandingSummaryStats,
} from '../../types/intelligence'
import { fetchPatients } from '../../services/patientApi'
import {
  fetchPatientInvestigations,
  fetchPatientOutstandingItems,
} from '../../services/intelligenceApi'
import { useDebounce } from '../../hooks/useDebounce'
import './InvestigationsView.css'

interface InvestigationsViewProps {
  targetPatient?: PatientRecord
  patients?: PatientRecord[]
  onPatientChange?: (patient: PatientRecord) => void
  onSelectPatient?: () => void
  onInspectDocument?: (documentId: string) => void
}

type InvTab = 'investigations' | 'outstanding'

export const InvestigationsView: React.FC<InvestigationsViewProps> = ({
  targetPatient,
  patients: propPatients,
  onPatientChange,
  onInspectDocument,
}) => {
  const [patients, setPatients] = useState<PatientRecord[]>(propPatients || [])
  const [selectedPatientId, setSelectedPatientId] = useState<string>(targetPatient?.id || '')
  const [currentPatient, setCurrentPatient] = useState<PatientRecord | null>(targetPatient || null)

  const [activeTab, setActiveTab] = useState<InvTab>('investigations')

  // Investigations state
  const [invs, setInvs] = useState<InvestigationItem[]>([])
  const [invSummary, setInvSummary] = useState<InvestigationSummaryStats | null>(null)
  const [invLoading, setInvLoading] = useState<boolean>(true)
  const [invError, setInvError] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const debouncedSearch = useDebounce(searchQuery, 300)

  // Outstanding Items state
  const [outstanding, setOutstanding] = useState<OutstandingItem[]>([])
  const [outSummary, setOutSummary] = useState<OutstandingSummaryStats | null>(null)
  const [outLoading, setOutLoading] = useState<boolean>(true)

  // Snippet toggle
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

  // 2. Fetch Investigations
  const loadInvestigations = useCallback(async () => {
    if (!selectedPatientId) return
    setInvLoading(true)
    setInvError(null)

    try {
      const data = await fetchPatientInvestigations(selectedPatientId, {
        status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        search: debouncedSearch.trim() || undefined,
        pageSize: 100,
      })
      setInvs(data.items)
      setInvSummary(data.summary)
    } catch (err: any) {
      setInvError(err.message || 'Failed to load investigations')
    } finally {
      setInvLoading(false)
    }
  }, [selectedPatientId, selectedStatus, debouncedSearch])

  // 3. Fetch Outstanding Items
  const loadOutstanding = useCallback(async () => {
    if (!selectedPatientId) return
    setOutLoading(true)

    try {
      const data = await fetchPatientOutstandingItems(selectedPatientId, {
        pageSize: 100,
      })
      setOutstanding(data.items)
      setOutSummary(data.summary)
    } catch (err: any) {
      console.error('Failed to load outstanding items:', err)
    } finally {
      setOutLoading(false)
    }
  }, [selectedPatientId])

  useEffect(() => {
    loadInvestigations()
    loadOutstanding()
  }, [loadInvestigations, loadOutstanding])

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
    <div className="investigations-view-container" role="main" aria-label="Investigation Intelligence Workspace">
      {/* ── Patient Context Header ── */}
      <header className="inv-header-card">
        <div className="inv-header-top">
          <div className="inv-patient-info">
            <div className="inv-avatar-pill" aria-hidden="true">🧪</div>
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

            <button
              type="button"
              className="btn-med-refresh"
              onClick={() => {
                loadInvestigations()
                loadOutstanding()
              }}
              title="Refresh investigation records"
            >
              <span>🔄</span> Refresh
            </button>
          </div>
        </div>

        {/* ── Summary Stats Ribbon ── */}
        <div className="inv-stats-ribbon" aria-label="Investigation Statistics">
          <div className="inv-stat-box">
            <span className="inv-stat-label">Completed Tests</span>
            <span className="inv-stat-val" style={{ color: '#16a34a' }}>
              {invSummary?.completed_count ?? 0}
            </span>
            <span className="inv-stat-sub">With Documented Results</span>
          </div>

          <div className="inv-stat-box">
            <span className="inv-stat-label">Explicitly Pending</span>
            <span className="inv-stat-val" style={{ color: '#d97706' }}>
              {invSummary?.pending_count ?? 0}
            </span>
            <span className="inv-stat-sub">Documented Awaiting Results</span>
          </div>

          <div className="inv-stat-box">
            <span className="inv-stat-label">Abnormal Findings</span>
            <span className="inv-stat-val" style={{ color: '#dc2626' }}>
              {invSummary?.abnormal_count ?? 0}
            </span>
            <span className="inv-stat-sub">Flagged Out-of-Range</span>
          </div>

          <div className="inv-stat-box">
            <span className="inv-stat-label">Outstanding Items</span>
            <span className="inv-stat-val" style={{ color: '#0d9488' }}>
              {outSummary?.open_count ?? 0}
            </span>
            <span className="inv-stat-sub">Follow-ups &amp; Action Items</span>
          </div>
        </div>
      </header>

      {/* ── Tab Switcher ── */}
      <nav className="inv-tab-bar" aria-label="Investigation Workspace Navigation">
        <button
          type="button"
          className={`inv-tab-btn ${activeTab === 'investigations' ? 'active' : ''}`}
          onClick={() => setActiveTab('investigations')}
        >
          <span>🧪 Diagnostic Reports &amp; Labs</span>
          <span className="tab-count-badge">{invSummary?.total_investigations ?? 0}</span>
        </button>
        <button
          type="button"
          className={`inv-tab-btn ${activeTab === 'outstanding' ? 'active' : ''}`}
          onClick={() => setActiveTab('outstanding')}
        >
          <span>📋 Outstanding Items &amp; Follow-ups</span>
          <span className="tab-count-badge">{outSummary?.total_outstanding ?? 0}</span>
        </button>
      </nav>

      {/* ── TAB 1: DIAGNOSTIC INVESTIGATIONS ── */}
      {activeTab === 'investigations' && (
        <>
          <div className="inv-controls-card">
            <div className="inv-search-wrap">
              <span style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }}>🔍</span>
              <input
                type="text"
                className="inv-search-input"
                placeholder="Search test name, lab result summary..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search investigations"
              />
            </div>

            <div className="inv-filter-pills" role="tablist" aria-label="Status filter">
              {['ALL', 'COMPLETED', 'PENDING', 'ORDERED', 'CANCELLED', 'UNKNOWN'].map((st) => (
                <button
                  key={st}
                  type="button"
                  className={`inv-filter-pill ${selectedStatus === st ? 'active' : ''}`}
                  onClick={() => setSelectedStatus(st)}
                  role="tab"
                  aria-selected={selectedStatus === st}
                >
                  {st === 'ALL' ? 'All Tests' : st}
                </button>
              ))}
            </div>
          </div>

          {invLoading ? (
            <div className="timeline-skeleton"><div className="skeleton-item" /><div className="skeleton-item" /></div>
          ) : invError ? (
            <div className="timeline-error-card">
              <div className="error-icon">⚠️</div>
              <h2 className="error-title">Unable to Load Investigation Records</h2>
              <p className="error-desc">{invError}</p>
              <button type="button" className="btn-retry" onClick={loadInvestigations}>Retry</button>
            </div>
          ) : invs.length === 0 ? (
            <div className="med-empty-card">
              <div className="med-empty-icon">🧪</div>
              <h2 className="med-empty-title">No Documented Investigations Found</h2>
              <p className="med-empty-desc">
                {searchQuery || selectedStatus !== 'ALL'
                  ? 'No investigations matched your filter.'
                  : 'No diagnostic investigations documented in the uploaded medical records.'}
              </p>
            </div>
          ) : (
            <div className="inv-table-card">
              <table className="inv-table" aria-label="Investigations Directory">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Investigation Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Documented Result</th>
                    <th>Reference Range</th>
                    <th>Source Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {invs.map((inv) => (
                    <tr key={inv.id}>
                      <td style={{ whiteSpace: 'nowrap', fontWeight: 600 }}>{inv.display_date}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <strong>{inv.investigation_name}</strong>
                          {inv.is_abnormal && <span className="abnormal-badge">Abnormal</span>}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.8rem', color: '#64748b', textTransform: 'uppercase' }}>
                          {inv.investigation_type}
                        </span>
                      </td>
                      <td>
                        <span className={`inv-status-chip ${inv.status.toLowerCase()}`}>
                          {inv.status}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: inv.is_abnormal ? 700 : 400, color: inv.is_abnormal ? '#b91c1c' : '#1e293b' }}>
                          {inv.result_summary || (inv.status === 'PENDING' ? 'Awaiting report' : 'No result documented')}
                        </span>
                      </td>
                      <td style={{ color: '#64748b' }}>
                        {inv.reference_range || '—'}
                      </td>
                      <td>
                        {inv.source.document_name ? (
                          <div style={{ fontSize: '0.8rem' }}>
                            {onInspectDocument && inv.source.document_id ? (
                              <button
                                type="button"
                                style={{ background: 'none', border: 'none', padding: 0, color: '#2563eb', cursor: 'pointer', textDecoration: 'underline', font: 'inherit' }}
                                onClick={() => onInspectDocument(inv.source.document_id!)}
                              >
                                📄 {inv.source.document_name}
                              </button>
                            ) : (
                              <span>📄 {inv.source.document_name}</span>
                            )}
                            {inv.source.page_number && <span> (p. {inv.source.page_number})</span>}
                            {inv.source.source_snippet && (
                              <div>
                                <button
                                  type="button"
                                  className="btn-text-snippet"
                                  onClick={() => toggleSnippet(inv.id)}
                                >
                                  {expandedSnippetId === inv.id ? 'Hide Citation ▲' : 'Citation ▼'}
                                </button>
                                {expandedSnippetId === inv.id && (
                                  <div className="snippet-drawer">"{inv.source.source_snippet}"</div>
                                )}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>—</span>
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

      {/* ── TAB 2: OUTSTANDING CLINICAL ITEMS ── */}
      {activeTab === 'outstanding' && (
        <>
          {outLoading ? (
            <div className="timeline-skeleton"><div className="skeleton-item" /><div className="skeleton-item" /></div>
          ) : outstanding.length === 0 ? (
            <div className="med-empty-card">
              <div className="med-empty-icon">✅</div>
              <h2 className="med-empty-title">No Documented Outstanding Items Found</h2>
              <p className="med-empty-desc">
                No unresolved lab orders, follow-up consults, or monitoring instructions are documented as pending.
              </p>
            </div>
          ) : (
            <div className="outstanding-cards-list">
              {outstanding.map((item) => (
                <article
                  key={item.id}
                  className={`outstanding-card ${item.priority === 'HIGH' || item.priority === 'CRITICAL' ? 'high-prio' : ''}`}
                >
                  <div className="out-top-row">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <span className="inv-status-chip pending">{item.item_type_label}</span>
                      <h3 className="out-title">{item.title}</h3>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className={`urgency-badge ${item.priority.toLowerCase()}`}>
                        Priority: {item.priority}
                      </span>
                      <span className="status-chip active">{item.status}</span>
                    </div>
                  </div>

                  {item.description && <p className="out-desc">{item.description}</p>}

                  <div className="out-meta-row">
                    <span>Target Date: <strong>{item.display_due_date}</strong></span>
                    <span>•</span>
                    <span>Classification: <strong>{item.origin}</strong></span>
                    {item.source.document_name && (
                      <>
                        <span>•</span>
                        <span>📄 {item.source.document_name} {item.source.page_number ? `(p. ${item.source.page_number})` : ''}</span>
                      </>
                    )}
                    {item.source.source_snippet && (
                      <button
                        type="button"
                        className="btn-text-snippet"
                        onClick={() => toggleSnippet(item.id)}
                      >
                        {expandedSnippetId === item.id ? 'Hide Citation ▲' : 'View Citation ▼'}
                      </button>
                    )}
                  </div>

                  {expandedSnippetId === item.id && item.source.source_snippet && (
                    <div className="snippet-drawer">
                      <span className="snippet-tag">Record Citation:</span>
                      "{item.source.source_snippet}"
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
