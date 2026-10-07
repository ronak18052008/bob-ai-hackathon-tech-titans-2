import React, { useState, useEffect, useCallback } from 'react'
import { ParticleCanvas } from './ParticleCanvas'
import { BrandEmblem } from './BrandEmblem'
import './MedBriefIntro.css'

interface MedBriefIntroProps {
  onComplete: () => void
}

export const MedBriefIntro: React.FC<MedBriefIntroProps> = ({ onComplete }) => {
  // Scene tracks progression from 1 through 8
  const [scene, setScene] = useState<number>(1)
  const [isTransitioningOut, setIsTransitioningOut] = useState<boolean>(false)
  const [isSkipped, setIsSkipped] = useState<boolean>(false)

  // Stage narrative labels corresponding to the conceptual flow
  const getStageNarrative = (currentScene: number) => {
    switch (currentScene) {
      case 1:
        return 'INITIALIZING CLINICAL ENVIRONMENT'
      case 2:
        return 'INGESTING MEDICAL RECORDS & KNOWLEDGE'
      case 3:
      case 4:
        return 'SYNTHESIZING CLINICAL INTELLIGENCE'
      case 5:
      case 6:
      case 7:
        return 'MEDBRIEF AI'
      default:
        return ''
    }
  }

  const handleFinish = useCallback(() => {
    if (isTransitioningOut) return
    setIsTransitioningOut(true)
    setTimeout(() => {
      onComplete()
    }, 700) // matches dissolve transition duration
  }, [isTransitioningOut, onComplete])

  useEffect(() => {
    // Check for user's reduced-motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (prefersReducedMotion) {
      setScene(7)
      const timer = setTimeout(() => {
        handleFinish()
      }, 1600)
      return () => clearTimeout(timer)
    }

    // Timeline sequence in milliseconds
    const timeline = [
      { scene: 2, delay: 1200 }, // Scene 2: Book & DNA Helix
      { scene: 3, delay: 2800 }, // Scene 3: Medical Cross / Emblem
      { scene: 4, delay: 4200 }, // Scene 4: Intelligence Light Reveal
      { scene: 5, delay: 5400 }, // Scene 5: MedBrief AI Title
      { scene: 6, delay: 6500 }, // Scene 6: Tagline
      { scene: 7, delay: 7600 }, // Scene 7: Final Brand Hold
      { scene: 8, delay: 8800 }, // Scene 8: Smooth Transition
    ]

    const timeouts = timeline.map(({ scene: nextScene, delay }) =>
      setTimeout(() => {
        if (!isSkipped) {
          if (nextScene === 8) {
            handleFinish()
          } else {
            setScene(nextScene)
          }
        }
      }, delay)
    )

    return () => {
      timeouts.forEach((t) => clearTimeout(t))
    }
  }, [handleFinish, isSkipped])

  // Allow keyboard skip (Escape, Space, Enter)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        setIsSkipped(true)
        handleFinish()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleFinish])

  return (
    <div
      className={`medbrief-intro-overlay ${isTransitioningOut ? 'fade-out' : ''}`}
      role="banner"
      aria-label="MedBrief AI Introduction"
    >
      {/* Living Atmospheric Background */}
      <div className="atmospheric-bg">
        <div className="radial-core-glow" />
        <div className="radial-top-glow" />
      </div>

      {/* Lightweight Medical Network Particle Layer */}
      <ParticleCanvas intensity={scene >= 2 ? 0.9 : 0.4} />

      {/* Main Cinematic Stage */}
      <main className="intro-stage">
        {/* Conceptual Narrative Label */}
        <div className="narrative-tracker" aria-live="polite">
          <span className="narrative-text">{getStageNarrative(scene)}</span>
        </div>

        {/* Central Brand Emblem & Typography */}
        <BrandEmblem scene={scene} />

        {/* Visual Storytelling Pipeline Breadcrumb */}
        <div className="storytelling-pipeline">
          <span className={`step ${scene >= 1 ? 'active' : ''}`}>Medical Records</span>
          <span className="arrow">→</span>
          <span className={`step ${scene >= 2 ? 'active' : ''}`}>Medical Knowledge</span>
          <span className="arrow">→</span>
          <span className={`step ${scene >= 3 ? 'active' : ''}`}>AI Intelligence</span>
          <span className="arrow">→</span>
          <span className={`step ${scene >= 5 ? 'active highlight' : ''}`}>MedBrief AI</span>
        </div>
      </main>

      {/* Subtle Skip Control */}
      <button
        type="button"
        className="intro-skip-button"
        onClick={() => {
          setIsSkipped(true)
          handleFinish()
        }}
        aria-label="Skip introductory animation"
      >
        Skip Intro
      </button>
    </div>
  )
}
