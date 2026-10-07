/**
 * MedBrief AI — Requires Attention Section
 * Step 5: Doctor Dashboard UI
 *
 * Highlights clinical tasks needing physician review without making
 * unsupported claims about clinical urgency.
 */

import React from 'react'
import type { AttentionItem } from '../../types/dashboard'
import './RequiresAttention.css'

interface RequiresAttentionProps {
  items: AttentionItem[]
  loading?: boolean
  onItemAction: (item: AttentionItem) => void
}

export const RequiresAttention: React.FC<RequiresAttentionProps> = ({
  items,
  loading = false,
  onItemAction,
}) => {
  if (loading) {
    return (
      <section className="attention-section" aria-label="Loading items requiring attention">
        <div className="section-header-row">
          <div className="section-title-wrap">
            <div className="section-icon-badge" aria-hidden="true">
              📋
            </div>
            <h2 className="section-title">Requires Attention</h2>
          </div>
        </div>
        <div className="attention-cards-list">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="attention-card skeleton" aria-hidden="true">
              <div className="attention-main-col">
                <div className="skeleton-box" style={{ width: 120, height: 16 }} />
                <div className="skeleton-box" style={{ width: '60%', height: 20, margin: '0.3rem 0' }} />
                <div className="skeleton-box" style={{ width: '85%', height: 14 }} />
              </div>
              <div className="skeleton-box" style={{ width: 90, height: 32 }} />
            </div>
          ))}
        </div>
      </section>
    )
  }

  if (items.length === 0) {
    return (
      <section className="attention-section" aria-label="Items requiring attention">
        <div className="section-header-row">
          <div className="section-title-wrap">
            <div className="section-icon-badge" aria-hidden="true">
              📋
            </div>
            <h2 className="section-title">Requires Attention</h2>
            <span className="section-count-badge">0 Items</span>
          </div>
        </div>
        <div className="attention-empty-state">
          <div className="empty-icon" aria-hidden="true">
            ✅
          </div>
          <h3 className="empty-title">You're all caught up</h3>
          <p className="empty-text">
            No diagnostic tests, medication modifications, or records currently require clinical review for your assigned caseload.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="attention-section" aria-label="Items requiring attention">
      <div className="section-header-row">
        <div className="section-title-wrap">
          <div className="section-icon-badge" aria-hidden="true">
            📋
          </div>
          <h2 className="section-title">Requires Attention</h2>
          <span className="section-count-badge">{items.length} Pending</span>
        </div>
        <p className="section-subtitle-text">
          Prioritized clinical items for physician validation and sign-off
        </p>
      </div>

      <div className="attention-cards-list" role="feed" aria-label="Attention Items">
        {items.map((item) => (
          <article key={item.id} className="attention-card" tabIndex={0}>
            <div className="attention-main-col">
              <div className="attention-meta-row">
                <span className="category-tag">{item.category}</span>
                <span className="patient-reference">{item.patientName}</span>
                <span className="patient-mrn-sub">({item.patientMrn})</span>
              </div>
              <h3 className="attention-title">{item.title}</h3>
              <p className="attention-desc">{item.description}</p>
            </div>

            <div className="attention-action-col">
              <span className="attention-status-pill">{item.status}</span>
              <button
                type="button"
                className="attention-action-btn"
                onClick={() => onItemAction(item)}
                aria-label={`${item.actionLabel} for ${item.patientName}`}
              >
                {item.actionLabel}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
