/**
 * MedBrief AI — Key Metric Cards
 * Step 5: Doctor Dashboard UI
 *
 * Renders 5 responsive clinical metric cards:
 * 1. Active Patients
 * 2. Records to Review
 * 3. Pending Investigations
 * 4. Medication Changes
 * 5. Follow-ups Due
 */

import React from 'react'
import type { DashboardMetric } from '../../types/dashboard'
import './MetricCards.css'

interface MetricCardsProps {
  metrics: DashboardMetric[]
  loading?: boolean
}

export const MetricCards: React.FC<MetricCardsProps> = ({ metrics, loading = false }) => {
  if (loading) {
    return (
      <div className="metrics-grid" aria-label="Loading clinical metrics">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="metric-card skeleton" aria-hidden="true">
            <div className="metric-top-row">
              <div className="skeleton-box" style={{ width: 36, height: 36 }} />
              <div className="skeleton-box" style={{ width: 50, height: 16 }} />
            </div>
            <div className="skeleton-box" style={{ width: '40%', height: 28, margin: '0.4rem 0' }} />
            <div className="skeleton-box" style={{ width: '70%', height: 14 }} />
            <div className="skeleton-box" style={{ width: '90%', height: 12 }} />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="metrics-grid" role="region" aria-label="Key Clinical Metrics">
      {metrics.map((m) => (
        <article
          key={m.id}
          className={`metric-card ${m.statusType || 'neutral'}`}
          tabIndex={0}
          aria-label={`${m.label}: ${m.value}. ${m.subtext}`}
        >
          <div className="metric-top-row">
            <div className="metric-icon-box" aria-hidden="true">
              {m.icon}
            </div>
            {m.statusType === 'attention' && (
              <span className="metric-status-tag attention">Action</span>
            )}
            {m.statusType === 'warning' && (
              <span className="metric-status-tag warning">Pending</span>
            )}
          </div>
          <div className="metric-value">{m.value}</div>
          <div className="metric-label">{m.label}</div>
          <p className="metric-subtext">{m.subtext}</p>
        </article>
      ))}
    </div>
  )
}
