/**
 * MedBrief AI — Quick Actions Panel
 * Step 5: Doctor Dashboard UI
 *
 * Fast entry points into key clinical workflows, triggering
 * clear roadmap boundary guidance for unreleased steps.
 */

import React from 'react'
import type { QuickActionItem } from '../../types/dashboard'
import './QuickActions.css'

interface QuickActionsProps {
  actions: QuickActionItem[]
  onActionClick: (action: QuickActionItem) => void
}

export const QuickActions: React.FC<QuickActionsProps> = ({ actions, onActionClick }) => {
  return (
    <section className="quick-actions-section" aria-label="Quick Clinical Actions">
      <div className="section-header-row">
        <div className="section-title-wrap">
          <div className="section-icon-badge" aria-hidden="true">
            ⚡
          </div>
          <h2 className="section-title">Quick Actions</h2>
        </div>
        <p className="section-subtitle-text">Fast navigation to upcoming clinical features</p>
      </div>

      <div className="quick-actions-grid" role="list">
        {actions.map((act) => (
          <button
            key={act.id}
            type="button"
            className="quick-action-card"
            onClick={() => onActionClick(act)}
            role="listitem"
            aria-label={`${act.title} (${act.targetStep})`}
          >
            <div className="quick-action-icon" aria-hidden="true">
              {act.icon}
            </div>
            <h3 className="quick-action-title">{act.title}</h3>
            <p className="quick-action-desc">{act.description}</p>
            <span className="quick-action-step-tag">{act.targetStep}</span>
          </button>
        ))}
      </div>
    </section>
  )
}
