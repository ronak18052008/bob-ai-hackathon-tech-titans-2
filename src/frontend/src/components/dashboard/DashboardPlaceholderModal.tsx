/**
 * MedBrief AI — Dashboard Placeholder Modal
 * Step 5: Doctor Dashboard UI
 *
 * Informs the clinician about planned roadmap features (Steps 6–15)
 * when clicking dashboard entry points without executing premature logic.
 */

import React, { useEffect } from 'react'
import './DashboardPlaceholderModal.css'

interface DashboardPlaceholderModalProps {
  isOpen: boolean
  title: string
  description: string
  stepInfo: string
  icon?: string
  onClose: () => void
}

export const DashboardPlaceholderModal: React.FC<DashboardPlaceholderModalProps> = ({
  isOpen,
  title,
  description,
  stepInfo,
  icon = '📌',
  onClose,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header-row">
          <div className="modal-icon-badge" aria-hidden="true">
            {icon}
          </div>
          <div className="modal-title-col">
            <h3 id="modal-title">{title}</h3>
            <span className="modal-step-tag">{stepInfo}</span>
          </div>
        </div>

        <p className="modal-body">{description}</p>

        <div className="modal-boundary-note">
          <strong>Clinical Decision Support:</strong> Access full patient dossiers, EHR documents, diagnostic timelines, pharmacotherapy intelligence, and clinical composers directly via the primary clinical navigation.
        </div>

        <div className="modal-actions">
          <button type="button" className="modal-close-btn" onClick={onClose}>
            Acknowledge & Close
          </button>
        </div>
      </div>
    </div>
  )
}
