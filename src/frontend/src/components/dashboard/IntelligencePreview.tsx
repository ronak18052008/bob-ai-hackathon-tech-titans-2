/**
 * MedBrief AI — Clinical Intelligence Preview
 * Step 5: Doctor Dashboard UI
 *
 * Showcases the 5 core AI capabilities planned in subsequent steps:
 * 1. Clinical Timeline
 * 2. Medication Changes
 * 3. Outstanding Investigations
 * 4. AI Clinical Summary
 * 5. Evidence & Sources
 */

import React from 'react'
import type { IntelligencePreviewItem } from '../../types/dashboard'
import './IntelligencePreview.css'

interface IntelligencePreviewProps {
  items: IntelligencePreviewItem[]
  onItemClick: (item: IntelligencePreviewItem) => void
}

export const IntelligencePreview: React.FC<IntelligencePreviewProps> = ({
  items,
  onItemClick,
}) => {
  return (
    <section className="intelligence-section" aria-label="Clinical Intelligence Previews">
      {/* Product Value Message Banner (Section 14) */}
      <div className="product-value-banner">
        <div className="value-banner-icon" aria-hidden="true">
          ✨
        </div>
        <div className="value-banner-content">
          <h3>From 200 pages of records to one clinically traceable patient story</h3>
          <p>
            MedBrief AI empowers physicians to rapidly understand what changed across hospitalizations,
            what remains unresolved, and what requires clinical attention next — backed by verifiable source citations.
          </p>
        </div>
      </div>

      <div className="section-header-row">
        <div className="section-title-wrap">
          <div className="section-icon-badge" aria-hidden="true">
            🧠
          </div>
          <h2 className="section-title">Clinical Intelligence Previews</h2>
        </div>
        <p className="section-subtitle-text">
          Core AI modules designed for physician decision-support
        </p>
      </div>

      <div className="intelligence-grid" role="list">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className="intelligence-card"
            onClick={() => onItemClick(item)}
            role="listitem"
            aria-label={`${item.title}: ${item.tagline}. Planned for ${item.plannedStep}.`}
          >
            <div className="intelligence-top">
              <div className="intelligence-icon" aria-hidden="true">
                {item.icon}
              </div>
              <span className="intelligence-badge">{item.badge}</span>
            </div>

            <div>
              <h3 className="intelligence-title">{item.title}</h3>
              <div className="intelligence-tagline">{item.tagline}</div>
            </div>

            <p className="intelligence-desc">{item.description}</p>

            <div className="intelligence-footer">
              <span>Planned Pipeline</span>
              <span>{item.plannedStep} →</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}
