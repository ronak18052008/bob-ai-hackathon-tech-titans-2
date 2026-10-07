/**
 * MedBrief AI — Application Entry Point
 * Step 5: Doctor Dashboard UI
 *
 * Integrates:
 * - Step 1: Branded Cinematic Intro Experience
 * - Step 4: Authentication Context, Session Restoration, and Protected Routes
 * - Step 5: Full Doctor Dashboard Clinical Workspace (for DOCTOR role)
 * - Preserves Step 4 Admin verification shell (for ADMIN role)
 */

import React, { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { MedBriefIntro } from './components/MedBriefIntro/MedBriefIntro'
import { DoctorDashboard } from './components/dashboard/DoctorDashboard'
import { Logo } from './components/common/Logo'
import type { AccessCheckResult } from './types/auth'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import './App.css'

interface HealthResponse {
  status: string
  service: string
  database: string
}

const AdminShellView: React.FC<{ onReplayIntro: () => void }> = ({ onReplayIntro }) => {
  const { user, logout, testAdminAccess } = useAuth()
  const [adminProbeResult, setAdminProbeResult] = useState<AccessCheckResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null)

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetch(`${apiUrl}/health`)
      .then((res) => res.json())
      .then((data) => setBackendHealth(data))
      .catch(() => setBackendHealth(null))
  }, [apiUrl])

  const handleAdminProbe = async () => {
    setLoading(true)
    const res = await testAdminAccess()
    setAdminProbeResult(res)
    setLoading(false)
  }

  return (
    <div className="clinical-app-shell">
      <nav className="clinical-navbar" aria-label="Administrative Navigation">
        <Logo size={34} onClick={onReplayIntro} />
        <div className="navbar-actions-group">
          <div className="user-identity-card">
            <span className="user-avatar-badge" aria-hidden="true">
              🛡️
            </span>
            <div className="user-info-text">
              <span className="user-name">{user?.display_name || user?.email}</span>
              <span className="user-meta-sub">{user?.role_title || 'Administrator'}</span>
            </div>
            <span className="role-pill admin">ADMIN</span>
          </div>

          <button
            type="button"
            className="nav-btn replay-btn"
            onClick={onReplayIntro}
            title="Replay cinematic branded introduction"
          >
            ▶ Replay Intro
          </button>

          <button
            type="button"
            className="nav-btn logout-btn"
            onClick={() => logout()}
            title="Sign out of administrative session"
          >
            Sign Out
          </button>
        </div>
      </nav>

      <main className="clinical-main-content">
        <header className="step-status-header">
          <div className="step-status-title">
            <h2>Administrative System Shell</h2>
            <p>
              Current session: <strong>{user?.display_name}</strong> (Administrator privileges active).
            </p>
          </div>
          <div className="active-step-badge">Enterprise Admin Portal</div>
        </header>

        <section className="tab-panel-card">
          <div className="panel-header-row">
            <div>
              <h3>Enterprise Access Control & Clinical Isolation</h3>
              <p>
                Administrators manage system configuration, database connectivity, and immutable audit trails.
                Under HIPAA minimum necessary principles, administrators do not access patient clinical health records.
              </p>
            </div>
            <span className="badge-success val">
              {backendHealth ? `DB: ${backendHealth.database}` : 'Admin Verified'}
            </span>
          </div>

          <div className="probe-grid">
            <div className="probe-card">
              <h4>🛡️ System Admin Route Probe</h4>
              <p>
                Verifies server-side RBAC via <code>GET /api/v1/auth/admin-access</code>.
              </p>
              <button
                type="button"
                className="probe-btn primary"
                onClick={handleAdminProbe}
                disabled={loading}
              >
                {loading ? 'Probing...' : 'Execute Admin RBAC Probe'}
              </button>
              {adminProbeResult && (
                <pre
                  className={`probe-result-box ${
                    adminProbeResult.statusCode === 200 ? 'success' : 'error'
                  }`}
                >
                  HTTP {adminProbeResult.statusCode} — {JSON.stringify(adminProbeResult, null, 2)}
                </pre>
              )}
            </div>
          </div>

          <div className="next-step-notice">
            <span className="next-step-icon" aria-hidden="true">
              🩺
            </span>
            <div>
              <strong>To access the Physician Clinical Workspace:</strong> Please sign out and sign in using
              an Attending Physician account (<code>dr.sarah.chen@demo-clinic.test</code>).
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

const AuthenticatedRouter: React.FC<{ onReplayIntro: () => void }> = ({ onReplayIntro }) => {
  const { user } = useAuth()
  const isAdmin = user?.roles?.includes('admin')

  // If user is Admin, render the administrative view; if Doctor, render Doctor Dashboard
  if (isAdmin) {
    return <AdminShellView onReplayIntro={onReplayIntro} />
  }

  return <DoctorDashboard onReplayIntro={onReplayIntro} />
}

function App() {
  const [showIntro, setShowIntro] = useState<boolean>(true)

  return (
    <ErrorBoundary fallbackTitle="MedBrief AI Application Error">
      <ToastProvider>
        <AuthProvider>
          {/* ── Branded Cinematic Intro Experience (Step 1) ── */}
          {showIntro && (
            <MedBriefIntro onComplete={() => setShowIntro(false)} />
          )}

          {/* ── Protected Route Shell (Step 4 & 5) ── */}
          <ProtectedRoute>
            <ErrorBoundary fallbackTitle="Clinical Workspace Error">
              <AuthenticatedRouter onReplayIntro={() => setShowIntro(true)} />
            </ErrorBoundary>
          </ProtectedRoute>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  )
}

export default App
