/**
 * MedBrief AI — Role-Based Access Control Component Guard
 * Step 4: Authentication + RBAC
 *
 * Enforces role restrictions on views.
 * If user lacks required role, displays an accessible clinical access denied panel.
 */

import React from 'react'
import { useAuth } from '../../context/AuthContext'
import './ProtectedRoute.css'

interface RoleGuardProps {
  requiredRole: string
  fallback?: React.ReactNode
  children: React.ReactNode
}

export const RoleGuard: React.FC<RoleGuardProps> = ({
  requiredRole,
  fallback,
  children,
}) => {
  const { user, hasRole } = useAuth()

  const allowed = hasRole(requiredRole)

  if (allowed) {
    return <>{children}</>
  }

  if (fallback) {
    return <>{fallback}</>
  }

  return (
    <div className="access-denied-container" role="alert">
      <div className="access-denied-card">
        <div className="access-denied-icon" aria-hidden="true">
          🛡️
        </div>
        <h3>Access Restricted</h3>
        <p>
          Your account (<strong>{user?.display_name || user?.email}</strong>) does not have
          the required permissions for this area.
        </p>
        <p>
          Required Role: <span className="access-denied-role-badge">{requiredRole.toUpperCase()}</span>
        </p>
        <p>
          Assigned Roles: {user?.roles?.map((r) => r.toUpperCase()).join(', ') || 'None'}
        </p>
      </div>
    </div>
  )
}
