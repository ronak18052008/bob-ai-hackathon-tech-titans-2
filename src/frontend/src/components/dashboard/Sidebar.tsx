/**
 * MedBrief AI — Left Sidebar Navigation
 * Step 5: Doctor Dashboard UI
 *
 * Prominently features the MedBrief AI logo in the top-left corner,
 * dashboard navigation, and coming-soon roadmap indicators.
 */

import React from 'react'
import { Logo } from '../common/Logo'
import './Sidebar.css'

interface NavItem {
  id: string
  label: string
  icon: string
  stepInfo: string
  description: string
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: '📊',
    stepInfo: 'Overview',
    description: 'Current active doctor dashboard.',
  },
  {
    id: 'patients',
    label: 'Patients',
    icon: '👥',
    stepInfo: 'Caseload',
    description: 'Caseload directory, MRN indexing, and demographic management.',
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: '📁',
    stepInfo: 'EHR Records',
    description: 'Multi-page clinical PDF ingestion, page extraction, and storage.',
  },
  {
    id: 'timeline',
    label: 'Timeline',
    icon: '⏳',
    stepInfo: 'Care Journey',
    description: 'Chronological timeline of admissions, events, and treatments.',
  },
  {
    id: 'medications',
    label: 'Medications',
    icon: '💊',
    stepInfo: 'Pharmacotherapy',
    description: 'Drug reconciliation, start/stop tracking, and dosage changes.',
  },
  {
    id: 'investigations',
    label: 'Investigations',
    icon: '🔬',
    stepInfo: 'Diagnostics',
    description: 'Diagnostic results, pending labs, and abnormal values tracker.',
  },
  {
    id: 'summaries',
    label: 'Summaries',
    icon: '📝',
    stepInfo: 'AI Briefs',
    description: 'Synthesized medical summaries with 100% grounded document citations.',
  },
  {
    id: 'referrals',
    label: 'Referrals / Discharge',
    icon: '📋',
    stepInfo: 'Correspondence',
    description: 'Automated Referral, Discharge & Handoff draft generation with clinician sign-off.',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: '⚙️',
    stepInfo: 'System & Audit',
    description: 'System preferences, audit logs, and security configuration.',
  },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  onSelectComingSoon: (title: string, step: string, description: string) => void
  onLogoClick: () => void
  activeNav?: string
  onNavigate?: (viewId: string) => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onSelectComingSoon,
  onLogoClick,
  activeNav = 'dashboard',
  onNavigate,
}) => {
  const handleItemClick = (item: NavItem) => {
    if (
      item.id === 'dashboard' ||
      item.id === 'patients' ||
      item.id === 'documents' ||
      item.id === 'timeline' ||
      item.id === 'medications' ||
      item.id === 'investigations' ||
      item.id === 'summaries' ||
      item.id === 'referrals' ||
      item.id === 'settings'
    ) {
      if (onNavigate) {
        onNavigate(item.id)
      } else if (item.id === 'dashboard') {
        onLogoClick()
      }
    } else {
      onSelectComingSoon(item.label, item.stepInfo, item.description)
    }
    // Close drawer on mobile
    if (window.innerWidth <= 768) {
      onClose()
    }
  }

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={`sidebar-backdrop ${isOpen ? 'open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`sidebar-container ${isOpen ? 'open' : ''}`}
        aria-label="Clinical Navigation Sidebar"
      >
        {/* Top-Left Prominent MedBrief AI Logo */}
        <div className="sidebar-header">
          <Logo
            size={36}
            onClick={() => {
              onLogoClick()
              if (window.innerWidth <= 768) onClose()
            }}
          />
        </div>

        {/* Navigation list */}
        <nav className="sidebar-nav">
          <div className="nav-section-label">Clinical Workspace</div>
          {NAV_ITEMS.map((item) => {
            const isActive = activeNav === item.id
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => handleItemClick(item)}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="nav-item-left">
                  <span className="nav-item-icon" aria-hidden="true">
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="nav-pill-badge">{item.badge}</span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Clinical Assurance Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-footer-card">
            <span className="footer-card-tag">Clinical Decision Support</span>
            <p className="footer-card-text">
              Doctor-in-the-loop validation required for all clinical outputs.
            </p>
          </div>
        </div>
      </aside>
    </>
  )
}
