/**
 * MedBrief AI — Clinical Document Composers & Drafts Workspace
 * Step 13: Referral / Discharge / Handoff Clinical Composers & Editable Draft Workflow
 *
 * Dedicated physician workspace for:
 * - Composing AI-generated Referral Letters, Discharge Summaries, and Clinical Handoffs
 * - Multi-draft version history per patient (non-destructive persistence)
 * - Grounded evidence citations linking clinical statements to exact source records
 * - Complete clinician review & editing workflow with explicit doctor sign-off / approval
 * - Prominent "AI GENERATED DRAFT — CLINICIAN REVIEW REQUIRED" safety badge
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord } from '../../types/patient'
import type {
  DraftType,
  DraftStatus,
  DraftItem,
  DraftDetail,
  DraftEvidenceCitation,
} from '../../types/draft'
import { fetchPatients } from '../../services/patientApi'
import {
  fetchPatientDrafts,
  generatePatientDraft,
  fetchDraftById,
  updateDraft,
} from '../../services/draftApi'
import { useToast } from '../../context/ToastContext'
import './DraftsView.css'

interface DraftsViewProps {
  targetPatient?: PatientRecord
  patients?: PatientRecord[]
  onPatientChange?: (patient: PatientRecord) => void
  onSelectPatient?: () => void
}

const DRAFT_TYPES: { type: DraftType; label: string; desc: string; icon: string }[] = [
  {
    type: 'REFERRAL',
    label: 'Referral Letter',
    desc: 'Structured consultant referral letter with reason, history, meds & clinical questions',
    icon: '📨',
  },
  {
    type: 'DISCHARGE',
    label: 'Discharge Summary',
    desc: 'Hospital course, verified diagnoses, reconciled discharge meds & follow-up plan',
    icon: '🏥',
  },
  {
    type: 'HANDOFF',
    label: 'Clinical Handoff',
    desc: 'Inter-shift / transfer briefing on active clinical issues & outstanding investigations',
    icon: '🔄',
  },
]

export const DraftsView: React.FC<DraftsViewProps> = ({
  targetPatient,
  patients: propPatients,
  onPatientChange,
}) => {
  const { showToast } = useToast()
  const [patients, setPatients] = useState<PatientRecord[]>(propPatients || [])
  const [selectedPatientId, setSelectedPatientId] = useState<string>(targetPatient?.id || '')
  const [currentPatient, setCurrentPatient] = useState<PatientRecord | null>(targetPatient || null)

  // Composer state
  const [selectedType, setSelectedType] = useState<DraftType>('REFERRAL')
  const [recipientInfo, setRecipientInfo] = useState<string>('')
  const [customInstructions, setCustomInstructions] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [generationError, setGenerationError] = useState<string | null>(null)

  // Drafts history & active draft state
  const [draftsList, setDraftsList] = useState<DraftItem[]>([])
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null)
  const [activeDraftDetail, setActiveDraftDetail] = useState<DraftDetail | null>(null)
  const [loadingList, setLoadingList] = useState<boolean>(false)
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false)

  // Editing state
  const [editableTitle, setEditableTitle] = useState<string>('')
  const [editableContent, setEditableContent] = useState<string>('')
  const [isSaving, setIsSaving] = useState<boolean>(false)
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'editor' | 'structured' | 'evidence'>('editor')
  const [copyFeedback, setCopyFeedback] = useState<boolean>(false)

  // Citation modal state
  const [activeCitation, setActiveCitation] = useState<DraftEvidenceCitation | null>(null)

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

  // 2. Load Patient Drafts
  const loadDrafts = useCallback(async (patientId: string) => {
    if (!patientId) return
    setLoadingList(true)
    try {
      const res = await fetchPatientDrafts(patientId)
      setDraftsList(res.items)
      if (res.items.length > 0) {
        setSelectedDraftId(res.items[0].id)
      } else {
        setSelectedDraftId(null)
        setActiveDraftDetail(null)
      }
    } catch (err) {
      console.error('Error fetching drafts list:', err)
      setDraftsList([])
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    if (selectedPatientId) {
      loadDrafts(selectedPatientId)
    }
  }, [selectedPatientId, loadDrafts])

  // 3. Load Selected Draft Detail
  useEffect(() => {
    if (!selectedDraftId) {
      setActiveDraftDetail(null)
      setEditableTitle('')
      setEditableContent('')
      return
    }
    setLoadingDetail(true)
    fetchDraftById(selectedDraftId)
      .then((detail) => {
        setActiveDraftDetail(detail)
        setEditableTitle(detail.title)
        setEditableContent(detail.content)
      })
      .catch((err) => {
        console.error('Error fetching draft detail:', err)
        setActiveDraftDetail(null)
      })
      .finally(() => setLoadingDetail(false))
  }, [selectedDraftId])

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

  // 5. Handle AI Draft Generation
  const handleGenerate = async () => {
    if (!selectedPatientId || isGenerating) return
    setIsGenerating(true)
    setGenerationError(null)

    try {
      const generated = await generatePatientDraft(selectedPatientId, {
        draft_type: selectedType,
        recipient_info: recipientInfo.trim() || undefined,
        custom_instructions: customInstructions.trim() || undefined,
      })
      await loadDrafts(selectedPatientId)
      setSelectedDraftId(generated.id)
      setActiveDraftDetail(generated)
      setEditableTitle(generated.title)
      setEditableContent(generated.content)
      setCustomInstructions('')
      setRecipientInfo('')
      showToast('AI clinical draft generated successfully.', 'success')
    } catch (err: any) {
      console.error('Failed to generate clinical draft:', err)
      const msg = err.message || 'Error communicating with AI synthesis service.'
      setGenerationError(msg)
      showToast(msg, 'error')
    } finally {
      setIsGenerating(false)
    }
  }

  // 6. Handle Save Draft Changes
  const handleSaveDraft = async (newStatus?: DraftStatus) => {
    if (!selectedDraftId || isSaving) return
    setIsSaving(true)
    setSaveSuccessMsg(null)

    try {
      const updated = await updateDraft(selectedDraftId, {
        title: editableTitle,
        content: editableContent,
        status: newStatus || (activeDraftDetail?.status === 'APPROVED' ? 'APPROVED' : 'IN_REVIEW'),
      })
      setActiveDraftDetail(updated)
      setEditableTitle(updated.title)
      setEditableContent(updated.content)
      const successText =
        newStatus === 'APPROVED'
          ? 'Draft signed off and approved successfully!'
          : 'Draft updates saved successfully.'
      setSaveSuccessMsg(successText)
      showToast(successText, 'success')
      setTimeout(() => setSaveSuccessMsg(null), 3500)
      // Refresh list to update status badge / title
      const res = await fetchPatientDrafts(selectedPatientId)
      setDraftsList(res.items)
    } catch (err: any) {
      const msg = err.message || 'Failed to save draft changes.'
      showToast(msg, 'error')
    } finally {
      setIsSaving(false)
    }
  }

  // 7. Handle Copy to Clipboard
  const handleCopyClipboard = () => {
    if (!editableContent) return
    navigator.clipboard.writeText(`${editableTitle}\n\n${editableContent}`).then(() => {
      setCopyFeedback(true)
      setTimeout(() => setCopyFeedback(false), 2500)
    })
  }

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'Not recorded'
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

  const getStatusBadge = (status: DraftStatus) => {
    switch (status) {
      case 'APPROVED':
        return <span className="status-badge approved">✓ Approved</span>
      case 'IN_REVIEW':
        return <span className="status-badge in-review">In Review</span>
      case 'ARCHIVED':
        return <span className="status-badge archived">Archived</span>
      case 'DRAFT':
      default:
        return <span className="status-badge draft">Draft</span>
    }
  }

  return (
    <div className="drafts-container">
      {/* ── Top Header ── */}
      <header className="drafts-header">
        <div className="drafts-title-group">
          <span className="drafts-icon">📋</span>
          <div>
            <h1 className="drafts-title">Referral &amp; Discharge Clinical Composers</h1>
            <p className="drafts-subtitle">
              AI-composed clinical correspondence with doctor sign-off workflow and grounded source evidence.
              {currentPatient && (
                <span> &bull; Active: <strong>{currentPatient.first_name} {currentPatient.last_name}</strong> ({currentPatient.mrn})</span>
              )}
            </p>
          </div>
        </div>

        <div className="patient-picker">
          <label htmlFor="draft-patient-select">Patient:</label>
          <select
            id="draft-patient-select"
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

      {/* ── Composer Control Panel ── */}
      <section className="draft-composer-panel" aria-label="Clinical Draft Generation Controls">
        <div className="panel-header">
          <div className="panel-title">
            <span>✨</span> Compose Clinical Document Draft
          </div>
          <span className="badge-pill model">Gemini AI Synthesis Gateway</span>
        </div>

        <div className="composer-type-selector">
          {DRAFT_TYPES.map((t) => (
            <button
              key={t.type}
              type="button"
              className={`type-btn ${selectedType === t.type ? 'active' : ''}`}
              onClick={() => setSelectedType(t.type)}
            >
              <div className="type-name">
                {t.icon} {t.label}
              </div>
              <div className="type-desc">{t.desc}</div>
            </button>
          ))}
        </div>

        <div className="composer-inputs-row">
          <input
            type="text"
            className="composer-input recipient-input"
            placeholder="Recipient (e.g. 'Dr. Sarah Jenkins, Dept of Cardiology, St. Jude')..."
            value={recipientInfo}
            onChange={(e) => setRecipientInfo(e.target.value)}
            disabled={isGenerating}
          />
          <input
            type="text"
            className="composer-input instructions-input"
            placeholder="Clinician instructions (e.g. 'Focus on post-discharge medication reconciliation')..."
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
                <span className="spinner" /> Synthesizing Draft...
              </>
            ) : (
              <>
                <span>🚀</span> Generate AI Draft
              </>
            )}
          </button>
        </div>

        {generationError && (
          <div className="generation-error-banner" role="alert">
            <span>⚠️</span> {generationError}
          </div>
        )}
      </section>

      {/* ── Main Workspace: Split View ── */}
      <div className="drafts-workspace-grid">
        {/* Left Column: Drafts History / Versions */}
        <aside className="drafts-sidebar">
          <div className="sidebar-header">
            <h3>Document Drafts ({draftsList.length})</h3>
            <span className="version-tag">Non-destructive</span>
          </div>

          {loadingList ? (
            <div className="loading-state">
              <span className="spinner" /> Loading drafts...
            </div>
          ) : draftsList.length === 0 ? (
            <div className="empty-drafts-list">
              <span className="empty-icon">📝</span>
              <p>No drafts generated for this patient yet.</p>
              <span className="hint">Select a document type above and click "Generate AI Draft".</span>
            </div>
          ) : (
            <div className="drafts-list-scroll">
              {draftsList.map((draft) => {
                const isSelected = draft.id === selectedDraftId
                return (
                  <div
                    key={draft.id}
                    className={`draft-list-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedDraftId(draft.id)}
                  >
                    <div className="card-top-row">
                      <span className="draft-type-tag">{draft.draft_type_label}</span>
                      {getStatusBadge(draft.status)}
                    </div>
                    <div className="draft-card-title">{draft.title}</div>
                    <div className="card-bottom-row">
                      <span className="draft-date">{formatDate(draft.created_at)}</span>
                      {draft.evidence_count > 0 && (
                        <span className="evidence-pill">📎 {draft.evidence_count} sources</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </aside>

        {/* Right Column: Draft Editor & Approval Suite */}
        <main className="draft-editor-pane">
          {loadingDetail ? (
            <div className="loading-state full">
              <span className="spinner" /> Retrieving clinical document...
            </div>
          ) : !activeDraftDetail ? (
            <div className="no-draft-selected">
              <span>📄</span>
              <h3>No Draft Selected</h3>
              <p>Select a draft from the history panel or generate a new clinical letter.</p>
            </div>
          ) : (
            <div className="draft-content-card">
              {/* Review / Status Banner */}
              {activeDraftDetail.status === 'APPROVED' ? (
                <div className="clinician-review-banner approved" role="status">
                  <div className="banner-icon">✅</div>
                  <div className="banner-content">
                    <h4>DOCTOR APPROVED CLINICAL DOCUMENT</h4>
                    <p>
                      Formally verified and approved by Clinician on{' '}
                      <strong>{formatDate(activeDraftDetail.reviewed_at)}</strong>. Ready for clinical dispatch.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="clinician-review-banner pending" role="status">
                  <div className="banner-icon">⚠️</div>
                  <div className="banner-content">
                    <h4>AI GENERATED DRAFT — CLINICIAN REVIEW REQUIRED</h4>
                    <p>
                      This draft was synthesized from patient medical records. Clinician review, editing, and sign-off are required prior to clinical transmission.
                    </p>
                  </div>
                </div>
              )}

              {saveSuccessMsg && (
                <div className="save-success-banner" role="status">
                  <span>✓</span> {saveSuccessMsg}
                </div>
              )}

              {/* Title & Action Toolbar */}
              <div className="editor-toolbar">
                <input
                  type="text"
                  className="editable-title-input"
                  value={editableTitle}
                  onChange={(e) => setEditableTitle(e.target.value)}
                  placeholder="Document Title..."
                />

                <div className="toolbar-actions">
                  <button
                    type="button"
                    className="action-btn copy-btn"
                    onClick={handleCopyClipboard}
                    title="Copy full text to clipboard"
                  >
                    {copyFeedback ? '✓ Copied!' : '📋 Copy Text'}
                  </button>

                  <button
                    type="button"
                    className="action-btn save-btn"
                    onClick={() => handleSaveDraft('IN_REVIEW')}
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : '💾 Save Draft'}
                  </button>

                  {activeDraftDetail.status !== 'APPROVED' ? (
                    <button
                      type="button"
                      className="action-btn approve-btn"
                      onClick={() => handleSaveDraft('APPROVED')}
                      disabled={isSaving}
                      title="Sign off and lock document as approved"
                    >
                      {isSaving ? 'Processing...' : '✓ Sign-off & Approve'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="action-btn revert-btn"
                      onClick={() => handleSaveDraft('IN_REVIEW')}
                      disabled={isSaving}
                      title="Reopen approved draft for revisions"
                    >
                      Reopen for Edit
                    </button>
                  )}
                </div>
              </div>

              {/* View Tabs */}
              <div className="draft-view-tabs">
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'editor' ? 'active' : ''}`}
                  onClick={() => setActiveTab('editor')}
                >
                  ✏️ Editable Document Body
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'structured' ? 'active' : ''}`}
                  onClick={() => setActiveTab('structured')}
                >
                  📑 Structured Sections &amp; Citations ({activeDraftDetail.structured_sections.length})
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
                  onClick={() => setActiveTab('evidence')}
                >
                  📎 Grounded Evidence ({activeDraftDetail.evidence_references.length})
                </button>
              </div>

              {/* Tab 1: Editable Document Textarea */}
              {activeTab === 'editor' && (
                <div className="editor-tab-body">
                  <div className="editor-helper-row">
                    <span className="helper-text">
                      Physicians can directly edit, amend, or redact any statements below.
                    </span>
                    <span className="char-count">
                      {editableContent.length} chars &bull; {editableContent.split(/\s+/).filter(Boolean).length} words
                    </span>
                  </div>
                  <textarea
                    className="draft-textarea"
                    value={editableContent}
                    onChange={(e) => setEditableContent(e.target.value)}
                    rows={22}
                    placeholder="Enter clinical document text..."
                  />
                </div>
              )}

              {/* Tab 2: Structured Sections & Citations */}
              {activeTab === 'structured' && (
                <div className="structured-tab-body">
                  {activeDraftDetail.structured_sections.map((section) => (
                    <div key={section.section_key} className="structured-section-card">
                      <h4 className="section-title">{section.title}</h4>
                      {section.content_text && (
                        <p className="section-content-text">{section.content_text}</p>
                      )}
                      {section.bullet_points.length > 0 && (
                        <ul className="bullet-points-list">
                          {section.bullet_points.map((pt, idx) => (
                            <li key={idx} className="bullet-item">
                              <span className="statement-text">{pt.statement}</span>
                              {pt.is_uncertain && (
                                <span className="uncertain-badge" title={pt.uncertainty_note || 'Clinical uncertainty flagged'}>
                                  ⚠️ Suspected / Unconfirmed
                                </span>
                              )}
                              {pt.citations.map((cite, cIdx) => (
                                <button
                                  key={cIdx}
                                  type="button"
                                  className="citation-pill-btn"
                                  onClick={() => setActiveCitation(cite)}
                                  title="View grounded record snippet"
                                >
                                  📎 {cite.document_name || 'Document'} {cite.page_number ? `(p. ${cite.page_number})` : ''}
                                </button>
                              ))}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 3: Source Evidence References */}
              {activeTab === 'evidence' && (
                <div className="evidence-tab-body">
                  {activeDraftDetail.evidence_references.length === 0 ? (
                    <p className="no-evidence-msg">No direct source snippets indexed for this draft.</p>
                  ) : (
                    <div className="evidence-grid">
                      {activeDraftDetail.evidence_references.map((ev) => (
                        <div
                          key={ev.id}
                          className="evidence-ref-card"
                          onClick={() =>
                            setActiveCitation({
                              document_id: ev.document_id,
                              document_name: ev.document_name,
                              page_number: ev.page_number,
                              document_page_id: ev.document_page_id,
                              source_snippet: ev.source_text,
                              source_section: ev.source_section,
                            })
                          }
                        >
                          <div className="ev-header">
                            <span className="ev-doc-title">
                              📄 {ev.document_name || 'Medical Document'}
                            </span>
                            {ev.page_number && <span className="ev-page">Pg. {ev.page_number}</span>}
                          </div>
                          {ev.source_section && <div className="ev-section">{ev.source_section}</div>}
                          <blockquote className="ev-snippet">"{ev.source_text}"</blockquote>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Footer Audit Metadata */}
              <div className="draft-audit-footer">
                <span>Model: {activeDraftDetail.model_name || 'Gemini 2.5 Flash'}</span>
                <span>Created: {formatDate(activeDraftDetail.created_at)}</span>
                {activeDraftDetail.reviewed_at && (
                  <span>Reviewed: {formatDate(activeDraftDetail.reviewed_at)}</span>
                )}
                <span className="ai-provenance">100% Grounded in Patient Records</span>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── Grounded Citation Verification Drawer / Modal ── */}
      {activeCitation && (
        <div className="citation-modal-backdrop" onClick={() => setActiveCitation(null)}>
          <div
            className="citation-modal-content"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Source Document Citation"
          >
            <div className="modal-header">
              <div className="modal-title-row">
                <span className="modal-icon">🔍</span>
                <div>
                  <h3>Grounded Source Verification</h3>
                  <p className="modal-subtitle">
                    Verbatim record text directly supporting this clinical assertion
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setActiveCitation(null)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="meta-box">
                <div className="meta-item">
                  <span className="label">Source Document:</span>
                  <span className="val">{activeCitation.document_name || 'Clinical Document'}</span>
                </div>
                {activeCitation.page_number && (
                  <div className="meta-item">
                    <span className="label">Page Number:</span>
                    <span className="val">Page {activeCitation.page_number}</span>
                  </div>
                )}
                {activeCitation.source_section && (
                  <div className="meta-item">
                    <span className="label">Section:</span>
                    <span className="val">{activeCitation.source_section}</span>
                  </div>
                )}
              </div>

              <div className="excerpt-box">
                <div className="excerpt-title">Verbatim Medical Record Excerpt</div>
                <blockquote className="verbatim-quote">"{activeCitation.source_snippet}"</blockquote>
              </div>

              <div className="safety-callout">
                <span className="check-icon">🛡️</span>
                <span>
                  <strong>Hallucination Guard:</strong> This fact is 100% grounded in the extracted text of the patient's uploaded documentation.
                </span>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-btn-primary"
                onClick={() => setActiveCitation(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
