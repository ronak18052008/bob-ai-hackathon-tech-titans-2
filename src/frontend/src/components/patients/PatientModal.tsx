/**
 * MedBrief AI — Patient Create & Edit Modal
 * Step 6: Patient Management
 *
 * Provides validated form dialog for registering new patients or updating
 * demographics, contact details, and clinical status.
 */

import React, { useState, useEffect } from 'react'
import type { PatientRecord, PatientFormData, PatientStatus } from '../../types/patient'
import './PatientModal.css'

interface PatientModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: PatientFormData) => Promise<void>
  initialData?: PatientRecord | null
  title?: string
}

export const PatientModal: React.FC<PatientModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  title,
}) => {
  const isEdit = Boolean(initialData)

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [mrn, setMrn] = useState('')
  const [dob, setDob] = useState('')
  const [gender, setGender] = useState('Male')
  const [phone, setPhone] = useState('')
  const [status, setStatus] = useState<PatientStatus>('ACTIVE')

  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (initialData) {
      setFirstName(initialData.first_name || '')
      setLastName(initialData.last_name || '')
      setMrn(initialData.mrn || '')
      setDob(initialData.date_of_birth ? initialData.date_of_birth.split('T')[0] : '')
      setGender(initialData.gender || 'Male')
      setPhone(initialData.contact_phone || '')
      setStatus(initialData.status || 'ACTIVE')
    } else {
      setFirstName('')
      setLastName('')
      setMrn('')
      setDob('')
      setGender('Male')
      setPhone('')
      setStatus('ACTIVE')
    }
    setFormError(null)
  }, [initialData, isOpen])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!firstName.trim() || !lastName.trim()) {
      setFormError('First and last name are required clinical identifiers.')
      return
    }

    if (dob) {
      const parsedDate = new Date(dob)
      if (isNaN(parsedDate.getTime()) || parsedDate > new Date()) {
        setFormError('Date of birth cannot be a future date.')
        return
      }
    }

    setSubmitting(true)
    try {
      const payload: PatientFormData = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        mrn: mrn.trim() ? mrn.trim() : undefined,
        date_of_birth: dob ? dob : undefined,
        gender: gender || undefined,
        contact_phone: phone.trim() ? phone.trim() : undefined,
        status,
      }
      await onSubmit(payload)
      onClose()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred.'
      setFormError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="patient-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="patient-modal-card"
        onClick={(e) => e.stopPropagation()}
        aria-labelledby="patient-modal-title"
      >
        <div className="patient-modal-header">
          <div className="patient-modal-title-wrap">
            <span className="patient-modal-icon">{isEdit ? '✏️' : '👤'}</span>
            <div>
              <h3 id="patient-modal-title">{title || (isEdit ? 'Edit Patient Record' : 'Register New Patient')}</h3>
              <p className="patient-modal-sub">
                {isEdit
                  ? `Update clinical record for ${initialData?.first_name} ${initialData?.last_name}`
                  : 'Enroll a patient into your clinical caseload with secure access controls'}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="patient-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {formError && (
          <div className="patient-modal-alert error" role="alert">
            <span className="alert-icon">⚠️</span>
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="patient-modal-form">
          <div className="form-row-duo">
            <div className="form-field">
              <label htmlFor="p-first-name">First Name *</label>
              <input
                id="p-first-name"
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="e.g. Johnathan"
                className="patient-input"
              />
            </div>

            <div className="form-field">
              <label htmlFor="p-last-name">Last Name *</label>
              <input
                id="p-last-name"
                type="text"
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="e.g. Doe"
                className="patient-input"
              />
            </div>
          </div>

          <div className="form-row-duo">
            <div className="form-field">
              <label htmlFor="p-mrn">
                Medical Record Number (MRN)
                <span className="label-hint"> {isEdit ? '' : '(Auto-generated if left blank)'}</span>
              </label>
              <input
                id="p-mrn"
                type="text"
                value={mrn}
                onChange={(e) => setMrn(e.target.value)}
                placeholder="e.g. MRN-2026-0042"
                className="patient-input mono"
              />
            </div>

            <div className="form-field">
              <label htmlFor="p-dob">Date of Birth</label>
              <input
                id="p-dob"
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                className="patient-input"
              />
            </div>
          </div>

          <div className="form-row-duo">
            <div className="form-field">
              <label htmlFor="p-gender">Gender</label>
              <select
                id="p-gender"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="patient-input"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Non-binary">Non-binary</option>
                <option value="Other">Other</option>
                <option value="Unknown">Unknown</option>
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="p-phone">Contact Phone</label>
              <input
                id="p-phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="e.g. +1-555-0199"
                className="patient-input"
              />
            </div>
          </div>

          <div className="form-field">
            <label htmlFor="p-status">Clinical Status</label>
            <select
              id="p-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as PatientStatus)}
              className="patient-input"
            >
              <option value="ACTIVE">ACTIVE — Under active clinical management</option>
              <option value="INACTIVE">INACTIVE — Discharged / routine monitoring paused</option>
              <option value="ARCHIVED">ARCHIVED — Historical record preserved</option>
              <option value="DECEASED">DECEASED — Closed clinical dossier</option>
            </select>
          </div>

          <div className="patient-modal-actions">
            <button
              type="button"
              className="patient-btn secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="patient-btn primary"
              disabled={submitting}
            >
              {submitting ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Patient Record'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
