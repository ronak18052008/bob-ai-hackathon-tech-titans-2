/**
 * MedBrief AI — Authentication Context & Session State
 * Step 4: Authentication + RBAC
 *
 * Manages user login, session persistence in localStorage, token verification
 * via GET /api/v1/auth/me, logout, and server-side role validation helpers.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { UserProfile, AuthStatus, LoginResponse, AccessCheckResult, PatientAccessCheckResult, UserPreferences } from '../types/auth'

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'light',
  reduced_motion: false,
  density: 'comfortable',
  notify_in_app: true,
  notify_doc_processing: true,
  notify_ai_completion: true,
  notify_follow_up_alerts: true,
  default_dashboard_view: 'dashboard',
  default_summary_type: 'CLINICAL_BRIEF',
  results_per_page: 10,
  date_format: 'YYYY-MM-DD',
}

interface AuthContextType {
  status: AuthStatus
  user: UserProfile | null
  token: string | null
  error: string | null
  preferences: UserPreferences
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
  hasRole: (role: string) => boolean
  updateProfile: (data: { display_name: string; role_title?: string; medical_license_id?: string }) => Promise<UserProfile>
  changePassword: (data: { current_password: string; new_password: string; confirm_password: string }) => Promise<void>
  updatePreferences: (data: Partial<UserPreferences>) => Promise<UserPreferences>
  testDoctorAccess: () => Promise<AccessCheckResult>
  testAdminAccess: () => Promise<AccessCheckResult>
  testPatientAccess: (patientId: string) => Promise<PatientAccessCheckResult>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'medbrief_clinical_token'
const PREFS_KEY = 'medbrief_clinical_preferences'

function applyDomPreferences(prefs: UserPreferences) {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-reduced-motion', String(prefs.reduced_motion))
  document.documentElement.setAttribute('data-density', prefs.density)
  document.documentElement.setAttribute('data-theme', prefs.theme)
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<UserProfile | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(PREFS_KEY)
        if (saved) {
          return { ...DEFAULT_PREFERENCES, ...JSON.parse(saved) }
        }
      } catch {
        // Fall back to defaults
      }
    }
    return DEFAULT_PREFERENCES
  })

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // Apply DOM attributes on preferences update
  useEffect(() => {
    applyDomPreferences(preferences)
  }, [preferences])

  // Helper to sync remote preferences
  const syncRemotePreferences = useCallback(async (authToken: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/preferences`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (res.ok) {
        const remote = (await res.json()) as UserPreferences
        setPreferences((prev) => {
          const merged = { ...prev, ...remote }
          localStorage.setItem(PREFS_KEY, JSON.stringify(merged))
          return merged
        })
      }
    } catch {
      // Keep local preferences
    }
  }, [apiUrl])

  // Initialize session on mount
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY)
    if (!savedToken) {
      setStatus('unauthenticated')
      return
    }

    // Verify token validity against backend /auth/me
    fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${savedToken}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error('Session expired')
        }
        return res.json() as Promise<UserProfile>
      })
      .then((profile) => {
        setUser(profile)
        setToken(savedToken)
        setStatus('authenticated')
        syncRemotePreferences(savedToken)
      })
      .catch(() => {
        // Expired or invalid session
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
        setToken(null)
        setStatus('unauthenticated')
      })
  }, [apiUrl, syncRemotePreferences])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null)
      try {
        const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password }),
        })

        const data = await res.json()
        if (!res.ok) {
          const message = data.detail || 'Authentication failed. Please verify credentials.'
          setError(message)
          throw new Error(message)
        }

        const loginData = data as LoginResponse
        localStorage.setItem(TOKEN_KEY, loginData.access_token)
        setToken(loginData.access_token)
        setUser(loginData.user)
        setStatus('authenticated')
        setError(null)
        syncRemotePreferences(loginData.access_token)
      } catch (err: unknown) {
        if (err instanceof Error && err.message) {
          setError(err.message)
        } else {
          setError('Unable to connect to clinical authentication server.')
        }
        throw err
      }
    },
    [apiUrl, syncRemotePreferences]
  )

  const logout = useCallback(async () => {
    if (token) {
      try {
        await fetch(`${apiUrl}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
      } catch {
        // Silent fail on network error during logout
      }
    }
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    setStatus('unauthenticated')
    setError(null)
  }, [apiUrl, token])

  const hasRole = useCallback(
    (role: string): boolean => {
      if (!user || !user.roles) return false
      return user.roles.map((r) => r.toLowerCase()).includes(role.toLowerCase())
    },
    [user]
  )

  const updateProfile = useCallback(
    async (data: { display_name: string; role_title?: string; medical_license_id?: string }): Promise<UserProfile> => {
      if (!token) throw new Error('Not authenticated')
      const res = await fetch(`${apiUrl}/api/v1/auth/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })
      const resData = await res.json()
      if (!res.ok) {
        throw new Error(resData.detail || 'Failed to update profile.')
      }
      const updated = resData as UserProfile
      setUser(updated)
      return updated
    },
    [apiUrl, token]
  )

  const changePassword = useCallback(
    async (data: { current_password: string; new_password: string; confirm_password: string }): Promise<void> => {
      if (!token) throw new Error('Not authenticated')
      const res = await fetch(`${apiUrl}/api/v1/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })
      const resData = await res.json()
      if (!res.ok) {
        throw new Error(resData.detail || 'Failed to change password.')
      }
    },
    [apiUrl, token]
  )

  const updatePreferences = useCallback(
    async (data: Partial<UserPreferences>): Promise<UserPreferences> => {
      const updated: UserPreferences = { ...preferences, ...data }
      setPreferences(updated)
      localStorage.setItem(PREFS_KEY, JSON.stringify(updated))
      applyDomPreferences(updated)

      if (token) {
        try {
          const res = await fetch(`${apiUrl}/api/v1/auth/preferences`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(updated),
          })
          if (res.ok) {
            const serverPrefs = (await res.json()) as UserPreferences
            setPreferences(serverPrefs)
            localStorage.setItem(PREFS_KEY, JSON.stringify(serverPrefs))
            return serverPrefs
          }
        } catch {
          // Local changes remain active
        }
      }
      return updated
    },
    [apiUrl, token, preferences]
  )

  const testDoctorAccess = useCallback(async (): Promise<AccessCheckResult> => {
    if (!token) return { status: 'unauthenticated', statusCode: 401 }
    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/doctor-access`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      return { ...data, statusCode: res.status }
    } catch (err: unknown) {
      return { status: 'network_error', detail: String(err), statusCode: 0 }
    }
  }, [apiUrl, token])

  const testAdminAccess = useCallback(async (): Promise<AccessCheckResult> => {
    if (!token) return { status: 'unauthenticated', statusCode: 401 }
    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/admin-access`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      return { ...data, statusCode: res.status }
    } catch (err: unknown) {
      return { status: 'network_error', detail: String(err), statusCode: 0 }
    }
  }, [apiUrl, token])

  const testPatientAccess = useCallback(
    async (patientId: string): Promise<PatientAccessCheckResult> => {
      if (!token) {
        return {
          status: 'unauthenticated',
          patient_id: patientId,
          user_id: '',
          access_granted: false,
          statusCode: 401,
        }
      }
      try {
        const res = await fetch(`${apiUrl}/api/v1/auth/patient-access/${patientId}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        return { ...data, statusCode: res.status }
      } catch (err: unknown) {
        return {
          status: 'error',
          patient_id: patientId,
          user_id: '',
          access_granted: false,
          detail: String(err),
          statusCode: 0,
        }
      }
    },
    [apiUrl, token]
  )

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        token,
        error,
        preferences,
        login,
        logout,
        clearError,
        hasRole,
        updateProfile,
        changePassword,
        updatePreferences,
        testDoctorAccess,
        testAdminAccess,
        testPatientAccess,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
