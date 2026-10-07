/**
 * MedBrief AI — Brand Logo Component
 * Step 5: Top-Left Prominent Website Logo
 *
 * Clickable logo with official asset & vector BrandEmblem fallback.
 * Wordmark: "MedBrief" in emerald green (#0a5c36), "AI" in warm gold (#d97706).
 * Tagline: "Intelligent Medical Summarization" in slate navy (#1e293b).
 */

import React, { useState } from 'react'
import { BrandEmblem } from '../MedBriefIntro/BrandEmblem'
import './Logo.css'

interface LogoProps {
  onClick?: () => void
  size?: number
  showTagline?: boolean
  className?: string
  useOfficialImage?: boolean
}

export const Logo: React.FC<LogoProps> = ({
  onClick,
  size = 40,
  showTagline = true,
  className = '',
  useOfficialImage = true,
}) => {
  const [imageError, setImageError] = useState(false)

  return (
    <button
      type="button"
      className={`medbrief-logo-link ${className}`}
      onClick={onClick}
      aria-label="MedBrief AI Home — Doctor Dashboard"
    >
      <div className="medbrief-logo-mark" style={{ width: size, height: size }}>
        {useOfficialImage && !imageError ? (
          <img
            src="/medbrief-logo.jpg"
            alt="MedBrief AI Official Logo"
            className="medbrief-official-logo-img"
            onError={() => setImageError(true)}
            style={{ width: size, height: size, objectFit: 'contain' }}
          />
        ) : (
          <BrandEmblem size={size} hideText />
        )}
      </div>
      <div className="medbrief-logo-text">
        <div className="medbrief-wordmark">
          <span className="medbrief-brand-name">MedBrief</span>
          <span className="medbrief-ai-accent">AI</span>
        </div>
        {showTagline && (
          <div className="medbrief-tagline">INTELLIGENT MEDICAL SUMMARIZATION</div>
        )}
      </div>
    </button>
  )
}
