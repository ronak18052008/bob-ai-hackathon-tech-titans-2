/**
 * MedBrief AI — Medical Document Detail & Preview Modal
 * Step 7: PDF / Medical Document Upload & Ingestion Foundation
 * Step 9: Medical Information Extraction
 *
 * Provides:
 * - Comprehensive document metadata inspection
 * - Processing job status monitoring
 * - Page-aware clinical extraction trigger & results inspection (Step 9)
 * - Grounded evidence reference citations for clinical auditability
 * - Authenticated, private PDF preview & secure download
 * - Processing retry trigger for failed ingestion jobs
 */

import React, { useState, useEffect, useCallback } from 'react'
import type {
  DocumentRecord,
  DocumentExtractionSummary,
  ExtractedEventItem,
  ExtractedMedicationItem,
  ExtractedInvestigationItem,
  ExtractedFollowUpItem,
} from '../../types/document'
import {
  streamDocumentBlob,
  retryDocumentProcessing,
  triggerDocumentExtraction,
  fetchDocumentExtraction,
} from '../../services/documentApi'
import './DocumentDetailModal.css'

interface DocumentDetailModalProps {
  isOpen: boolean
  onClose: () => void
  document: DocumentRecord | null
  onDocumentUpdated?: (updated: DocumentRecord) => void
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({
  isOpen,
  onClose,
  document: doc,
  onDocumentUpdated,
}) => {
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loadingFile, setLoadingFile] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
  const [loadingExtraction, setLoadingExtraction] = useState(false)
  const [extractionSummary, setExtractionSummary] = useState<DocumentExtractionSummary | null>(null)
  const [activeExtractionTab, setActiveExtractionTab] = useState<
    'conditions' | 'medications' | 'investigations' | 'procedures' | 'events' | 'follow_ups'
  >('conditions')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const loadExtractionData = useCallback(async (docId: string) => {
    setLoadingExtraction(true)
    try {
      const summary = await fetchDocumentExtraction(docId)
      setExtractionSummary(summary)
    } catch {
      // Extraction may not have been run yet — non-fatal
      setExtractionSummary(null)
    } finally {
      setLoadingExtraction(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen && doc) {
      if (doc.status === 'PROCESSED' || doc.status === 'PARTIAL') {
        loadExtractionData(doc.id)
      } else {
        setExtractionSummary(null)
      }
      if (doc.status === 'FAILED') {
        setErrorMsg('Medical extraction has not completed successfully for this document. Click "Retry Medical Extraction" to run the extraction pipeline.')
      } else {
        setErrorMsg(null)
      }
      setSuccessMsg(null)
    } else {
      setExtractionSummary(null)
      setErrorMsg(null)
      setSuccessMsg(null)
    }
  }, [isOpen, doc, loadExtractionData])

  if (!isOpen || !doc) return null

  const handlePreviewPdf = async () => {
    if (previewUrl) {
      setIsPreviewing(!isPreviewing)
      return
    }

    setLoadingFile(true)
    setErrorMsg(null)
    try {
      const { blob } = await streamDocumentBlob(doc.id)
      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
      setIsPreviewing(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to retrieve PDF binary.'
      setErrorMsg(msg)
    } finally {
      setLoadingFile(false)
    }
  }

  const handleDownloadPdf = async () => {
    setLoadingFile(true)
    setErrorMsg(null)
    try {
      const { blob, filename } = await streamDocumentBlob(doc.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename || doc.file_name
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to download PDF file.'
      setErrorMsg(msg)
    } finally {
      setLoadingFile(false)
    }
  }

  const handleRetry = async () => {
    setIsRetrying(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const updated = await retryDocumentProcessing(doc.id)
      if (onDocumentUpdated) {
        onDocumentUpdated(updated)
      }
      if (updated.status === 'FAILED') {
        setErrorMsg('Document text extraction failed. Please ensure the PDF is valid.')
      } else {
        setSuccessMsg('Document ingestion & page text extraction completed successfully.')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to re-process document ingestion.'
      setErrorMsg(msg)
      setSuccessMsg(null)
    } finally {
      setIsRetrying(false)
    }
  }

  const handleExtract = async () => {
    setIsExtracting(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const result = await triggerDocumentExtraction(doc.id)
      if (result.status === 'FAILED') {
        setErrorMsg(result.message || 'Medical information extraction could not be completed.')
        setSuccessMsg(null)
      } else if (result.status === 'PARTIAL') {
        setErrorMsg(result.message || 'Medical extraction completed with partial errors.')
        setSuccessMsg(null)
        await loadExtractionData(doc.id)
      } else {
        setSuccessMsg(result.message || 'Medical information extracted successfully.')
        setErrorMsg(null)
        await loadExtractionData(doc.id)
      }
      if (onDocumentUpdated) {
        onDocumentUpdated({
          ...doc,
          status: result.status as any,
          job_status: result.job_status as any,
        })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Medical information extraction failed.'
      setErrorMsg(msg)
      setSuccessMsg(null)
    } finally {
      setIsExtracting(false)
    }
  }

  const handleClose = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
    setIsPreviewing(false)
    setErrorMsg(null)
    setSuccessMsg(null)
    onClose()
  }

  return (
    <div className="doc-detail-backdrop" onClick={handleClose} role="dialog" aria-modal="true">
      <div
        className={`doc-detail-card ${isPreviewing ? 'with-preview' : ''}`}
        onClick={(e) => e.stopPropagation()}
        aria-labelledby="doc-detail-title"
      >
        {/* Modal Header */}
        <div className="doc-detail-header">
          <div className="doc-detail-title-wrap">
            <span className="doc-detail-icon" aria-hidden="true">📄</span>
            <div>
              <div className="doc-header-badges">
                <span className="doc-type-pill">{doc.document_type.replace('_', ' ')}</span>
                <span className={`doc-status-pill ${doc.status.toLowerCase()}`}>
                  {doc.status}
                </span>
                <span className="doc-job-pill">
                  Job: {doc.job_status || 'QUEUED'}
                </span>
              </div>
              <h3 id="doc-detail-title" className="doc-title-text" title={doc.file_name}>
                {doc.file_name}
              </h3>
            </div>
          </div>
          <button
            type="button"
            className="doc-detail-close-btn"
            onClick={handleClose}
            aria-label="Close document details"
          >
            ✕
          </button>
        </div>

        {errorMsg && (
          <div className="doc-detail-alert error" role="alert">
            <span className="alert-icon" aria-hidden="true">⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="doc-detail-alert success" role="alert">
            <span className="alert-icon" aria-hidden="true">✓</span>
            <span>{successMsg}</span>
          </div>
        )}

        <div className="doc-detail-body">
          {/* Metadata Grid */}
          <div className="doc-meta-section">
            <h4 className="meta-section-title">Clinical & File Metadata</h4>
            <div className="meta-grid">
              <div className="meta-item">
                <span className="meta-label">Associated Patient</span>
                <span className="meta-val highlight">
                  {doc.patient_name || 'Patient Dossier'} ({doc.patient_mrn || 'MRN'})
                </span>
              </div>

              <div className="meta-item">
                <span className="meta-label">File Size</span>
                <span className="meta-val">{formatFileSize(doc.file_size)}</span>
              </div>

              <div className="meta-item">
                <span className="meta-label">Page Count</span>
                <span className="meta-val">{doc.page_count} {doc.page_count === 1 ? 'Page' : 'Pages'}</span>
              </div>

              <div className="meta-item">
                <span className="meta-label">MIME Format</span>
                <span className="meta-val mono">{doc.file_type}</span>
              </div>

              <div className="meta-item">
                <span className="meta-label">Uploaded By</span>
                <span className="meta-val">{doc.uploader_name || 'Clinical Staff'}</span>
              </div>

              <div className="meta-item">
                <span className="meta-label">Upload Timestamp</span>
                <span className="meta-val">{formatDate(doc.uploaded_at)}</span>
              </div>

              <div className="meta-item full-col">
                <span className="meta-label">Cryptographic Checksum (SHA-256)</span>
                <span className="meta-val mono checksum">
                  {doc.checksum_sha256 || 'Calculated on transmission'}
                </span>
              </div>
            </div>
          </div>

          {/* AI Medical Extraction Section (Step 9) */}
          <div className="extraction-pipeline-card">
            <div className="pipeline-header">
              <div className="extraction-header-left">
                <span className="pipeline-icon">🧠</span>
                <div>
                  <h5 className="pipeline-title">Clinical Entity Extraction & Intelligence</h5>
                  <span className="pipeline-sub">
                    Grounded Clinical Entity Dossier • Evidence-Linked Extractions
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="extract-action-btn"
                onClick={handleExtract}
                disabled={isExtracting}
                title="Run page-aware medical extraction through Gemini AI Gateway"
              >
                {isExtracting ? (
                  <>
                    <span className="extract-spinner" aria-hidden="true" />
                    Extracting Medical Information...
                  </>
                ) : doc.status === 'PROCESSED' || (extractionSummary && extractionSummary.counts.total > 0) ? (
                  <>🔄 Re-extract Medical Information</>
                ) : doc.status === 'FAILED' ? (
                  <>🔄 Retry Medical Extraction</>
                ) : (
                  <>⚡ Extract Medical Information</>
                )}
              </button>
            </div>

            {loadingExtraction && (
              <div className="extraction-loading-state">
                <span>Loading clinical extraction dossier...</span>
              </div>
            )}

            {extractionSummary && (
              <div className="extraction-content">
                {/* Extraction Counts Overview Banner */}
                <div className="extraction-summary-banner">
                  <span className="summary-status-badge">✓ Medical Information Extracted</span>
                  <span className="summary-counts-text">
                    Total: <strong>{extractionSummary.counts.total}</strong> • Events: <strong>{extractionSummary.counts.events}</strong> • Conditions: <strong>{extractionSummary.counts.conditions}</strong> • Medications: <strong>{extractionSummary.counts.medications}</strong> • Investigations: <strong>{extractionSummary.counts.investigations}</strong> • Procedures: <strong>{extractionSummary.counts.procedures}</strong> • Follow-ups: <strong>{extractionSummary.counts.follow_ups}</strong>
                  </span>
                </div>

                {/* Metric Summary Chips */}
                <div className="extraction-metrics-row">
                  <div
                    className={`metric-chip ${activeExtractionTab === 'conditions' ? 'active' : ''}`}
                    onClick={() => setActiveExtractionTab('conditions')}
                  >
                    <span className="chip-count">{extractionSummary.counts.conditions}</span>
                    <span className="chip-name">Conditions</span>
                  </div>
                  <div
                    className={`metric-chip ${activeExtractionTab === 'medications' ? 'active' : ''}`}
                    onClick={() => setActiveExtractionTab('medications')}
                  >
                    <span className="chip-count">{extractionSummary.counts.medications}</span>
                    <span className="chip-name">Medications</span>
                  </div>
                  <div
                    className={`metric-chip ${activeExtractionTab === 'investigations' ? 'active' : ''}`}
                    onClick={() => setActiveExtractionTab('investigations')}
                  >
                    <span className="chip-count">{extractionSummary.counts.investigations}</span>
                    <span className="chip-name">Investigations</span>
                  </div>
                  <div
                    className={`metric-chip ${activeExtractionTab === 'procedures' ? 'active' : ''}`}
                    onClick={() => setActiveExtractionTab('procedures')}
                  >
                    <span className="chip-count">{extractionSummary.counts.procedures}</span>
                    <span className="chip-name">Procedures</span>
                  </div>
                  <div
                    className={`metric-chip ${activeExtractionTab === 'events' ? 'active' : ''}`}
                    onClick={() => setActiveExtractionTab('events')}
                  >
                    <span className="chip-count">{extractionSummary.counts.events}</span>
                    <span className="chip-name">Events</span>
                  </div>
                  <div
                    className={`metric-chip ${activeExtractionTab === 'follow_ups' ? 'active' : ''}`}
                    onClick={() => setActiveExtractionTab('follow_ups')}
                  >
                    <span className="chip-count">{extractionSummary.counts.follow_ups}</span>
                    <span className="chip-name">Follow-ups</span>
                  </div>
                </div>

                {/* Tabbed Entity List */}
                <div className="extraction-items-container">
                  {/* Conditions Tab */}
                  {activeExtractionTab === 'conditions' && (
                    <div className="extraction-items-list">
                      {extractionSummary.conditions.length === 0 ? (
                        <p className="no-items-text">No conditions or diagnoses extracted from this document.</p>
                      ) : (
                        extractionSummary.conditions.map((c: ExtractedEventItem) => (
                          <div key={c.id} className="extracted-item-card condition">
                            <div className="item-card-header">
                              <span className="item-title">{c.title}</span>
                              {c.is_conflict && <span className="uncertain-tag">⚠️ Uncertain</span>}
                            </div>
                            <p className="item-desc">{c.description}</p>
                            {c.evidence_snippet && (
                              <div className="item-evidence">
                                <span className="evidence-label">Source Evidence:</span>
                                <span className="evidence-quote">“{c.evidence_snippet}”</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* Medications Tab */}
                  {activeExtractionTab === 'medications' && (
                    <div className="extraction-items-list">
                      {extractionSummary.medications.length === 0 ? (
                        <p className="no-items-text">No medications extracted from this document.</p>
                      ) : (
                        extractionSummary.medications.map((m: ExtractedMedicationItem) => (
                          <div key={m.id} className="extracted-item-card medication">
                            <div className="item-card-header">
                              <span className="item-title">{m.medication_name}</span>
                              <span className={`med-status-tag ${m.status.toLowerCase()}`}>{m.status}</span>
                            </div>
                            <div className="item-details-row">
                              {m.dosage && <span>Dose: <strong>{m.dosage} {m.dose_unit || ''}</strong></span>}
                              {m.frequency && <span>Freq: <strong>{m.frequency}</strong></span>}
                              {m.route && <span>Route: <strong>{m.route}</strong></span>}
                            </div>
                            {m.evidence_snippet && (
                              <div className="item-evidence">
                                <span className="evidence-label">Source Evidence:</span>
                                <span className="evidence-quote">“{m.evidence_snippet}”</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* Investigations Tab */}
                  {activeExtractionTab === 'investigations' && (
                    <div className="extraction-items-list">
                      {extractionSummary.investigations.length === 0 ? (
                        <p className="no-items-text">No diagnostic investigations extracted from this document.</p>
                      ) : (
                        extractionSummary.investigations.map((i: ExtractedInvestigationItem) => (
                          <div key={i.id} className="extracted-item-card investigation">
                            <div className="item-card-header">
                              <span className="item-title">{i.investigation_name}</span>
                              <div className="inv-badge-group">
                                <span className="inv-type-tag">{i.investigation_type}</span>
                                {i.is_abnormal && <span className="abnormal-tag">ABNORMAL</span>}
                              </div>
                            </div>
                            {i.result_summary && (
                              <p className="item-result">
                                <strong>Result:</strong> {i.result_summary}
                                {i.reference_range && <span className="ref-range"> (Ref: {i.reference_range})</span>}
                              </p>
                            )}
                            {i.evidence_snippet && (
                              <div className="item-evidence">
                                <span className="evidence-label">Source Evidence:</span>
                                <span className="evidence-quote">“{i.evidence_snippet}”</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* Procedures Tab */}
                  {activeExtractionTab === 'procedures' && (
                    <div className="extraction-items-list">
                      {extractionSummary.procedures.length === 0 ? (
                        <p className="no-items-text">No procedures extracted from this document.</p>
                      ) : (
                        extractionSummary.procedures.map((p: ExtractedEventItem) => (
                          <div key={p.id} className="extracted-item-card procedure">
                            <div className="item-card-header">
                              <span className="item-title">{p.title}</span>
                              <span className="date-tag">{p.event_date ? formatDate(p.event_date) : p.event_date_precision}</span>
                            </div>
                            <p className="item-desc">{p.description}</p>
                            {p.evidence_snippet && (
                              <div className="item-evidence">
                                <span className="evidence-label">Source Evidence:</span>
                                <span className="evidence-quote">“{p.evidence_snippet}”</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* Clinical Events Tab */}
                  {activeExtractionTab === 'events' && (
                    <div className="extraction-items-list">
                      {extractionSummary.events.length === 0 ? (
                        <p className="no-items-text">No clinical events extracted from this document.</p>
                      ) : (
                        extractionSummary.events.map((e: ExtractedEventItem) => (
                          <div key={e.id} className="extracted-item-card event">
                            <div className="item-card-header">
                              <span className="item-title">{e.title}</span>
                              <span className="event-type-badge">{e.event_type}</span>
                            </div>
                            <p className="item-desc">{e.description}</p>
                            {e.evidence_snippet && (
                              <div className="item-evidence">
                                <span className="evidence-label">Source Evidence:</span>
                                <span className="evidence-quote">“{e.evidence_snippet}”</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* Follow-ups Tab */}
                  {activeExtractionTab === 'follow_ups' && (
                    <div className="extraction-items-list">
                      {extractionSummary.follow_ups.length === 0 ? (
                        <p className="no-items-text">No follow-up items or pending orders extracted from this document.</p>
                      ) : (
                        extractionSummary.follow_ups.map((f: ExtractedFollowUpItem) => (
                          <div key={f.id} className="extracted-item-card follow-up">
                            <div className="item-card-header">
                              <span className="item-title">{f.title}</span>
                              <span className={`priority-tag ${f.priority.toLowerCase()}`}>{f.priority}</span>
                            </div>
                            {f.description && <p className="item-desc">{f.description}</p>}
                            {f.due_date && <span className="due-date-tag">Due: {f.due_date}</span>}
                            {f.evidence_snippet && (
                              <div className="item-evidence">
                                <span className="evidence-label">Source Evidence:</span>
                                <span className="evidence-quote">“{f.evidence_snippet}”</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Interactive PDF Preview Pane */}
          {isPreviewing && previewUrl && (
            <div className="pdf-preview-container" aria-label="PDF Document Preview">
              <div className="preview-pane-header">
                <span className="preview-label">Authenticated Preview Frame</span>
                <span className="preview-security-tag">🔒 Private Session Stream</span>
              </div>
              <iframe
                src={previewUrl}
                className="pdf-preview-iframe"
                title={`Preview of ${doc.file_name}`}
              />
            </div>
          )}
        </div>

        {/* Modal Actions */}
        <div className="doc-detail-footer">
          {doc.status === 'FAILED' && (
            <button
              type="button"
              className="doc-footer-btn retry"
              onClick={handleRetry}
              disabled={isRetrying}
            >
              {isRetrying ? 'Re-queuing...' : '🔄 Retry Ingestion'}
            </button>
          )}

          <button
            type="button"
            className="doc-footer-btn secondary"
            onClick={handleDownloadPdf}
            disabled={loadingFile}
          >
            {loadingFile ? 'Downloading...' : '⬇ Download PDF'}
          </button>

          <button
            type="button"
            className="doc-footer-btn primary"
            onClick={handlePreviewPdf}
            disabled={loadingFile}
          >
            {loadingFile
              ? 'Loading...'
              : isPreviewing
              ? 'Hide Preview'
              : '👁 Preview Document'}
          </button>
        </div>
      </div>
    </div>
  )
}
