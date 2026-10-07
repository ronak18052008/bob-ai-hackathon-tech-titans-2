/**
 * MedBrief AI — Clinical Authentication View
 * Step 4: Authentication + RBAC
 *
 * Provides accessible, responsive login UI matching MedBrief AI's clinical design system.
 * Includes quick-fill options for seeded demo accounts (Doctor & Admin).
 */

import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { BrandEmblem } from '../MedBriefIntro/BrandEmblem'
import './LoginView.css'

interface LoginViewProps {
  onSuccess?: () => void
}

export const LoginView: React.FC<LoginViewProps> = ({ onSuccess }) => {
  const { login, error: contextError, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)
    clearError()

    if (!email.trim()) {
      setLocalError('Please enter your clinical email address.')
      return
    }

    if (!password) {
      setLocalError('Please enter your password.')
      return
    }

    setIsSubmitting(true)
    try {
      await login(email.trim(), password)
      if (onSuccess) {
        onSuccess()
      }
    } catch {
      // Handled via context error state
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    setLocalError(null)
    clearError()
  }

  const activeError = localError || contextError

  return (
    <div className="login-page-wrapper">
      <main className="login-card" role="main" aria-labelledby="login-title">
        {/* Header with MedBrief AI Vector Emblem */}
        <header className="login-header">
          <div className="login-brand-icon">
            <BrandEmblem size={64} hideText />
          </div>
          <h1 id="login-title" className="login-title">
            MedBrief AI
          </h1>
          <p className="login-subtitle">Intelligent Medical Summarization</p>
          <div className="login-badge-row">
            <span className="clinical-badge">Clinical Enterprise Access</span>
            <span className="clinical-badge">HIPAA / Zero-PHI Verified</span>
          </div>
        </header>

        {/* Accessible Error Banner */}
        {activeError && (
          <div className="login-error-alert" role="alert" aria-live="assertive">
            <span className="login-error-icon" aria-hidden="true">
              ⚠
            </span>
            <div className="login-error-text">{activeError}</div>
          </div>
        )}

        {/* Credentials Form */}
        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="auth-email" className="form-label">
              Clinical Email
            </label>
            <input
              id="auth-email"
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. dr.sarah.chen@demo-clinic.test"
              autoComplete="username"
              disabled={isSubmitting}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="auth-password" className="form-label">
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              autoComplete="current-password"
              disabled={isSubmitting}
              required
            />
          </div>

          <button
            type="submit"
            className="login-submit-btn"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner" aria-hidden="true" />
                <span>Authenticating...</span>
              </>
            ) : (
              <span>Sign In to Clinical Environment</span>
            )}
          </button>
        </form>

        {/* Quick Demo Fill Buttons */}
        <section className="demo-accounts-section" aria-label="Development Demo Accounts">
          <div className="demo-section-title">Clinical Quick Access</div>
          <div className="demo-buttons-grid">
            <button
              type="button"
              className="demo-fill-btn doctor-demo"
              onClick={() =>
                handleQuickFill('dr.sarah.chen@demo-clinic.test', 'MedBrief2026!')
              }
              disabled={isSubmitting}
            >
              <strong>Dr. Sarah Chen</strong>
              <span>Attending Physician (Cardiology)</span>
            </button>

            <button
              type="button"
              className="demo-fill-btn admin-demo"
              onClick={() =>
                handleQuickFill('admin@demo-clinic.test', 'MedBriefAdmin2026!')
              }
              disabled={isSubmitting}
            >
              <strong>Alex Rivera</strong>
              <span>Systems Administrator (Enterprise Admin)</span>
            </button>
          </div>
        </section>

        {/* Security & Audit Notice */}
        <footer className="login-card-footer">
          Authorized clinical & system personnel only. All access events and patient record
          queries are recorded in immutable audit logs.
        </footer>
      </main>
    </div>
  )
}
