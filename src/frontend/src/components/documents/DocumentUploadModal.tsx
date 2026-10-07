/**
 * MedBrief AI — Medical Record Upload Dialog
 * Step 7: PDF / Medical Document Upload & Ingestion Foundation
 *
 * Polished clinical upload experience featuring:
 * - Drag-and-drop upload zone with keyboard accessibility
 * - Patient selector (pre-locked if triggered from Patient Dossier)
 * - Clinical document category classification
 * - Client-side validation (PDF format, size limits, empty check)
 * - Genuine transmission progress tracking (XHR upload events)
 * - Clear clinical status indicators ('Upload Complete — Processing Queued')
 * - Human-readable error alerts (duplicate files, oversized records)
 */

import React, { useState, useEffect, useRef } from 'react'
import type { PatientRecord } from '../../types/patient'
import type { DocumentRecord, ClinicalDocumentType } from '../../types/document'
import { uploadDocument } from '../../services/documentApi'
import { fetchPatients } from '../../services/patientApi'
import './DocumentUploadModal.css'

interface DocumentUploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (document: DocumentRecord) => void
  targetPatient?: PatientRecord | null
}

const MAX_SIZE_MB = 25
const MAX_BYTES = MAX_SIZE_MB * 1024 * 1024

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  targetPatient,
}) => {
  const [patients, setPatients] = useState<PatientRecord[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState<string>('')
  const [documentType, setDocumentType] = useState<ClinicalDocumentType>('DISCHARGE_SUMMARY')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStatusMsg, setUploadStatusMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Load patients if no pre-selected patient
  useEffect(() => {
    if (isOpen) {
      if (targetPatient) {
        setSelectedPatientId(targetPatient.id)
      } else {
        fetchPatients({ page: 1, pageSize: 50 })
          .then((res) => {
            setPatients(res.items)
            if (res.items.length > 0) {
              setSelectedPatientId(res.items[0].id)
            }
          })
          .catch(() => setPatients([]))
      }
      setSelectedFile(null)
      setUploadProgress(0)
      setIsUploading(false)
      setErrorMsg(null)
      setIsSuccess(false)
      setUploadStatusMsg('')
    }
  }, [isOpen, targetPatient])

  if (!isOpen) return null

  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      return 'Only PDF medical records (.pdf) are supported in this release.'
    }
    if (file.size === 0) {
      return 'The selected file is empty (0 bytes).'
    }
    if (file.size > MAX_BYTES) {
      return `This file is larger than the allowed limit (${MAX_SIZE_MB} MB). Selected: ${formatFileSize(file.size)}.`
    }
    return null
  }

  const handleFileSelection = (file: File) => {
    setErrorMsg(null)
    const validationError = validateFile(file)
    if (validationError) {
      setErrorMsg(validationError)
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setErrorMsg('Please select a PDF medical record to upload.')
      return
    }
    if (!selectedPatientId) {
      setErrorMsg('Every uploaded medical document must be associated with an active patient.')
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setUploadStatusMsg('Initiating secure file transfer...')
    setErrorMsg(null)

    try {
      const doc = await uploadDocument(
        selectedPatientId,
        selectedFile,
        documentType,
        (percent) => {
          setUploadProgress(percent)
          if (percent < 100) {
            setUploadStatusMsg(`Uploading... ${percent}%`)
          } else {
            setUploadStatusMsg('Upload complete — Queuing ingestion job...')
          }
        }
      )

      setIsSuccess(true)
      setUploadStatusMsg('Document ingested successfully — Queued for clinical processing.')
      setTimeout(() => {
        onSuccess(doc)
        onClose()
      }, 1200)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'An error occurred during document upload.'
      setErrorMsg(msg)
      setIsUploading(false)
      setUploadProgress(0)
      setUploadStatusMsg('')
    }
  }

  const resolvedPatientName = targetPatient
    ? `${targetPatient.first_name} ${targetPatient.last_name} (${targetPatient.mrn})`
    : patients.find((p) => p.id === selectedPatientId)
    ? `${patients.find((p) => p.id === selectedPatientId)?.first_name} ${
        patients.find((p) => p.id === selectedPatientId)?.last_name
      } (${patients.find((p) => p.id === selectedPatientId)?.mrn})`
    : 'Select a patient'

  return (
    <div className="doc-upload-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="doc-upload-card"
        onClick={(e) => e.stopPropagation()}
        aria-labelledby="doc-upload-title"
      >
        <div className="doc-upload-header">
          <div className="doc-upload-title-wrap">
            <span className="doc-upload-icon" aria-hidden="true">📤</span>
            <div>
              <h3 id="doc-upload-title">Upload Medical Record</h3>
              <p className="doc-upload-sub">
                Add an official PDF medical record to this patient's clinical dossier.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="doc-upload-close-btn"
            onClick={onClose}
            aria-label="Close upload dialog"
            disabled={isUploading}
          >
            ✕
          </button>
        </div>

        <div className="doc-upload-body">
          {errorMsg && (
            <div className="doc-upload-alert error" role="alert">
              <span className="alert-icon" aria-hidden="true">⚠️</span>
              <div className="alert-text">{errorMsg}</div>
            </div>
          )}

          {isSuccess && (
            <div className="doc-upload-alert success" role="status">
              <span className="alert-icon" aria-hidden="true">✓</span>
              <div className="alert-text">{uploadStatusMsg}</div>
            </div>
          )}

          {/* Patient Association */}
          <div className="upload-field-row">
            <label htmlFor="upload-patient-select" className="upload-label">
              Patient Association *
            </label>
            {targetPatient ? (
              <div className="locked-patient-pill">
                <span className="patient-avatar-mini">👤</span>
                <span className="patient-locked-text">{resolvedPatientName}</span>
                <span className="patient-locked-badge">Active Dossier</span>
              </div>
            ) : (
              <select
                id="upload-patient-select"
                className="upload-select"
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                disabled={isUploading || isSuccess}
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name} — {p.mrn}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Document Type Selector */}
          <div className="upload-field-row">
            <label htmlFor="upload-doc-type" className="upload-label">
              Document Classification
            </label>
            <select
              id="upload-doc-type"
              className="upload-select"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value as ClinicalDocumentType)}
              disabled={isUploading || isSuccess}
            >
              <option value="DISCHARGE_SUMMARY">Discharge Summary</option>
              <option value="CLINIC_CONSULTATION">Clinic Consultation Note</option>
              <option value="LAB_PATHOLOGY">Laboratory & Pathology Report</option>
              <option value="RADIOLOGY_REPORT">Radiology & Imaging Report</option>
              <option value="PRESCRIPTION">Prescription & Medication Order</option>
              <option value="REFERRAL_LETTER">Specialist Referral Letter</option>
              <option value="OTHER">Other Clinical Record</option>
            </select>
          </div>

          {/* Drag & Drop Zone */}
          {!selectedFile ? (
            <div
              className={`doc-dropzone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
              }}
              tabIndex={0}
              role="button"
              aria-label="Drag and drop PDF medical record here or click to browse"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="file-hidden-input"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileSelection(e.target.files[0])
                  }
                }}
              />
              <span className="dropzone-icon" aria-hidden="true">📄</span>
              <div className="dropzone-text-group">
                <span className="dropzone-title">Drag & drop your medical record here</span>
                <span className="dropzone-sub">or click to browse your computer</span>
              </div>
              <div className="dropzone-footer-tags">
                <span className="tag-spec">PDF files only</span>
                <span className="tag-spec">Max {MAX_SIZE_MB} MB</span>
              </div>
            </div>
          ) : (
            <div className="selected-file-card">
              <div className="file-card-left">
                <span className="file-badge-pdf" aria-hidden="true">PDF</span>
                <div className="file-name-group">
                  <span className="file-display-name" title={selectedFile.name}>
                    {selectedFile.name}
                  </span>
                  <span className="file-display-size">{formatFileSize(selectedFile.size)}</span>
                </div>
              </div>
              {!isUploading && !isSuccess && (
                <button
                  type="button"
                  className="file-remove-btn"
                  onClick={() => setSelectedFile(null)}
                  title="Remove selected file"
                  aria-label="Remove selected file"
                >
                  ✕
                </button>
              )}
            </div>
          )}

          {/* Upload Progress Bar */}
          {isUploading && (
            <div className="upload-progress-container" aria-live="polite">
              <div className="progress-label-row">
                <span className="progress-status-msg">{uploadStatusMsg}</span>
                <span className="progress-percent">{uploadProgress}%</span>
              </div>
              <div className="progress-track" role="progressbar" aria-valuenow={uploadProgress} aria-valuemin={0} aria-valuemax={100}>
                <div
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="doc-upload-footer">
          <button
            type="button"
            className="doc-btn secondary"
            onClick={onClose}
            disabled={isUploading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="doc-btn primary"
            onClick={handleUpload}
            disabled={!selectedFile || isUploading || isSuccess}
          >
            {isUploading ? 'Uploading...' : isSuccess ? 'Ingested' : 'Upload Medical Record'}
          </button>
        </div>
      </div>
    </div>
  )
}
