import React from 'react'

interface BrandEmblemProps {
  scene?: number // 1 to 7, defaults to 7 for static emblem usage
  className?: string
  size?: number
  hideText?: boolean
}

export const BrandEmblem: React.FC<BrandEmblemProps> = ({
  scene = 7,
  className = '',
  size,
  hideText = false,
}) => {
  // Scene-dependent animation classes & opacities
  const showBook = scene >= 2
  const showHelix = scene >= 2
  const showCross = scene >= 3
  const showGlow = scene >= 4
  const showText = scene >= 5
  const showTagline = scene >= 6

  return (
    <div
      className={`brand-emblem-wrapper ${className}`}
      style={size ? { width: size, height: size, maxWidth: size, maxHeight: size } : undefined}
    >
      <svg
        viewBox="0 0 500 500"
        className="brand-emblem-svg"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="MedBrief AI Emblem"
      >
        <defs>
          {/* Gradients */}
          <linearGradient id="bookCoverGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1e3a8a" />
            <stop offset="50%" stopColor="#0f2b48" />
            <stop offset="100%" stopColor="#071b30" />
          </linearGradient>

          <linearGradient id="bookPageGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.4" />
          </linearGradient>

          <linearGradient id="goldCrossGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fef08a" />
            <stop offset="35%" stopColor="#f59e0b" />
            <stop offset="85%" stopColor="#d97706" />
            <stop offset="100%" stopColor="#b45309" />
          </linearGradient>

          <linearGradient id="dnaStrandGrad" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="70%" stopColor="#93c5fd" />
            <stop offset="100%" stopColor="#fcd34d" />
          </linearGradient>

          <radialGradient id="auraGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.45" />
            <stop offset="40%" stopColor="#38bdf8" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#0284c7" stopOpacity="0" />
          </radialGradient>

          <radialGradient id="centerBurst" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.6" />
            <stop offset="30%" stopColor="#fbbf24" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
          </radialGradient>

          {/* Filters */}
          <filter id="softGoldGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="8" result="blur1" />
            <feGaussianBlur stdDeviation="16" result="blur2" />
            <feMerge>
              <feMergeNode in="blur2" />
              <feMergeNode in="blur1" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="blueCyanGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ── AMBIENT INTELLIGENCE AURA (Scene 4+) ── */}
        <g className={`ambient-intelligence ${showGlow ? 'visible' : ''}`}>
          <circle cx="250" cy="120" r="130" fill="url(#auraGlow)" className="pulse-aura" />
          <circle cx="250" cy="120" r="60" fill="url(#centerBurst)" className="center-sparkle" />
          
          {/* Subtle light rays radiating from emblem */}
          <g className="light-rays" opacity="0.35">
            <line x1="250" y1="120" x2="250" y2="20" stroke="#fef08a" strokeWidth="1" strokeDasharray="4 6" />
            <line x1="250" y1="120" x2="330" y2="50" stroke="#fef08a" strokeWidth="1" strokeDasharray="3 5" />
            <line x1="250" y1="120" x2="170" y2="50" stroke="#fef08a" strokeWidth="1" strokeDasharray="3 5" />
            <line x1="250" y1="120" x2="360" y2="120" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4 6" />
            <line x1="250" y1="120" x2="140" y2="120" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4 6" />
          </g>
        </g>

        {/* ── OPEN MEDICAL KNOWLEDGE BOOK (Scene 2+) ── */}
        <g className={`book-group ${showBook ? 'visible' : ''}`} filter="url(#blueCyanGlow)">
          {/* Outer Cover Base & Spine */}
          <path
            d="M 250 315 C 238 322, 225 320, 160 305 C 130 298, 115 295, 105 295 L 105 160 C 120 160, 140 164, 175 174 C 215 186, 235 192, 250 198 C 265 192, 285 186, 325 174 C 360 164, 380 160, 395 160 L 395 295 C 385 295, 370 298, 340 305 C 275 320, 262 322, 250 315 Z"
            fill="url(#bookCoverGrad)"
            stroke="#1e40af"
            strokeWidth="3.5"
            className="book-cover"
          />

          {/* Book Spine Center Notch */}
          <path
            d="M 235 315 C 243 324, 257 324, 265 315 C 257 319, 243 319, 235 315 Z"
            fill="#38bdf8"
            opacity="0.8"
          />

          {/* Fanned Layered Pages - Left Flank */}
          <g className="fanned-pages-left">
            <path
              d="M 105 290 C 115 290, 130 286, 165 278 C 210 268, 235 264, 246 270"
              fill="none"
              stroke="#60a5fa"
              strokeWidth="2.5"
              strokeLinecap="round"
              opacity="0.8"
            />
            <path
              d="M 112 275 C 122 275, 138 271, 172 264 C 215 254, 236 252, 246 256"
              fill="none"
              stroke="#93c5fd"
              strokeWidth="2"
              strokeLinecap="round"
              opacity="0.7"
            />
            <path
              d="M 120 260 C 130 260, 145 256, 180 248 C 218 240, 238 238, 246 242"
              fill="none"
              stroke="#bfdbfe"
              strokeWidth="1.8"
              strokeLinecap="round"
              opacity="0.6"
            />
            {/* Left page vertical edge fan */}
            <path
              d="M 105 160 L 105 295 M 112 170 L 112 285 M 120 180 L 120 275"
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
              opacity="0.6"
            />
          </g>

          {/* Fanned Layered Pages - Right Flank */}
          <g className="fanned-pages-right">
            <path
              d="M 395 290 C 385 290, 370 286, 335 278 C 290 268, 265 264, 254 270"
              fill="none"
              stroke="#60a5fa"
              strokeWidth="2.5"
              strokeLinecap="round"
              opacity="0.8"
            />
            <path
              d="M 388 275 C 378 275, 362 271, 328 264 C 285 254, 264 252, 254 256"
              fill="none"
              stroke="#93c5fd"
              strokeWidth="2"
              strokeLinecap="round"
              opacity="0.7"
            />
            <path
              d="M 380 260 C 370 260, 355 256, 320 248 C 282 240, 262 238, 254 242"
              fill="none"
              stroke="#bfdbfe"
              strokeWidth="1.8"
              strokeLinecap="round"
              opacity="0.6"
            />
            {/* Right page vertical edge fan */}
            <path
              d="M 395 160 L 395 295 M 388 170 L 388 285 M 380 180 L 380 275"
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
              opacity="0.6"
            />
          </g>

          {/* Inner Open Book Sheets */}
          <path
            d="M 248 285 C 238 275, 205 260, 135 235 L 135 155 C 205 180, 238 195, 248 205 Z"
            fill="url(#bookPageGrad)"
            stroke="#93c5fd"
            strokeWidth="2"
            opacity="0.6"
          />
          <path
            d="M 252 285 C 262 275, 295 260, 365 235 L 365 155 C 295 180, 262 195, 252 205 Z"
            fill="url(#bookPageGrad)"
            stroke="#93c5fd"
            strokeWidth="2"
            opacity="0.6"
          />
        </g>

        {/* ── MOLECULAR & NEURAL NETWORKS (Scene 2+) ── */}
        <g className={`molecules-group ${showHelix ? 'visible' : ''}`}>
          {/* Left Molecular Constellation */}
          <g className="mol-left" stroke="#38bdf8" strokeWidth="1.5" opacity="0.85">
            <line x1="150" y1="210" x2="175" y2="195" />
            <line x1="175" y1="195" x2="200" y2="215" />
            <line x1="200" y1="215" x2="185" y2="245" />
            <line x1="185" y1="245" x2="155" y2="240" />
            <line x1="155" y1="240" x2="150" y2="210" />
            <line x1="150" y1="210" x2="135" y2="230" />
            <line x1="200" y1="215" x2="220" y2="205" />

            <circle cx="150" cy="210" r="4.5" fill="#bae6fd" />
            <circle cx="175" cy="195" r="4" fill="#38bdf8" />
            <circle cx="200" cy="215" r="5" fill="#bae6fd" />
            <circle cx="185" cy="245" r="4" fill="#38bdf8" />
            <circle cx="155" cy="240" r="4.5" fill="#7dd3fc" />
            <circle cx="135" cy="230" r="3.5" fill="#93c5fd" />
            <circle cx="220" cy="205" r="3.5" fill="#e0f2fe" />
          </g>

          {/* Right Molecular Constellation */}
          <g className="mol-right" stroke="#38bdf8" strokeWidth="1.5" opacity="0.85">
            <line x1="350" y1="210" x2="325" y2="195" />
            <line x1="325" y1="195" x2="300" y2="215" />
            <line x1="300" y1="215" x2="315" y2="245" />
            <line x1="315" y1="245" x2="345" y2="240" />
            <line x1="345" y1="240" x2="350" y2="210" />
            <line x1="350" y1="210" x2="365" y2="230" />
            <line x1="300" y1="215" x2="280" y2="205" />

            <circle cx="350" cy="210" r="4.5" fill="#bae6fd" />
            <circle cx="325" cy="195" r="4" fill="#38bdf8" />
            <circle cx="300" cy="215" r="5" fill="#bae6fd" />
            <circle cx="315" cy="245" r="4" fill="#38bdf8" />
            <circle cx="345" cy="240" r="4.5" fill="#7dd3fc" />
            <circle cx="365" cy="230" r="3.5" fill="#93c5fd" />
            <circle cx="280" cy="205" r="3.5" fill="#e0f2fe" />
          </g>
        </g>

        {/* ── CENTRAL DNA DOUBLE HELIX (Scene 2+) ── */}
        <g className={`dna-group ${showHelix ? 'visible' : ''}`}>
          {/* DNA Rungs / Base Pairs linking strands */}
          <g className="dna-rungs" stroke="#93c5fd" strokeWidth="2.5" opacity="0.85">
            <line x1="242" y1="280" x2="258" y2="280" />
            <line x1="237" y1="262" x2="263" y2="262" />
            <line x1="245" y1="244" x2="255" y2="244" />
            <line x1="258" y1="226" x2="242" y2="226" />
            <line x1="264" y1="208" x2="236" y2="208" />
            <line x1="256" y1="190" x2="244" y2="190" />
            <line x1="240" y1="172" x2="260" y2="172" />
            <line x1="234" y1="154" x2="266" y2="154" />
          </g>

          {/* DNA Strand 1 - Sinusoidal Helix */}
          <path
            d="M 250 295 C 235 280, 235 265, 250 248 C 265 230, 265 210, 250 195 C 235 180, 235 160, 250 145 C 242 135, 230 130, 222 125"
            fill="none"
            stroke="url(#dnaStrandGrad)"
            strokeWidth="3.5"
            strokeLinecap="round"
            className="dna-strand strand-left"
          />

          {/* DNA Strand 2 - Opposite Phase Helix */}
          <path
            d="M 250 295 C 265 280, 265 265, 250 248 C 235 230, 235 210, 250 195 C 265 180, 265 160, 250 145 C 258 135, 270 130, 278 125"
            fill="none"
            stroke="url(#dnaStrandGrad)"
            strokeWidth="3.5"
            strokeLinecap="round"
            className="dna-strand strand-right"
          />

          {/* Reaching Tendril Terminal Nodes */}
          <circle cx="222" cy="125" r="3.5" fill="#fbbf24" />
          <circle cx="278" cy="125" r="3.5" fill="#fbbf24" />
        </g>

        {/* ── GOLDEN MEDICAL CROSS / INFINITY EMBLEM (Scene 3+) ── */}
        <g
          className={`cross-group ${showCross ? 'visible' : ''}`}
          filter="url(#softGoldGlow)"
        >
          {/* Outer Cross Shadow/Backdrop */}
          <path
            d="M 235 70 C 235 60, 243 52, 250 52 C 257 52, 265 60, 265 70 L 265 85 L 280 85 C 290 85, 298 93, 298 100 C 298 107, 290 115, 280 115 L 265 115 L 265 130 C 265 140, 257 148, 250 148 C 243 148, 235 140, 235 130 L 235 115 L 220 115 C 210 115, 202 107, 202 100 C 202 93, 210 85, 220 85 L 235 85 Z"
            fill="url(#goldCrossGrad)"
            className="cross-outer-silhouette"
          />

          {/* Organic Intertwined Infinity Ribbon Center within the Cross */}
          <path
            d="M 236 90 C 230 96, 230 104, 236 110 C 242 116, 246 116, 250 110 C 254 104, 258 104, 264 110 C 270 116, 270 104, 264 96 C 258 88, 254 88, 250 96 C 246 104, 242 104, 236 90 Z"
            fill="none"
            stroke="#ffffff"
            strokeWidth="3.2"
            strokeLinecap="round"
            opacity="0.95"
            className="infinity-ribbon"
          />

          {/* Central Radiance Accent */}
          <circle cx="250" cy="100" r="5" fill="#ffffff" opacity="0.9" />
          <circle cx="250" cy="100" r="12" fill="#fef08a" opacity="0.35" />
        </g>
      </svg>

      {/* ── BRAND TYPOGRAPHY (Scene 5 & 6) ── */}
      {!hideText && (
        <div className={`brand-text-container ${showText ? 'visible' : ''}`}>
          <div className="brand-title">
            <span className="brand-medbrief">MedBrief</span>
            <span className="brand-ai">AI</span>
          </div>
          <div className={`brand-tagline ${showTagline ? 'visible' : ''}`}>
            INTELLIGENT MEDICAL SUMMARIZATION
          </div>
        </div>
      )}
    </div>
  )
}
