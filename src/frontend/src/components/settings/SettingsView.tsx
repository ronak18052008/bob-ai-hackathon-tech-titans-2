/**
 * MedBrief AI — System & Clinical Settings View
 *
 * Fully functional, production-grade settings management for clinicians:
 * - Profile Management (Full Name, Title, Medical License ID)
 * - Account & Security (Credentials, Password change with PBKDF2 hashing, Session)
 * - Appearance & Accessibility (Light/System theme, Reduced Motion, Table Density)
 * - Notification Rules (In-App alerts, Document processing, AI completion, Labs)
 * - Privacy & Data Governance (Zero-retention BAA notice, Local Cache clearance)
 * - Application Preferences (Default view, Summary format, Page size, Date format)
 * - About MedBrief AI (Version, System Architecture, Clinical Disclaimer)
 */

import React, { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Logo } from '../common/Logo'
import type { UserPreferences } from '../../types/auth'
import './SettingsView.css'

type SettingsTab =
  | 'profile'
  | 'security'
  | 'appearance'
  | 'notifications'
  | 'privacy'
  | 'preferences'
  | 'about'

interface SettingsViewProps {
  onNavigate?: (view: string) => void
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onNavigate }) => {
  const { user, preferences, updateProfile, changePassword, updatePreferences, logout } = useAuth()

  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')

  // Profile Form State
  const [profileName, setProfileName] = useState(user?.display_name || '')
  const [profileTitle, setProfileTitle] = useState(user?.role_title || '')
  const [profileLicense, setProfileLicense] = useState(user?.medical_license_id || '')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)

  // Password Form State
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  // Preferences Form State
  const [localPrefs, setLocalPrefs] = useState<UserPreferences>(preferences)
  const [prefsSaving, setPrefsSaving] = useState(false)
  const [prefsSuccess, setPrefsSuccess] = useState<string | null>(null)
  const [prefsError, setPrefsError] = useState<string | null>(null)

  // Cache Clear Modal State
  const [showCacheModal, setShowCacheModal] = useState(false)
  const [cacheClearSuccess, setCacheClearSuccess] = useState(false)

  // Track Unsaved Changes
  const isProfileDirty =
    profileName !== (user?.display_name || '') ||
    profileTitle !== (user?.role_title || '') ||
    profileLicense !== (user?.medical_license_id || '')

  const isPasswordDirty =
    currentPassword.length > 0 || newPassword.length > 0 || confirmPassword.length > 0

  const isPrefsDirty =
    JSON.stringify(localPrefs) !== JSON.stringify(preferences)

  // Sync state when user or preferences update
  useEffect(() => {
    if (user) {
      setProfileName(user.display_name || '')
      setProfileTitle(user.role_title || '')
      setProfileLicense(user.medical_license_id || '')
    }
  }, [user])

  useEffect(() => {
    setLocalPrefs(preferences)
  }, [preferences])

  // Handle Tab Switch with Unsaved Alert
  const handleTabSwitch = (tab: SettingsTab) => {
    if (activeTab === 'profile' && isProfileDirty) {
      if (!window.confirm('You have unsaved changes in your Profile. Discard changes and switch tabs?')) {
        return
      }
      setProfileName(user?.display_name || '')
      setProfileTitle(user?.role_title || '')
      setProfileLicense(user?.medical_license_id || '')
    } else if (activeTab === 'security' && isPasswordDirty) {
      if (!window.confirm('You have entered password fields. Discard and switch tabs?')) {
        return
      }
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } else if ((activeTab === 'appearance' || activeTab === 'notifications' || activeTab === 'preferences') && isPrefsDirty) {
      if (!window.confirm('You have unsaved preference adjustments. Discard changes and switch tabs?')) {
        return
      }
      setLocalPrefs(preferences)
    }

    setProfileSuccess(null)
    setProfileError(null)
    setPasswordSuccess(null)
    setPasswordError(null)
    setPrefsSuccess(null)
    setPrefsError(null)
    setActiveTab(tab)
  }

  // Profile Save
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileError(null)
    setProfileSuccess(null)

    if (!profileName.trim()) {
      setProfileError('Full Name / Display Name is required.')
      return
    }

    setProfileSaving(true)
    try {
      await updateProfile({
        display_name: profileName.trim(),
        role_title: profileTitle.trim() || undefined,
        medical_license_id: profileLicense.trim() || undefined,
      })
      setProfileSuccess('Physician profile updated and synchronized with clinical directory.')
      setTimeout(() => setProfileSuccess(null), 4000)
    } catch (err: unknown) {
      setProfileError(err instanceof Error ? err.message : 'Failed to update profile.')
    } finally {
      setProfileSaving(false)
    }
  }

  // Password Validation Checks
  const passwordCriteria = {
    length: newPassword.length >= 8,
    upper: /[A-Z]/.test(newPassword),
    lower: /[a-z]/.test(newPassword),
    digit: /[0-9]/.test(newPassword),
    special: /[!@#$%^&*()_+\-=[\]{}|;:,.<>?/~`]/.test(newPassword),
  }
  const isPasswordValid = Object.values(passwordCriteria).every(Boolean)

  // Password Change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(null)

    if (!currentPassword) {
      setPasswordError('Please enter your current password.')
      return
    }
    if (!isPasswordValid) {
      setPasswordError('New password does not meet the clinical complexity requirements.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.')
      return
    }

    setPasswordSaving(true)
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setPasswordSuccess('Password successfully updated and secured with salted PBKDF2 hash.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPasswordSuccess(null), 5000)
    } catch (err: unknown) {
      setPasswordError(err instanceof Error ? err.message : 'Failed to change password.')
    } finally {
      setPasswordSaving(false)
    }
  }

  // Preference Save
  const handleSavePreferences = async (updatedSubset?: Partial<UserPreferences>) => {
    setPrefsError(null)
    setPrefsSuccess(null)
    setPrefsSaving(true)

    const payload = updatedSubset ? { ...localPrefs, ...updatedSubset } : localPrefs
    try {
      const saved = await updatePreferences(payload)
      setLocalPrefs(saved)
      setPrefsSuccess('Clinical preferences saved and applied.')
      setTimeout(() => setPrefsSuccess(null), 3000)
    } catch (err: unknown) {
      setPrefsError(err instanceof Error ? err.message : 'Failed to save preferences.')
    } finally {
      setPrefsSaving(false)
    }
  }

  // Clear Local Cache Action
  const handleConfirmClearCache = () => {
    try {
      const savedToken = localStorage.getItem('medbrief_clinical_token')
      // Clear non-essential cached keys
      localStorage.clear()
      if (savedToken) {
        localStorage.setItem('medbrief_clinical_token', savedToken)
      }
      sessionStorage.clear()
      setShowCacheModal(false)
      setCacheClearSuccess(true)
      setTimeout(() => setCacheClearSuccess(false), 4000)
    } catch {
      setShowCacheModal(false)
    }
  }

  return (
    <div className="settings-container">
      {/* Settings Top Bar */}
      <div className="settings-header">
        <div className="settings-header-title-col">
          <div className="settings-breadcrumb">
            <button
              type="button"
              className="breadcrumb-link"
              onClick={() => onNavigate && onNavigate('dashboard')}
            >
              Dashboard
            </button>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">Settings & Configuration</span>
          </div>
          <h2 className="settings-title">System & Physician Settings</h2>
          <p className="settings-subtitle">
            Manage your clinical credentials, accessibility preferences, security controls, and application behaviors.
          </p>
        </div>

        <div className="settings-header-actions">
          {(isProfileDirty || isPasswordDirty || isPrefsDirty) && (
            <span className="unsaved-badge">
              <span className="unsaved-dot" /> Unsaved changes
            </span>
          )}
          <button
            type="button"
            className="settings-back-btn"
            onClick={() => onNavigate && onNavigate('dashboard')}
          >
            ← Return to Workspace
          </button>
        </div>
      </div>

      {/* Main Settings Layout (Sidebar + Content Card) */}
      <div className="settings-layout">
        {/* Navigation Tabs */}
        <aside className="settings-sidebar" aria-label="Settings navigation">
          <div className="settings-nav-group">
            <span className="settings-nav-heading">Physician Account</span>
            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('profile')}
            >
              <span className="nav-btn-icon">👨‍⚕️</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">Profile Credentials</span>
                <span className="nav-btn-sub">Name, title & license ID</span>
              </div>
              {isProfileDirty && <span className="nav-dirty-dot" />}
            </button>

            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'security' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('security')}
            >
              <span className="nav-btn-icon">🔒</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">Account & Security</span>
                <span className="nav-btn-sub">Password, sessions & RBAC</span>
              </div>
              {isPasswordDirty && <span className="nav-dirty-dot" />}
            </button>
          </div>

          <div className="settings-nav-group">
            <span className="settings-nav-heading">Experience & UI</span>
            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'appearance' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('appearance')}
            >
              <span className="nav-btn-icon">🎨</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">Appearance & Motion</span>
                <span className="nav-btn-sub">Theme, motion & density</span>
              </div>
            </button>

            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'notifications' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('notifications')}
            >
              <span className="nav-btn-icon">🔔</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">Notifications & Alerts</span>
                <span className="nav-btn-sub">In-app & clinical triage</span>
              </div>
            </button>

            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'preferences' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('preferences')}
            >
              <span className="nav-btn-icon">⚙️</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">Application Defaults</span>
                <span className="nav-btn-sub">Default view & summaries</span>
              </div>
            </button>
          </div>

          <div className="settings-nav-group">
            <span className="settings-nav-heading">Governance & System</span>
            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'privacy' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('privacy')}
            >
              <span className="nav-btn-icon">🛡️</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">Privacy & Data</span>
                <span className="nav-btn-sub">BAA, zero-retention & cache</span>
              </div>
            </button>

            <button
              type="button"
              className={`settings-nav-btn ${activeTab === 'about' ? 'active' : ''}`}
              onClick={() => handleTabSwitch('about')}
            >
              <span className="nav-btn-icon">ℹ️</span>
              <div className="nav-btn-text">
                <span className="nav-btn-label">About MedBrief AI</span>
                <span className="nav-btn-sub">Version, tech stack & safety</span>
              </div>
            </button>
          </div>

          <div className="settings-sidebar-footer">
            <button
              type="button"
              className="settings-signout-btn"
              onClick={() => logout()}
            >
              🚪 Sign Out Current Session
            </button>
          </div>
        </aside>

        {/* Tab Content Display */}
        <main className="settings-content" aria-live="polite">
          {/* TAB 1: PROFILE CREDENTIALS */}
          {activeTab === 'profile' && (
            <div className="settings-section-card">
              <div className="section-card-header">
                <div>
                  <h3 className="section-card-title">Physician Profile & Clinical Credentials</h3>
                  <p className="section-card-desc">
                    Your display name and clinical license ID are stamped on medical summaries, referral drafts, and the EHR audit trail.
                  </p>
                </div>
                <span className="status-badge-verified">Verified Clinician</span>
              </div>

              {profileSuccess && (
                <div className="settings-alert-banner success" role="alert">
                  <span className="alert-icon">✓</span>
                  <span>{profileSuccess}</span>
                </div>
              )}
              {profileError && (
                <div className="settings-alert-banner error" role="alert">
                  <span className="alert-icon">⚠️</span>
                  <span>{profileError}</span>
                </div>
              )}

              <form onSubmit={handleSaveProfile} className="settings-form">
                <div className="form-grid-2col">
                  <div className="form-group">
                    <label htmlFor="profile-fullname" className="form-label">
                      Full Name & Title <span className="required-star">*</span>
                    </label>
                    <input
                      id="profile-fullname"
                      type="text"
                      className="form-input"
                      value={profileName}
                      onChange={(e) => setProfileName(e.target.value)}
                      placeholder="e.g. Dr. Sarah Chen, MD"
                      required
                    />
                    <span className="form-hint">Displayed on clinical reports and communication headers.</span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="profile-role-title" className="form-label">
                      Professional Role / Designation
                    </label>
                    <input
                      id="profile-role-title"
                      type="text"
                      className="form-input"
                      value={profileTitle}
                      onChange={(e) => setProfileTitle(e.target.value)}
                      placeholder="e.g. Attending Physician, Internal Medicine"
                    />
                    <span className="form-hint">Specialty or department position.</span>
                  </div>
                </div>

                <div className="form-grid-2col">
                  <div className="form-group">
                    <label htmlFor="profile-license" className="form-label">
                      Medical License ID
                    </label>
                    <input
                      id="profile-license"
                      type="text"
                      className="form-input mono"
                      value={profileLicense}
                      onChange={(e) => setProfileLicense(e.target.value)}
                      placeholder="e.g. MED-LIC-98421"
                    />
                    <span className="form-hint">Included in physician sign-offs and legal EHR notes.</span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="profile-email-ro" className="form-label">
                      Email Address <span className="ro-tag">Managed by Hospital Directory</span>
                    </label>
                    <input
                      id="profile-email-ro"
                      type="email"
                      className="form-input readonly"
                      value={user?.email || ''}
                      readOnly
                      disabled
                    />
                    <span className="form-hint">Email is locked to directory SSO / hospital credentials.</span>
                  </div>
                </div>

                <div className="form-grid-2col">
                  <div className="form-group">
                    <label className="form-label">Assigned Roles</label>
                    <div className="roles-pill-container">
                      {(user?.roles || ['doctor']).map((role) => (
                        <span key={role} className="role-pill">
                          {role.toUpperCase()}
                        </span>
                      ))}
                    </div>
                    <span className="form-hint">Configured via database Role-Based Access Control (RBAC).</span>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Internal Clinician UUID</label>
                    <input
                      type="text"
                      className="form-input readonly mono"
                      value={user?.id || '—'}
                      readOnly
                      disabled
                    />
                    <span className="form-hint">Immutable database primary identifier.</span>
                  </div>
                </div>

                <div className="form-actions-bar">
                  <button
                    type="submit"
                    className="settings-primary-btn"
                    disabled={profileSaving || !isProfileDirty}
                  >
                    {profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}
                  </button>
                  {isProfileDirty && (
                    <button
                      type="button"
                      className="settings-secondary-btn"
                      onClick={() => {
                        setProfileName(user?.display_name || '')
                        setProfileTitle(user?.role_title || '')
                        setProfileLicense(user?.medical_license_id || '')
                      }}
                    >
                      Reset
                    </button>
                  )}
                </div>
              </form>
            </div>
          )}

          {/* TAB 2: ACCOUNT & SECURITY */}
          {activeTab === 'security' && (
            <div className="settings-section-card">
              <div className="section-card-header">
                <div>
                  <h3 className="section-card-title">Account Security & Credentials</h3>
                  <p className="section-card-desc">
                    Manage session security, authentication tokens, and rotate your physician login password.
                  </p>
                </div>
                <span className="status-badge-secure">PBKDF2-HMAC-SHA256 Active</span>
              </div>

              {passwordSuccess && (
                <div className="settings-alert-banner success" role="alert">
                  <span className="alert-icon">✓</span>
                  <span>{passwordSuccess}</span>
                </div>
              )}
              {passwordError && (
                <div className="settings-alert-banner error" role="alert">
                  <span className="alert-icon">⚠️</span>
                  <span>{passwordError}</span>
                </div>
              )}

              {/* Password Change Form */}
              <div className="security-subcard">
                <h4 className="subcard-title">Change Password</h4>
                <p className="subcard-subtitle">
                  Passwords are securely salted and hashed using PBKDF2 with SHA-256 (310,000 rounds). Plaintext passwords are never stored or logged.
                </p>

                <form onSubmit={handleChangePassword} className="settings-form">
                  <div className="form-group">
                    <label htmlFor="sec-current-pw" className="form-label">
                      Current Password <span className="required-star">*</span>
                    </label>
                    <div className="password-input-wrap">
                      <input
                        id="sec-current-pw"
                        type={showCurrentPassword ? 'text' : 'password'}
                        className="form-input"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        placeholder="Enter current password"
                        required
                        autoComplete="current-password"
                      />
                      <button
                        type="button"
                        className="pw-toggle-btn"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
                      >
                        {showCurrentPassword ? '🙈' : '👁️'}
                      </button>
                    </div>
                  </div>

                  <div className="form-grid-2col">
                    <div className="form-group">
                      <label htmlFor="sec-new-pw" className="form-label">
                        New Password <span className="required-star">*</span>
                      </label>
                      <div className="password-input-wrap">
                        <input
                          id="sec-new-pw"
                          type={showNewPassword ? 'text' : 'password'}
                          className="form-input"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder="Enter new strong password"
                          required
                          autoComplete="new-password"
                        />
                        <button
                          type="button"
                          className="pw-toggle-btn"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                        >
                          {showNewPassword ? '🙈' : '👁️'}
                        </button>
                      </div>
                    </div>

                    <div className="form-group">
                      <label htmlFor="sec-confirm-pw" className="form-label">
                        Confirm New Password <span className="required-star">*</span>
                      </label>
                      <div className="password-input-wrap">
                        <input
                          id="sec-confirm-pw"
                          type={showConfirmPassword ? 'text' : 'password'}
                          className="form-input"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="Re-enter new password"
                          required
                          autoComplete="new-password"
                        />
                        <button
                          type="button"
                          className="pw-toggle-btn"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                        >
                          {showConfirmPassword ? '🙈' : '👁️'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Password Complexity Checklist */}
                  {newPassword.length > 0 && (
                    <div className="password-requirements-card">
                      <span className="req-title">Clinical Password Complexity Requirements:</span>
                      <ul className="req-list">
                        <li className={passwordCriteria.length ? 'met' : 'unmet'}>
                          {passwordCriteria.length ? '✓' : '○'} At least 8 characters
                        </li>
                        <li className={passwordCriteria.upper ? 'met' : 'unmet'}>
                          {passwordCriteria.upper ? '✓' : '○'} At least one uppercase letter (A-Z)
                        </li>
                        <li className={passwordCriteria.lower ? 'met' : 'unmet'}>
                          {passwordCriteria.lower ? '✓' : '○'} At least one lowercase letter (a-z)
                        </li>
                        <li className={passwordCriteria.digit ? 'met' : 'unmet'}>
                          {passwordCriteria.digit ? '✓' : '○'} At least one digit (0-9)
                        </li>
                        <li className={passwordCriteria.special ? 'met' : 'unmet'}>
                          {passwordCriteria.special ? '✓' : '○'} At least one special symbol (!@#$%^&*...)
                        </li>
                      </ul>
                    </div>
                  )}

                  <div className="form-actions-bar">
                    <button
                      type="submit"
                      className="settings-primary-btn"
                      disabled={passwordSaving || !currentPassword || !newPassword || !confirmPassword}
                    >
                      {passwordSaving ? 'Verifying & Updating...' : 'Update Password'}
                    </button>
                  </div>
                </form>
              </div>

              {/* Session Information */}
              <div className="security-subcard" style={{ marginTop: '24px' }}>
                <h4 className="subcard-title">Active Clinical Session</h4>
                <div className="session-grid">
                  <div className="session-info-item">
                    <span className="session-info-label">Authentication Type</span>
                    <span className="session-info-value">JWT Bearer (HMAC-SHA256)</span>
                  </div>
                  <div className="session-info-item">
                    <span className="session-info-label">Session Duration</span>
                    <span className="session-info-value">60-Minute Sliding Window</span>
                  </div>
                  <div className="session-info-item">
                    <span className="session-info-label">HIPAA Audit Trail</span>
                    <span className="session-info-value text-success">Active & Monitored</span>
                  </div>
                  <div className="session-info-item">
                    <span className="session-info-label">Account Status</span>
                    <span className="session-info-value text-success">Active Clinician</span>
                  </div>
                </div>

                <div className="session-signout-row">
                  <button
                    type="button"
                    className="danger-outline-btn"
                    onClick={() => logout()}
                  >
                    🚪 Terminate Active Session & Sign Out
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: APPEARANCE & ACCESSIBILITY */}
          {activeTab === 'appearance' && (
            <div className="settings-section-card">
              <div className="section-card-header">
                <div>
                  <h3 className="section-card-title">Appearance & Accessibility</h3>
                  <p className="section-card-desc">
                    Customize visual clarity, interface density, and animation behavior for optimal clinical reading comfort.
                  </p>
                </div>
              </div>

              {prefsSaving && (
                <div className="settings-alert-banner info" role="status">
                  <span className="alert-icon">⏳</span>
                  <span>Saving preferences...</span>
                </div>
              )}
              {prefsSuccess && (
                <div className="settings-alert-banner success" role="alert">
                  <span className="alert-icon">✓</span>
                  <span>{prefsSuccess}</span>
                </div>
              )}
              {prefsError && (
                <div className="settings-alert-banner error" role="alert">
                  <span className="alert-icon">⚠️</span>
                  <span>{prefsError}</span>
                </div>
              )}

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">Color Theme</span>
                  <span className="pref-desc">
                    Select your preferred interface theme. The primary medical theme is calibrated for maximum readability in clinic and hospital environments.
                  </span>
                </div>
                <div className="theme-toggle-group">
                  <button
                    type="button"
                    className={`theme-card-option ${localPrefs.theme === 'light' ? 'selected' : ''}`}
                    onClick={() => {
                      const updated = { ...localPrefs, theme: 'light' as const }
                      setLocalPrefs(updated)
                      handleSavePreferences({ theme: 'light' })
                    }}
                  >
                    <span className="theme-preview-box light-preview" />
                    <span className="theme-name">Clinical Light (Default)</span>
                    <span className="theme-sub">Recommended</span>
                  </button>
                  <button
                    type="button"
                    className={`theme-card-option ${localPrefs.theme === 'system' ? 'selected' : ''}`}
                    onClick={() => {
                      const updated = { ...localPrefs, theme: 'system' as const }
                      setLocalPrefs(updated)
                      handleSavePreferences({ theme: 'system' })
                    }}
                  >
                    <span className="theme-preview-box system-preview" />
                    <span className="theme-name">Match System</span>
                    <span className="theme-sub">Auto detect</span>
                  </button>
                </div>
              </div>

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">Reduced Motion</span>
                  <span className="pref-desc">
                    Suppresses non-essential transitions, CSS animations, and pulse indicators across the dashboard for accessibility and low visual distraction.
                  </span>
                </div>
                <label className="switch-toggle" aria-label="Toggle reduced motion">
                  <input
                    type="checkbox"
                    checked={localPrefs.reduced_motion}
                    onChange={(e) => {
                      const checked = e.target.checked
                      const updated = { ...localPrefs, reduced_motion: checked }
                      setLocalPrefs(updated)
                      handleSavePreferences({ reduced_motion: checked })
                    }}
                  />
                  <span className="slider-switch" />
                </label>
              </div>

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">Information Density</span>
                  <span className="pref-desc">
                    Comfortable provides spacious reading padding; Compact tightens patient tables and diagnostic lists for high-volume chart review.
                  </span>
                </div>
                <div className="density-button-group">
                  <button
                    type="button"
                    className={`density-btn ${localPrefs.density === 'comfortable' ? 'active' : ''}`}
                    onClick={() => {
                      const updated = { ...localPrefs, density: 'comfortable' as const }
                      setLocalPrefs(updated)
                      handleSavePreferences({ density: 'comfortable' })
                    }}
                  >
                    Comfortable (Standard)
                  </button>
                  <button
                    type="button"
                    className={`density-btn ${localPrefs.density === 'compact' ? 'active' : ''}`}
                    onClick={() => {
                      const updated = { ...localPrefs, density: 'compact' as const }
                      setLocalPrefs(updated)
                      handleSavePreferences({ density: 'compact' })
                    }}
                  >
                    Compact (High-Density)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: NOTIFICATIONS & ALERTS */}
          {activeTab === 'notifications' && (
            <div className="settings-section-card">
              <div className="section-card-header">
                <div>
                  <h3 className="section-card-title">Clinical Notifications & Alerts</h3>
                  <p className="section-card-desc">
                    Control which operational updates and clinical intelligence alerts appear during your review workflow.
                  </p>
                </div>
              </div>

              {prefsSuccess && (
                <div className="settings-alert-banner success" role="alert">
                  <span className="alert-icon">✓</span>
                  <span>{prefsSuccess}</span>
                </div>
              )}

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">In-App Notification Bell</span>
                  <span className="pref-desc">Display unread badge and alert dropdown in top dashboard header.</span>
                </div>
                <label className="switch-toggle" aria-label="Toggle in-app notification bell">
                  <input
                    type="checkbox"
                    checked={localPrefs.notify_in_app}
                    onChange={(e) => {
                      const updated = { ...localPrefs, notify_in_app: e.target.checked }
                      setLocalPrefs(updated)
                      handleSavePreferences({ notify_in_app: e.target.checked })
                    }}
                  />
                  <span className="slider-switch" />
                </label>
              </div>

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">Document Ingestion & OCR Processing</span>
                  <span className="pref-desc">Notify when multi-page PDF ingestion and page text extraction complete.</span>
                </div>
                <label className="switch-toggle" aria-label="Toggle document processing alerts">
                  <input
                    type="checkbox"
                    checked={localPrefs.notify_doc_processing}
                    onChange={(e) => {
                      const updated = { ...localPrefs, notify_doc_processing: e.target.checked }
                      setLocalPrefs(updated)
                      handleSavePreferences({ notify_doc_processing: e.target.checked })
                    }}
                  />
                  <span className="slider-switch" />
                </label>
              </div>

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">AI Clinical Summary Generation</span>
                  <span className="pref-desc">Alert when Gemini model completes synthesis and citation grounding.</span>
                </div>
                <label className="switch-toggle" aria-label="Toggle AI summary completion alerts">
                  <input
                    type="checkbox"
                    checked={localPrefs.notify_ai_completion}
                    onChange={(e) => {
                      const updated = { ...localPrefs, notify_ai_completion: e.target.checked }
                      setLocalPrefs(updated)
                      handleSavePreferences({ notify_ai_completion: e.target.checked })
                    }}
                  />
                  <span className="slider-switch" />
                </label>
              </div>

              <div className="pref-row">
                <div className="pref-meta">
                  <span className="pref-label">Abnormal Diagnostics & Follow-up Recommendations</span>
                  <span className="pref-desc">Flag high-priority abnormal lab results and overdue specialist follow-ups.</span>
                </div>
                <label className="switch-toggle" aria-label="Toggle follow-up recommendations alerts">
                  <input
                    type="checkbox"
                    checked={localPrefs.notify_follow_up_alerts}
                    onChange={(e) => {
                      const updated = { ...localPrefs, notify_follow_up_alerts: e.target.checked }
                      setLocalPrefs(updated)
                      handleSavePreferences({ notify_follow_up_alerts: e.target.checked })
                    }}
                  />
                  <span className="slider-switch" />
                </label>
              </div>

              <div className="pref-row disabled">
                <div className="pref-meta">
                  <div className="label-with-tag">
                    <span className="pref-label">Email Digest Notifications</span>
                    <span className="unavailable-pill">Unavailable / Unconfigured</span>
                  </div>
                  <span className="pref-desc">
                    Outbound SMTP server and hospital email gateway are not enabled in this local deployment. Clinical notifications are delivered safely in-app.
                  </span>
                </div>
                <label className="switch-toggle disabled" aria-label="Email alerts disabled">
                  <input type="checkbox" disabled checked={false} />
                  <span className="slider-switch" />
                </label>
              </div>
            </div>
          )}

          {/* TAB 5: PRIVACY & DATA GOVERNANCE */}
          {activeTab === 'privacy' && (
            <div className="settings-section-card">
              <div className="section-card-header">
                <div>
                  <h3 className="section-card-title">Privacy, Security & Data Governance</h3>
                  <p className="section-card-desc">
                    Review clinical privacy protections, zero-data-retention compliance, and local workstation storage.
                  </p>
                </div>
                <span className="status-badge-secure">HIPAA / BAA Enforced</span>
              </div>

              {cacheClearSuccess && (
                <div className="settings-alert-banner success" role="alert">
                  <span className="alert-icon">✓</span>
                  <span>Local browser cache cleared successfully. Clinical database records remain safely intact.</span>
                </div>
              )}

              <div className="privacy-grid">
                <div className="privacy-feature-card">
                  <div className="privacy-card-icon">🛡️</div>
                  <h4 className="privacy-card-title">Zero Data Retention (BAA)</h4>
                  <p className="privacy-card-text">
                    All document text sent to Google Gemini uses zero-data-retention enterprise API endpoints. Document contents are never used to train foundational AI models.
                  </p>
                </div>

                <div className="privacy-feature-card">
                  <div className="privacy-card-icon">🔐</div>
                  <h4 className="privacy-card-title">Role-Based Data Isolation</h4>
                  <p className="privacy-card-text">
                    Patient medical records and clinical notes are isolated by attending physician assignment and verified at the database layer on every API request.
                  </p>
                </div>

                <div className="privacy-feature-card">
                  <div className="privacy-card-icon">📑</div>
                  <h4 className="privacy-card-title">Cryptographic SHA-256 Storage</h4>
                  <p className="privacy-card-text">
                    Every uploaded medical PDF is hashed with SHA-256 upon receipt. The digest is stored to detect any accidental corruption or document alteration.
                  </p>
                </div>

                <div className="privacy-feature-card">
                  <div className="privacy-card-icon">📜</div>
                  <h4 className="privacy-card-title">Immutable Audit Trail</h4>
                  <p className="privacy-card-text">
                    All document extractions, clinical brief requests, and password rotations trigger structured audit events with clinician ID and UTC timestamp.
                  </p>
                </div>
              </div>

              {/* Local Storage & Cache Clearance */}
              <div className="cache-management-box">
                <div className="cache-info">
                  <h4 className="cache-title">Local Workstation Storage & Cache</h4>
                  <p className="cache-desc">
                    MedBrief AI caches non-sensitive UI preferences and recent view tokens in browser storage to ensure fast page loads.
                    Clearing your cache removes local temporary tokens and forces a clean sync from the clinical server.
                  </p>
                  <p className="cache-safety-note">
                    <strong>Important:</strong> Clearing your workstation cache will NOT delete or affect any patient records, uploaded EHR documents, medications, or AI summaries stored on the server.
                  </p>
                </div>
                <button
                  type="button"
                  className="cache-clear-btn"
                  onClick={() => setShowCacheModal(true)}
                >
                  🧹 Clear Local Browser Cache...
                </button>
              </div>
            </div>
          )}

          {/* TAB 6: APPLICATION PREFERENCES */}
          {activeTab === 'preferences' && (
            <div className="settings-section-card">
              <div className="section-card-header">
                <div>
                  <h3 className="section-card-title">Clinical Application Preferences</h3>
                  <p className="section-card-desc">
                    Configure default landing views, default clinical summary styles, and table pagination settings.
                  </p>
                </div>
              </div>

              {prefsSuccess && (
                <div className="settings-alert-banner success" role="alert">
                  <span className="alert-icon">✓</span>
                  <span>{prefsSuccess}</span>
                </div>
              )}
              {prefsError && (
                <div className="settings-alert-banner error" role="alert">
                  <span className="alert-icon">⚠️</span>
                  <span>{prefsError}</span>
                </div>
              )}

              <div className="settings-form">
                <div className="form-grid-2col">
                  <div className="form-group">
                    <label htmlFor="pref-default-view" className="form-label">
                      Default Workspace View
                    </label>
                    <select
                      id="pref-default-view"
                      className="form-select"
                      value={localPrefs.default_dashboard_view}
                      onChange={(e) => {
                        const updated = { ...localPrefs, default_dashboard_view: e.target.value }
                        setLocalPrefs(updated)
                        handleSavePreferences({ default_dashboard_view: e.target.value })
                      }}
                    >
                      <option value="dashboard">Clinical Dashboard (Overview)</option>
                      <option value="patients">Patient Caseload Directory</option>
                      <option value="documents">Medical Document Repository</option>
                      <option value="timeline">Care Journey Timeline</option>
                      <option value="medications">Medication Intelligence</option>
                      <option value="investigations">Diagnostic Investigations</option>
                      <option value="summaries">AI Clinical Summaries</option>
                      <option value="referrals">Referral & Discharge Drafts</option>
                    </select>
                    <span className="form-hint">View shown immediately upon physician sign-in.</span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="pref-default-summary" className="form-label">
                      Default Summary Architecture
                    </label>
                    <select
                      id="pref-default-summary"
                      className="form-select"
                      value={localPrefs.default_summary_type}
                      onChange={(e) => {
                        const updated = { ...localPrefs, default_summary_type: e.target.value }
                        setLocalPrefs(updated)
                        handleSavePreferences({ default_summary_type: e.target.value })
                      }}
                    >
                      <option value="CLINICAL_BRIEF">Comprehensive Clinical Brief</option>
                      <option value="SOAP_NOTE">Standard SOAP Progress Note</option>
                      <option value="DISCHARGE_HANDOFF">Inpatient Discharge & Handoff Summary</option>
                      <option value="SPECIALIST_CONSULT">Subspecialist Consult Note</option>
                    </select>
                    <span className="form-hint">Preselected format when requesting new AI syntheses.</span>
                  </div>
                </div>

                <div className="form-grid-2col">
                  <div className="form-group">
                    <label htmlFor="pref-results-page" className="form-label">
                      Table Results Per Page
                    </label>
                    <select
                      id="pref-results-page"
                      className="form-select"
                      value={localPrefs.results_per_page}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10)
                        const updated = { ...localPrefs, results_per_page: val }
                        setLocalPrefs(updated)
                        handleSavePreferences({ results_per_page: val })
                      }}
                    >
                      <option value={10}>10 items per page (Recommended)</option>
                      <option value={25}>25 items per page</option>
                      <option value={50}>50 items per page</option>
                    </select>
                    <span className="form-hint">Applies to Patient Directory and Document lists.</span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="pref-date-format" className="form-label">
                      Clinical Date Format
                    </label>
                    <select
                      id="pref-date-format"
                      className="form-select"
                      value={localPrefs.date_format}
                      onChange={(e) => {
                        const updated = { ...localPrefs, date_format: e.target.value }
                        setLocalPrefs(updated)
                        handleSavePreferences({ date_format: e.target.value })
                      }}
                    >
                      <option value="YYYY-MM-DD">ISO Standard (YYYY-MM-DD)</option>
                      <option value="MM/DD/YYYY">US Clinical (MM/DD/YYYY)</option>
                      <option value="DD/MM/YYYY">International (DD/MM/YYYY)</option>
                    </select>
                    <span className="form-hint">Applied to timeline markers and medication tables.</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: ABOUT MEDBRIEF AI */}
          {activeTab === 'about' && (
            <div className="settings-section-card">
              <div className="about-hero">
                <Logo size={48} />
                <div className="about-hero-text">
                  <h3 className="about-title">MedBrief AI Enterprise</h3>
                  <p className="about-version">
                    Version 1.0.0 • Clinical Release Build • Production Stable
                  </p>
                </div>
              </div>

              <div className="about-details-grid">
                <div className="about-item">
                  <span className="about-item-label">System Architecture</span>
                  <span className="about-item-value">FastAPI + React 18 + TypeScript + Vite</span>
                </div>
                <div className="about-item">
                  <span className="about-item-label">Foundation AI Engine</span>
                  <span className="about-item-value">Google Gemini 2.5 Flash</span>
                </div>
                <div className="about-item">
                  <span className="about-item-label">Grounding Protocol</span>
                  <span className="about-item-value">100% Page & Document Citation Enforcement</span>
                </div>
                <div className="about-item">
                  <span className="about-item-label">Database Engine</span>
                  <span className="about-item-value">PostgreSQL / SQLite with SQLAlchemy ORM</span>
                </div>
                <div className="about-item">
                  <span className="about-item-label">Credential Cryptography</span>
                  <span className="about-item-value">PBKDF2-HMAC-SHA256 (310,000 Rounds)</span>
                </div>
                <div className="about-item">
                  <span className="about-item-label">Document Integrity</span>
                  <span className="about-item-value">SHA-256 Checksum Verification</span>
                </div>
              </div>

              <div className="clinical-disclaimer-box">
                <div className="disclaimer-icon">⚕️</div>
                <div className="disclaimer-body">
                  <h4 className="disclaimer-title">Clinical Decision Support Notice</h4>
                  <p className="disclaimer-text">
                    MedBrief AI is designed strictly as a clinical decision-support and documentation assistant. It assists healthcare professionals by synthesizing complex EHR records, organizing timelines, and drafting documentation with 100% verifiable source citations.
                  </p>
                  <p className="disclaimer-text">
                    MedBrief AI does not provide autonomous medical diagnoses or treatment directives. Licensed attending healthcare providers retain sole responsibility for reviewing AI-synthesized outputs and validating all medical information prior to clinical execution.
                  </p>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Confirmation Modal for Clearing Local Cache */}
      {showCacheModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="cache-modal-title">
          <div className="modal-dialog-card">
            <div className="modal-header">
              <span className="modal-icon-badge">🧹</span>
              <h3 id="cache-modal-title" className="modal-title">Clear Local Browser Cache?</h3>
            </div>
            <div className="modal-body">
              <p>
                This action will clear locally stored UI preferences, draft forms, and browser session cache on this computer.
              </p>
              <div className="modal-notice-banner">
                <strong>Patient Data Protection:</strong> All patient charts, clinical documents, extracted entities, and summaries are securely stored in the clinical database and will <strong>NOT</strong> be deleted.
              </div>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="settings-secondary-btn"
                onClick={() => setShowCacheModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="settings-danger-btn"
                onClick={handleConfirmClearCache}
              >
                Confirm Cache Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
