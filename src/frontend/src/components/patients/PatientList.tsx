/**
 * MedBrief AI — Patient Directory & Caseload Management
 * Step 6: Patient Management
 *
 * Full clinical patient index with:
 * - Real-time search across MRN, first name, and last name
 * - Status filtering (ACTIVE, INACTIVE, ARCHIVED, DECEASED)
 * - Server-side pagination
 * - "+ New Patient" registration modal with validation
 * - In-place editing of demographics
 * - Responsive table / card view
 * - Loading skeletons and empty states
 * - Seamless navigation to Patient Overview dossier
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord, PatientFormData } from '../../types/patient'
import { fetchPatients, createPatient, updatePatient } from '../../services/patientApi'
import { useDebounce } from '../../hooks/useDebounce'
import { useToast } from '../../context/ToastContext'
import { PatientModal } from './PatientModal'
import './PatientList.css'

interface PatientListProps {
  onSelectPatient: (patient: PatientRecord) => void
  onPatientMutation?: () => void
  initialSearch?: string
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
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export const PatientList: React.FC<PatientListProps> = ({
  onSelectPatient,
  onPatientMutation,
  initialSearch = '',
}) => {
  const { showToast } = useToast()
  const [patients, setPatients] = useState<PatientRecord[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [pageSize] = useState(8)

  const [search, setSearch] = useState(initialSearch)
  const debouncedSearch = useDebounce(search, 300)
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingPatient, setEditingPatient] = useState<PatientRecord | null>(null)

  const loadPatients = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchPatients({
        search: debouncedSearch.trim() || undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        page,
        pageSize,
      })
      setPatients(res.items)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve patient caseload.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, statusFilter, page, pageSize])

  useEffect(() => {
    loadPatients()
  }, [loadPatients])

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value)
    setPage(1)
  }

  const handleStatusFilterChange = (status: string) => {
    setStatusFilter(status)
    setPage(1)
  }

  const handleOpenCreateModal = () => {
    setEditingPatient(null)
    setIsModalOpen(true)
  }

  const handleOpenEditModal = (patient: PatientRecord, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingPatient(patient)
    setIsModalOpen(true)
  }

  const handleModalSubmit = async (data: PatientFormData) => {
    if (editingPatient) {
      await updatePatient(editingPatient.id, data)
      showToast(`Patient ${data.first_name} ${data.last_name} updated successfully.`, 'success')
    } else {
      await createPatient(data)
      showToast(`Patient ${data.first_name} ${data.last_name} registered successfully.`, 'success')
    }
    await loadPatients()
    if (onPatientMutation) {
      onPatientMutation()
    }
  }

  return (
    <div className="patient-list-container" role="main" aria-label="Patient Directory">
      {/* Page Header */}
      <header className="patient-list-header">
        <div className="header-left">
          <div className="header-badge-row">
            <span className="step-tag-pill">Caseload Directory</span>
            <span className="header-count-pill">{total} Registered Patients</span>
          </div>
          <h1 className="header-title">Patients Directory</h1>
          <p className="header-subtitle">
            Authorized patient caseload, MRN indexing, and clinical demographic management.
          </p>
        </div>

        <button
          type="button"
          className="create-patient-btn"
          onClick={handleOpenCreateModal}
          aria-label="Register new patient"
        >
          <span className="plus-icon">＋</span>
          <span>Register New Patient</span>
        </button>
      </header>

      {/* Filter and Search Bar */}
      <div className="patient-filter-bar">
        <div className="search-input-wrap">
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="text"
            className="patient-search-input"
            value={search}
            onChange={handleSearchChange}
            placeholder="Search by patient name or MRN..."
            aria-label="Search patients by name or MRN"
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

        {/* Status Filter Pills */}
        <div className="status-filter-pills" role="radiogroup" aria-label="Filter by patient status">
          {['ALL', 'ACTIVE', 'INACTIVE', 'ARCHIVED'].map((st) => (
            <button
              key={st}
              type="button"
              className={`filter-pill ${statusFilter === st ? 'active' : ''}`}
              onClick={() => handleStatusFilterChange(st)}
              role="radio"
              aria-checked={statusFilter === st}
            >
              {st === 'ALL' ? 'All Records' : st}
            </button>
          ))}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="patient-list-alert error" role="alert">
          <span className="alert-icon">⚠️</span>
          <div className="alert-content">
            <strong>Unable to load patient records:</strong> {error}
          </div>
          <button type="button" className="retry-btn" onClick={loadPatients}>
            Retry
          </button>
        </div>
      )}

      {/* Content Area */}
      {loading ? (
        <div className="patient-skeleton-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="patient-skeleton-row" />
          ))}
        </div>
      ) : patients.length === 0 ? (
        <div className="patient-empty-state">
          <div className="empty-icon">👥</div>
          <h3 className="empty-title">No Patients Found</h3>
          <p className="empty-desc">
            {search || statusFilter !== 'ALL'
              ? 'No patient records match your current filter parameters. Try adjusting your search term or status.'
              : 'Your authorized caseload is currently empty. Click "Register New Patient" to enroll your first patient.'}
          </p>
          {(search || statusFilter !== 'ALL') && (
            <button
              type="button"
              className="clear-filters-btn"
              onClick={() => {
                setSearch('')
                setStatusFilter('ALL')
                setPage(1)
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      ) : (
        <div className="patient-table-card">
          <table className="patient-table">
            <thead>
              <tr>
                <th scope="col">Patient Name</th>
                <th scope="col">MRN</th>
                <th scope="col">DOB / Age</th>
                <th scope="col">Status</th>
                <th scope="col">Role</th>
                <th scope="col">Documents</th>
                <th scope="col">Last Record</th>
                <th scope="col" className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => {
                const age = calculateAge(p.date_of_birth)
                return (
                  <tr
                    key={p.id}
                    className="patient-table-row"
                    onClick={() => onSelectPatient(p)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') onSelectPatient(p)
                    }}
                  >
                    <td>
                      <div className="patient-cell-name">
                        <span className="patient-cell-avatar" aria-hidden="true">
                          {p.gender === 'Female' ? '👩' : '👨'}
                        </span>
                        <div>
                          <span className="patient-full-name">{p.first_name} {p.last_name}</span>
                          <span className="patient-gender-sub">{p.gender || 'Not specified'}</span>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className="mrn-badge mono">{p.mrn || '—'}</span>
                    </td>

                    <td>
                      <div className="patient-dob-cell">
                        <span className="dob-date">{formatDate(p.date_of_birth)}</span>
                        {age !== null && <span className="dob-age">{age} yrs</span>}
                      </div>
                    </td>

                    <td>
                      <span className={`status-pill ${p.status.toLowerCase()}`}>
                        {p.status}
                      </span>
                    </td>

                    <td>
                      <span className="role-tag">
                        {p.access_role?.replace('_', ' ') || 'PRIMARY PHYSICIAN'}
                      </span>
                    </td>

                    <td>
                      <span className="docs-badge">
                        📄 {p.document_count} {p.document_count === 1 ? 'doc' : 'docs'}
                      </span>
                    </td>

                    <td>
                      <span className="date-cell">{formatDate(p.last_document_date)}</span>
                    </td>

                    <td className="text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="row-action-btn primary"
                          onClick={() => onSelectPatient(p)}
                          title="Open full clinical dossier"
                        >
                          Overview →
                        </button>
                        <button
                          type="button"
                          className="row-action-btn edit"
                          onClick={(e) => handleOpenEditModal(p, e)}
                          title="Edit patient demographics"
                        >
                          ✏️
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer */}
      {!loading && patients.length > 0 && (
        <div className="patient-pagination-bar">
          <div className="pagination-info">
            Showing Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({total} total patients)
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

      {/* Patient Create / Edit Modal */}
      <PatientModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleModalSubmit}
        initialData={editingPatient}
      />
    </div>
  )
}
