/**
 * MedBrief AI — Doctor Dashboard Top Header
 * Step 5: Doctor Dashboard UI
 *
 * Provides:
 * - Page title & contextual subtitle
 * - Patient search bar placeholder
 * - Clinical notification affordance with unread popover
 * - Authenticated user initials avatar, title, and medical license ID
 * - Profile dropdown menu with Step 1 intro replay and Step 4 logout integration
 * - Mobile hamburger menu toggle
 */

import React, { useState, useRef, useEffect, useMemo } from 'react'
import { useAuth } from '../../context/AuthContext'
import { DEMO_NOTIFICATIONS } from './dashboardData'
import type { PatientRecord } from '../../types/patient'
import './Header.css'

interface HeaderProps {
  onToggleMobileSidebar: () => void
  onReplayIntro: () => void
  onSearchChange?: (query: string) => void
  searchQuery?: string
  patients?: PatientRecord[]
  onSelectPatient?: (patient: PatientRecord) => void
  onOpenSettings?: () => void
}

export const Header: React.FC<HeaderProps> = ({
  onToggleMobileSidebar,
  onReplayIntro,
  onSearchChange,
  searchQuery = '',
  patients = [],
  onSelectPatient,
  onOpenSettings,
}) => {
  const { user, logout } = useAuth()
  const [showNotifications, setShowNotifications] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)

  const notifRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const searchDropdownRef = useRef<HTMLDivElement>(null)

  // Filter patients by search query
  const matchingPatients = useMemo(() => {
    if (!searchQuery.trim() || !patients.length) return []
    const q = searchQuery.toLowerCase().trim()
    return patients
      .filter((p) =>
        `${p.first_name} ${p.last_name}`.toLowerCase().includes(q) ||
        p.mrn.toLowerCase().includes(q)
      )
      .slice(0, 6)
  }, [searchQuery, patients])

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false)
      }
      if (searchDropdownRef.current && !searchDropdownRef.current.contains(e.target as Node)) {
        setShowSearchDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = DEMO_NOTIFICATIONS.filter((n) => !n.isRead).length

  // Generate initials (e.g. Dr. Sarah Chen -> SC)
  const displayName = user?.display_name || 'Physician'
  const initials = displayName
    .replace(/^Dr\.\s*/i, '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('') || 'DR'

  return (
    <header className="doctor-header" aria-label="Dashboard Top Header">
      {/* Left: Mobile hamburger & Titles */}
      <div className="header-left-col">
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle navigation menu"
        >
          ☰
        </button>
        <div className="header-title-block">
          <h1 className="header-main-title">Doctor Dashboard</h1>
          <span className="header-subtitle">
            Clinical Decision-Support & Documentation Assistant
          </span>
        </div>
      </div>

      {/* Center: Patient Search Entry Point */}
      <div className="header-center-col" role="search" ref={searchDropdownRef}>
        <div className="search-input-wrapper">
          <span className="search-icon" aria-hidden="true">
            🔍
          </span>
          <input
            type="text"
            className="patient-search-input"
            placeholder="Search patients by name or MRN (e.g. Johnathan Doe)..."
            value={searchQuery}
            onFocus={() => {
              if (searchQuery.trim()) setShowSearchDropdown(true)
            }}
            onChange={(e) => {
              if (onSearchChange) onSearchChange(e.target.value)
              setShowSearchDropdown(true)
            }}
            aria-label="Search patients"
          />

          {/* Quick-Select Patient Dropdown */}
          {showSearchDropdown && searchQuery.trim() && (
            <div className="header-search-dropdown" role="listbox">
              <div className="search-dropdown-header">
                Matching Patients ({matchingPatients.length})
              </div>
              {matchingPatients.length === 0 ? (
                <div className="search-dropdown-empty">
                  No matching patients found in active caseload
                </div>
              ) : (
                matchingPatients.map((p) => (
                  <div
                    key={p.id}
                    className="search-dropdown-item"
                    role="option"
                    aria-selected={false}
                    onClick={() => {
                      if (onSelectPatient) onSelectPatient(p)
                      setShowSearchDropdown(false)
                      if (onSearchChange) onSearchChange('')
                    }}
                  >
                    <div className="search-dropdown-patient-info">
                      <span className="search-dropdown-name">
                        {p.last_name}, {p.first_name}
                      </span>
                      <span className="search-dropdown-status">
                        {p.gender || 'Patient'} • Status: {p.status}
                      </span>
                    </div>
                    <span className="search-dropdown-mrn">
                      MRN: {p.mrn}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Notifications & User Profile */}
      <div className="header-right-col">
        {/* Notification Bell Popover */}
        <div className="notification-wrapper" ref={notifRef}>
          <button
            type="button"
            className="icon-action-btn"
            onClick={() => setShowNotifications(!showNotifications)}
            aria-label={`Clinical alerts: ${unreadCount} unread`}
            aria-expanded={showNotifications}
          >
            🔔
            {unreadCount > 0 && <span className="unread-badge">{unreadCount}</span>}
          </button>

          {showNotifications && (
            <div className="notification-popover" role="region" aria-label="Clinical notifications">
              <div className="popover-header">
                <h4>Clinical Alerts</h4>
                <span>{unreadCount} Unread</span>
              </div>
              {DEMO_NOTIFICATIONS.map((n) => (
                <div key={n.id} className={`notif-item ${!n.isRead ? 'unread' : ''}`}>
                  <span className="notif-title">{n.title}</span>
                  <div className="notif-meta">
                    <span>{n.patientRef}</span>
                    <span>{n.timestamp}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div className="user-menu-wrapper" ref={userMenuRef}>
          <button
            type="button"
            className="user-profile-btn"
            onClick={() => setShowUserMenu(!showUserMenu)}
            aria-label="Doctor profile menu"
            aria-expanded={showUserMenu}
          >
            <div className="doctor-avatar-circle" aria-hidden="true">
              {initials}
            </div>
            <div className="user-summary-text">
              <span className="doctor-fullname">{displayName}</span>
              <span className="doctor-role-title">
                {user?.role_title || 'Attending Physician'}
              </span>
            </div>
            <span className="menu-chevron" aria-hidden="true">
              ▼
            </span>
          </button>

          {showUserMenu && (
            <div className="user-dropdown-menu" role="menu">
              <div className="dropdown-user-header">
                <div className="dropdown-name">{displayName}</div>
                <div className="dropdown-email">{user?.email}</div>
                {user?.medical_license_id && (
                  <div className="dropdown-license">
                    License: {user.medical_license_id}
                  </div>
                )}
              </div>

              <button
                type="button"
                className="dropdown-btn"
                role="menuitem"
                onClick={() => {
                  setShowUserMenu(false)
                  if (onOpenSettings) onOpenSettings()
                }}
              >
                ⚙️ Account & Settings
              </button>

              <button
                type="button"
                className="dropdown-btn"
                role="menuitem"
                onClick={() => {
                  setShowUserMenu(false)
                  onReplayIntro()
                }}
              >
                ▶ Replay Branded Intro
              </button>

              <button
                type="button"
                className="dropdown-btn logout"
                role="menuitem"
                onClick={() => logout()}
              >
                🚪 Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
