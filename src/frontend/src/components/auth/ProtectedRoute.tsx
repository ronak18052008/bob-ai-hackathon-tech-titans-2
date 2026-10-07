/**
 * MedBrief AI — Protected Route Wrapper
 * Step 4: Authentication + RBAC
 *
 * Ensures unauthenticated users cannot access protected views.
 * Restores sessions seamlessly without flashing protected content.
 */

import React from 'react'
import { useAuth } from '../../context/AuthContext'
import { LoginView } from './LoginView'
import './ProtectedRoute.css'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { status } = useAuth()

  if (status === 'loading') {
    return (
      <div className="auth-loading-screen" role="status" aria-live="polite">
        <div className="auth-loading-content">
          <div className="clinical-spinner-large" aria-hidden="true" />
          <p className="auth-loading-text">Verifying clinical credentials...</p>
        </div>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return <LoginView />
  }

  return <>{children}</>
}
