/**
 * MedBrief AI — Medical Documents Directory & Ingestion Workspace
 * Step 7: PDF / Medical Document Upload & Ingestion Foundation
 *
 * Dedicated workspace for:
 * - Exploring all ingested medical records across authorized patient caseloads
 * - Multi-criteria search across filenames, patient names, and MRNs
 * - Filtering by document classification and ingestion status
 * - One-click upload modal trigger with drag-and-drop
 * - Inspection of document metadata, file statistics, and SHA-256 checksums
 * - Authenticated PDF preview and secure download
 * - Re-queuing failed ingestion jobs
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { DocumentRecord } from '../../types/document'
import type { PatientRecord } from '../../types/patient'
import { fetchAllDocuments } from '../../services/documentApi'
import { DocumentUploadModal } from './DocumentUploadModal'
import { DocumentDetailModal } from './DocumentDetailModal'
import { useDebounce } from '../../hooks/useDebounce'
import { useToast } from '../../context/ToastContext'
import './DocumentsView.css'

interface DocumentsViewProps {
  initialPatientId?: string
  targetPatient?: PatientRecord | null
  patients?: PatientRecord[]
  onPatientChange?: (patient: PatientRecord) => void
  onClearPatientFilter?: () => void
  onSelectPatient?: (patientId: string) => void
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
  })
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  initialPatientId,
  targetPatient,
  patients = [],
  onPatientChange,
  onClearPatientFilter,
}) => {
  const { showToast } = useToast()
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [pageSize] = useState(10)

  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 300)
  const [docTypeFilter, setDocTypeFilter] = useState<string>('ALL')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modals state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedDocForDetail, setSelectedDocForDetail] = useState<DocumentRecord | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchAllDocuments({
        patient_id: initialPatientId || targetPatient?.id || undefined,
        document_type: docTypeFilter !== 'ALL' ? docTypeFilter : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        search: debouncedSearch.trim() || undefined,
        page,
        page_size: pageSize,
      })
      setDocuments(res.items)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve documents.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [initialPatientId, targetPatient, docTypeFilter, statusFilter, debouncedSearch, page, pageSize])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  // Smart polling for documents in PROCESSING or UPLOADED status
  useEffect(() => {
    const hasActiveJobs = documents.some(
      (d) =>
        d.status === 'PROCESSING' ||
        d.status === 'UPLOADED' ||
        d.job_status === 'PROCESSING' ||
        d.job_status === 'QUEUED'
    )
    if (!hasActiveJobs) return

    const pollTimer = setInterval(() => {
      fetchAllDocuments({
        patient_id: initialPatientId || targetPatient?.id || undefined,
        document_type: docTypeFilter !== 'ALL' ? docTypeFilter : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        search: debouncedSearch.trim() || undefined,
        page,
        page_size: pageSize,
      })
        .then((res) => {
          setDocuments(res.items)
          setTotal(res.total)
          setTotalPages(res.total_pages)
        })
        .catch(() => {})
    }, 3500)

    return () => clearInterval(pollTimer)
  }, [documents, initialPatientId, targetPatient, docTypeFilter, statusFilter, debouncedSearch, page, pageSize])

  const handleUploadSuccess = () => {
    loadDocuments()
    showToast('Medical record uploaded successfully. Processing queued.', 'success')
  }

  const handleDocumentUpdated = (updated: DocumentRecord) => {
    setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
    if (selectedDocForDetail?.id === updated.id) {
      setSelectedDocForDetail(updated)
    }
  }

  return (
    <div className="docs-view-container" role="main" aria-label="Medical Documents Directory">
      {/* Header Strip */}
      <header className="docs-view-header">
        <div className="docs-header-left">
          <div className="docs-badge-row">
            <span className="step-tag-pill">EHR Record Store</span>
            <span className="docs-count-pill">{total} Ingested Records</span>
          </div>
          <h1 className="docs-header-title">
            {targetPatient
              ? `Medical Records: ${targetPatient.first_name} ${targetPatient.last_name}`
              : 'Medical Documents Directory'}
          </h1>
          <p className="docs-header-subtitle">
            PDF document ingestion, page counting, and clinical record management.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {patients.length > 1 && onPatientChange && (
            <select
              className="docs-type-select"
              style={{ maxWidth: '240px', padding: '0.55rem 0.85rem' }}
              value={targetPatient?.id || ''}
              onChange={(e) => {
                const found = patients.find((p) => p.id === e.target.value)
                if (found) onPatientChange(found)
              }}
              aria-label="Switch patient"
            >
              <option value="" disabled>Switch Patient...</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name} ({p.mrn})
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            className="upload-trigger-btn"
            onClick={() => setIsUploadModalOpen(true)}
            aria-label="Upload medical record"
          >
            <span className="plus-icon">＋</span>
            <span>Upload Medical Record</span>
          </button>
        </div>
      </header>

      {/* Patient Scope Filter Banner */}
      {targetPatient && onClearPatientFilter && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#f0f9ff',
          border: '1px solid #bae6fd',
          borderRadius: '8px',
          padding: '0.6rem 1rem',
          marginBottom: '1rem',
          fontSize: '0.85rem',
          color: '#0369a1'
        }}>
          <span>
            Filtering records for patient: <strong>{targetPatient.first_name} {targetPatient.last_name}</strong> (MRN: {targetPatient.mrn})
          </span>
          <button
            type="button"
            onClick={onClearPatientFilter}
            style={{
              background: '#ffffff',
              border: '1px solid #93c5fd',
              color: '#0284c7',
              borderRadius: '6px',
              padding: '0.25rem 0.65rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Show All Patients ✕
          </button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="docs-filter-bar">
        <div className="search-wrap">
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="text"
            className="docs-search-input"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search by filename or patient MRN..."
            aria-label="Search documents by filename or patient MRN"
          />
          {search && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => {
                setSearch('')
                setPage(1)
              }}
              aria-label="Clear search query"
            >
              ✕
            </button>
          )}
        </div>

        {/* Document Type Dropdown */}
        <select
          className="docs-type-select"
          value={docTypeFilter}
          onChange={(e) => {
            setDocTypeFilter(e.target.value)
            setPage(1)
          }}
          aria-label="Filter by document type"
        >
          <option value="ALL">All Document Types</option>
          <option value="DISCHARGE_SUMMARY">Discharge Summaries</option>
          <option value="CLINIC_CONSULTATION">Clinic Consultations</option>
          <option value="LAB_PATHOLOGY">Lab & Pathology</option>
          <option value="RADIOLOGY_REPORT">Radiology & Imaging</option>
          <option value="PRESCRIPTION">Prescriptions</option>
          <option value="REFERRAL_LETTER">Referral Letters</option>
          <option value="OTHER">Other Clinical Records</option>
        </select>

        {/* Status Filter Pills */}
        <div className="docs-status-pills" role="radiogroup" aria-label="Filter by ingestion status">
          {['ALL', 'UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED'].map((st) => (
            <button
              key={st}
              type="button"
              className={`filter-pill ${statusFilter === st ? 'active' : ''}`}
              onClick={() => {
                setStatusFilter(st)
                setPage(1)
              }}
              role="radio"
              aria-checked={statusFilter === st}
            >
              {st === 'ALL' ? 'All Statuses' : st}
            </button>
          ))}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="docs-alert error" role="alert">
          <span className="alert-icon" aria-hidden="true">⚠️</span>
          <span>{error}</span>
          <button type="button" className="retry-btn" onClick={loadDocuments}>
            Retry
          </button>
        </div>
      )}

      {/* Content Area */}
      {loading ? (
        <div className="docs-skeleton-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="docs-skeleton-row" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="docs-empty-state">
          <div className="empty-icon" aria-hidden="true">📄</div>
          <h3 className="empty-title">No Medical Records Uploaded Yet</h3>
          <p className="empty-desc">
            {search || docTypeFilter !== 'ALL' || statusFilter !== 'ALL'
              ? 'No medical records match your current filter parameters.'
              : 'Upload a PDF medical record to begin building this patient dossier.'}
          </p>
          <button
            type="button"
            className="empty-action-btn"
            onClick={() => setIsUploadModalOpen(true)}
          >
            ＋ Upload Medical Record
          </button>
        </div>
      ) : (
        <div className="docs-table-card">
          <table className="docs-table">
            <thead>
              <tr>
                <th scope="col">Document Record</th>
                <th scope="col">Patient</th>
                <th scope="col">Type</th>
                <th scope="col">Pages / Size</th>
                <th scope="col">Ingestion Status</th>
                <th scope="col">Uploaded</th>
                <th scope="col" className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                <tr
                  key={d.id}
                  className="docs-table-row"
                  onClick={() => setSelectedDocForDetail(d)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') setSelectedDocForDetail(d)
                  }}
                >
                  <td>
                    <div className="doc-cell-title">
                      <span className="doc-pdf-badge" aria-hidden="true">PDF</span>
                      <div>
                        <span className="doc-name-text" title={d.file_name}>{d.file_name}</span>
                        <span className="doc-uploader-sub">By {d.uploader_name || 'Staff'}</span>
                      </div>
                    </div>
                  </td>

                  <td>
                    <div className="patient-link-cell">
                      <span className="patient-name-link">{d.patient_name || 'Patient'}</span>
                      <span className="patient-mrn-sub mono">{d.patient_mrn || '—'}</span>
                    </div>
                  </td>

                  <td>
                    <span className="doc-type-tag">
                      {d.document_type.replace('_', ' ')}
                    </span>
                  </td>

                  <td>
                    <div className="pages-size-cell">
                      <span className="pages-count">{d.page_count} {d.page_count === 1 ? 'page' : 'pages'}</span>
                      <span className="size-sub">{formatFileSize(d.file_size)}</span>
                    </div>
                  </td>

                  <td>
                    <div className="status-cell">
                      <span className={`status-pill ${d.status.toLowerCase()}`}>
                        {d.status === 'UPLOADED' ? 'Uploaded' : d.status}
                      </span>
                      <span className="job-status-sub">
                        Job: {d.job_status || 'QUEUED'}
                      </span>
                    </div>
                  </td>

                  <td>
                    <span className="date-cell">{formatDate(d.uploaded_at)}</span>
                  </td>

                  <td className="text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="row-action-btn primary"
                        onClick={() => setSelectedDocForDetail(d)}
                        title="View document metadata and preview"
                      >
                        Details →
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer */}
      {!loading && documents.length > 0 && (
        <div className="docs-pagination-bar">
          <div className="pagination-info">
            Showing Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({total} total records)
          </div>

          <div className="pagination-controls">
            <button
              type="button"
              className="page-nav-btn"
              disabled={page <= 1}
              onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
              aria-label="Previous page"
            >
              ← Previous
            </button>
            <span className="current-page-num">{page}</span>
            <button
              type="button"
              className="page-nav-btn"
              disabled={page >= totalPages}
              onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))}
              aria-label="Next page"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={handleUploadSuccess}
        targetPatient={targetPatient}
      />

      {/* Detail & Preview Modal */}
      <DocumentDetailModal
        isOpen={Boolean(selectedDocForDetail)}
        onClose={() => setSelectedDocForDetail(null)}
        document={selectedDocForDetail}
        onDocumentUpdated={handleDocumentUpdated}
      />
    </div>
  )
}
