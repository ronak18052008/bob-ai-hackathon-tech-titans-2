/**
 * MedBrief AI — Recent Patient Activity Feed
 * Step 5: Doctor Dashboard UI
 *
 * Displays a chronological feed of recent clinical events,
 * document processing updates, and medication changes.
 */

import React from 'react'
import type { RecentActivityItem } from '../../types/dashboard'
import './RecentActivity.css'

interface RecentActivityProps {
  activities: RecentActivityItem[]
  loading?: boolean
}

export const RecentActivity: React.FC<RecentActivityProps> = ({ activities, loading = false }) => {
  if (loading) {
    return (
      <div className="activity-card-container" aria-label="Loading recent patient activity">
        <div className="activity-header-row">
          <h3 className="activity-title">Recent Patient Activity</h3>
        </div>
        <div className="activity-feed-list">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="activity-item-row skeleton" aria-hidden="true">
              <div className="skeleton-box" style={{ width: 32, height: 32 }} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="skeleton-box" style={{ width: '40%', height: 14 }} />
                <div className="skeleton-box" style={{ width: '80%', height: 16 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="activity-card-container" role="region" aria-label="Recent Patient Activity">
      <div className="activity-header-row">
        <div className="activity-title-wrap">
          <span aria-hidden="true">⚡</span>
          <h3 className="activity-title">Recent Patient Activity</h3>
        </div>
        <span className="section-count-badge">Live Caseload</span>
      </div>

      <div className="activity-feed-list">
        {activities.map((item) => (
          <article key={item.id} className="activity-item-row" tabIndex={0}>
            <div className="activity-icon-badge" aria-hidden="true">
              {item.icon}
            </div>
            <div className="activity-details-col">
              <div className="activity-top-line">
                <span className="activity-type-tag">{item.type}</span>
                <time className="activity-time-stamp">{item.timestamp}</time>
              </div>
              <p className="activity-summary-text">{item.summary}</p>
              <div className="activity-patient-sub">
                Patient: <strong>{item.patientName}</strong> ({item.patientMrn})
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
