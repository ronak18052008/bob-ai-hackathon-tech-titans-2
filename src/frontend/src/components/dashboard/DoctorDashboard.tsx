/**
 * MedBrief AI — Main Doctor Dashboard
 * Step 5: Doctor Dashboard UI
 *
 * Professional clinical workspace designed for physicians:
 * - Prominent MedBrief AI logo in top-left corner
 * - Left persistent/collapsible sidebar
 * - Top header with patient search, notifications, and user menu
 * - Hero welcome with clinical message
 * - 5 key clinical metrics
 * - Prominent "Requires Attention" section
 * - Recent patient activity feed
 * - Recent medical records table
 * - Quick actions
 * - Clinical intelligence preview cards
 * - Core product value messaging
 * - Loading, empty, and error state validation toggles
 */

import React, { useState, useMemo } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { MetricCards } from './MetricCards'
import { RequiresAttention } from './RequiresAttention'
import { RecentActivity } from './RecentActivity'
import { RecentRecords } from './RecentRecords'
import { QuickActions } from './QuickActions'
import { IntelligencePreview } from './IntelligencePreview'
import { DashboardPlaceholderModal } from './DashboardPlaceholderModal'
import { SystemSettingsModal } from './SystemSettingsModal'
import { fetchPatients } from '../../services/patientApi'
import { DEMO_METRICS, DEMO_ATTENTION_ITEMS, DEMO_RECENT_ACTIVITY, DEMO_RECENT_RECORDS, DEMO_QUICK_ACTIONS, DEMO_INTELLIGENCE_PREVIEWS } from './dashboardData'
import type { AttentionItem, QuickActionItem, IntelligencePreviewItem, RecentRecordItem } from '../../types/dashboard'
import type { PatientRecord } from '../../types/patient'
import { PatientList } from '../patients/PatientList'
import { PatientOverview } from '../patients/PatientOverview'
import { DocumentsView } from '../documents/DocumentsView'
import { TimelineView } from '../timeline/TimelineView'
import { MedicationsView } from '../medications/MedicationsView'
import { InvestigationsView } from '../investigations/InvestigationsView'
import { SummariesView } from '../summaries/SummariesView'
import { DraftsView } from '../drafts/DraftsView'
import { SettingsView } from '../settings/SettingsView'
import './DoctorDashboard.css'

interface DoctorDashboardProps {
  onReplayIntro: () => void
}

type UIState = 'normal' | 'loading' | 'empty' | 'error'
type DashboardView = 'dashboard' | 'patients' | 'patient-overview' | 'documents' | 'timeline' | 'medications' | 'investigations' | 'summaries' | 'referrals' | 'settings'

export const DoctorDashboard: React.FC<DoctorDashboardProps> = ({ onReplayIntro }) => {
  const { user } = useAuth()
  const [activeView, setActiveView] = useState<DashboardView>('dashboard')
  const [selectedPatient, setSelectedPatient] = useState<PatientRecord | null>(null)
  const [patients, setPatients] = useState<PatientRecord[]>([])
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [uiState, setUiState] = useState<UIState>('normal')
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)

  // Load patients on mount and provide refresh callback across views
  const loadPatientsList = React.useCallback(() => {
    fetchPatients({ pageSize: 50 })
      .then((res) => {
        if (res && res.items) {
          setPatients(res.items)
          if (!selectedPatient && res.items.length > 0) {
            setSelectedPatient(res.items[0])
          }
        }
      })
      .catch(() => {})
  }, [selectedPatient])

  React.useEffect(() => {
    loadPatientsList()
  }, [loadPatientsList])

  // Roadmap Placeholder Modal State (retained as safe fallback)
  const [modalState, setModalState] = useState<{
    isOpen: boolean
    title: string
    stepInfo: string
    description: string
    icon: string
  }>({
    isOpen: false,
    title: '',
    stepInfo: '',
    description: '',
    icon: '📌',
  })

  const openPlaceholderModal = (title: string, stepInfo: string, description: string, icon = '📌') => {
    setModalState({
      isOpen: true,
      title,
      stepInfo,
      description,
      icon,
    })
  }

  const closePlaceholderModal = () => {
    setModalState((prev) => ({ ...prev, isOpen: false }))
  }

  const findPatientForRef = (patientMrn: string, patientName: string): PatientRecord | null => {
    const byMrn = patients.find((p) => p.mrn.toLowerCase() === patientMrn.toLowerCase())
    if (byMrn) return byMrn
    const byName = patients.find((p) =>
      `${p.first_name} ${p.last_name}`.toLowerCase().includes(patientName.toLowerCase())
    )
    if (byName) return byName
    return patients[0] || null
  }

  // Filter items if a search query is active
  const filteredAttention = useMemo(() => {
    if (!searchQuery.trim()) return DEMO_ATTENTION_ITEMS
    const q = searchQuery.toLowerCase()
    return DEMO_ATTENTION_ITEMS.filter(
      (item) =>
        item.patientName.toLowerCase().includes(q) ||
        item.patientMrn.toLowerCase().includes(q) ||
        item.title.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
    )
  }, [searchQuery])

  const filteredRecords = useMemo(() => {
    if (!searchQuery.trim()) return DEMO_RECENT_RECORDS
    const q = searchQuery.toLowerCase()
    return DEMO_RECENT_RECORDS.filter(
      (rec) =>
        rec.patientName.toLowerCase().includes(q) ||
        rec.patientMrn.toLowerCase().includes(q) ||
        rec.recordTitle.toLowerCase().includes(q)
    )
  }, [searchQuery])

  const handleAttentionAction = (item: AttentionItem) => {
    const patient = findPatientForRef(item.patientMrn, item.patientName)
    if (patient) {
      setSelectedPatient(patient)
    }
    const cat = item.category.toLowerCase()
    if (cat.includes('investigation') || cat.includes('lab') || cat.includes('imaging') || cat.includes('panel')) {
      setActiveView('investigations')
    } else if (cat.includes('medication') || cat.includes('statin') || cat.includes('dose')) {
      setActiveView('medications')
    } else if (cat.includes('record') || cat.includes('note') || cat.includes('consult')) {
      setActiveView('documents')
    } else if (cat.includes('referral') || cat.includes('follow-up') || cat.includes('sign-off') || cat.includes('specialist')) {
      setActiveView('referrals')
    } else {
      setActiveView('summaries')
    }
  }

  const handleRecordAction = (record: RecentRecordItem) => {
    const patient = findPatientForRef(record.patientMrn, record.patientName)
    if (patient) {
      setSelectedPatient(patient)
    }
    setActiveView('documents')
  }

  const handleQuickActionClick = (action: QuickActionItem) => {
    if (action.id === 'qa-patients') {
      setActiveView('patients')
      return
    }
    if (action.id === 'qa-upload') {
      setActiveView('documents')
      return
    }
    if (action.id === 'qa-investigations') {
      setActiveView('investigations')
      return
    }
    if (action.id === 'qa-medications') {
      setActiveView('medications')
      return
    }
    if (action.id === 'qa-summaries') {
      setActiveView('summaries')
      return
    }
    setActiveView('patients')
  }

  const handleIntelligenceItemClick = (item: IntelligencePreviewItem) => {
    if (item.id === 'prev-timeline') {
      setActiveView('timeline')
      return
    }
    if (item.id === 'prev-meds') {
      setActiveView('medications')
      return
    }
    if (item.id === 'prev-inv') {
      setActiveView('investigations')
      return
    }
    if (item.id === 'prev-summary') {
      setActiveView('summaries')
      return
    }
    if (item.id === 'prev-evidence') {
      setActiveView('summaries')
      return
    }
    setActiveView('timeline')
  }

  const doctorGreetingName = user?.display_name || 'Dr. Sarah Chen, MD'

  return (
    <div className="dashboard-layout-container">
      {/* ── Left Sidebar (Persistent on Desktop, Drawer on Mobile) ── */}
      <Sidebar
        isOpen={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        onSelectComingSoon={(title, step, desc) => openPlaceholderModal(title, step, desc)}
        activeNav={activeView === 'patient-overview' ? 'patients' : activeView}
        onNavigate={(viewId) => {
          if (viewId === 'patients') {
            setActiveView('patients')
          } else if (viewId === 'documents') {
            setActiveView('documents')
          } else if (viewId === 'timeline') {
            setActiveView('timeline')
          } else if (viewId === 'medications') {
            setActiveView('medications')
          } else if (viewId === 'investigations') {
            setActiveView('investigations')
          } else if (viewId === 'summaries') {
            setActiveView('summaries')
          } else if (viewId === 'referrals') {
            setActiveView('referrals')
          } else if (viewId === 'settings') {
            setActiveView('settings')
          } else if (viewId === 'dashboard') {
            setActiveView('dashboard')
          }
        }}
        onLogoClick={() => {
          setActiveView('dashboard')
          setSearchQuery('')
          setUiState('normal')
        }}
      />

      {/* ── Main Application Area ── */}
      <div className="dashboard-main-area">
        {/* Top Header */}
        <Header
          onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          onReplayIntro={onReplayIntro}
          onSearchChange={setSearchQuery}
          searchQuery={searchQuery}
          patients={patients}
          onSelectPatient={(p) => {
            setSelectedPatient(p)
            setActiveView('patient-overview')
          }}
          onOpenSettings={() => setActiveView('settings')}
        />

        {/* Scrollable Clinical Workspace */}
        <main className="dashboard-scroll-content" role="main">
          {/* View: Patients Caseload Directory (Step 6) */}
          {activeView === 'patients' && (
            <PatientList
              onSelectPatient={(p) => {
                setSelectedPatient(p)
                setActiveView('patient-overview')
              }}
              onPatientMutation={loadPatientsList}
              initialSearch={searchQuery}
            />
          )}

          {/* View: Patient Overview Dossier (Step 6) */}
          {activeView === 'patient-overview' && selectedPatient && (
            <PatientOverview
              patient={selectedPatient}
              onBack={() => setActiveView('patients')}
              onPatientUpdated={(upd) => {
                setSelectedPatient(upd)
                loadPatientsList()
              }}
              onNavigateToTimeline={(p) => {
                setSelectedPatient(p)
                setActiveView('timeline')
              }}
              onNavigateToMedications={(p) => {
                setSelectedPatient(p)
                setActiveView('medications')
              }}
              onNavigateToInvestigations={(p) => {
                setSelectedPatient(p)
                setActiveView('investigations')
              }}
              onNavigateToSummaries={(p) => {
                setSelectedPatient(p)
                setActiveView('summaries')
              }}
            />
          )}

          {/* View: Medical Documents Directory & Ingestion Workspace (Step 7) */}
          {activeView === 'documents' && (
            <DocumentsView
              targetPatient={selectedPatient}
              patients={patients}
              onPatientChange={(p) => setSelectedPatient(p)}
              onClearPatientFilter={() => setSelectedPatient(null)}
              onSelectPatient={() => setActiveView('patients')}
            />
          )}

          {/* View: Clinical Timeline (Step 10) */}
          {activeView === 'timeline' && (
            <TimelineView
              targetPatient={selectedPatient || undefined}
              patients={patients}
              onPatientChange={(p) => setSelectedPatient(p)}
              onSelectPatient={() => setActiveView('patients')}
              onInspectDocument={(_docId) => setActiveView('documents')}
            />
          )}

          {/* View: Medication Intelligence (Step 11) */}
          {activeView === 'medications' && (
            <MedicationsView
              targetPatient={selectedPatient || undefined}
              patients={patients}
              onPatientChange={(p) => setSelectedPatient(p)}
              onSelectPatient={() => setActiveView('patients')}
              onInspectTimeline={() => setActiveView('timeline')}
            />
          )}

          {/* View: Investigation Intelligence & Diagnostics (Step 11) */}
          {activeView === 'investigations' && (
            <InvestigationsView
              targetPatient={selectedPatient || undefined}
              patients={patients}
              onPatientChange={(p) => setSelectedPatient(p)}
              onSelectPatient={() => setActiveView('patients')}
            />
          )}

          {/* View: AI Clinical Summaries & Evidence (Step 12) */}
          {activeView === 'summaries' && (
            <SummariesView
              targetPatient={selectedPatient || undefined}
              patients={patients}
              onPatientChange={(p) => setSelectedPatient(p)}
              onSelectPatient={() => setActiveView('patients')}
            />
          )}

          {/* View: Referral / Discharge / Handoff Drafts (Step 13) */}
          {activeView === 'referrals' && (
            <DraftsView
              targetPatient={selectedPatient || undefined}
              patients={patients}
              onPatientChange={(p) => setSelectedPatient(p)}
              onSelectPatient={() => setActiveView('patients')}
            />
          )}

          {/* View: Settings & Clinical Preferences */}
          {activeView === 'settings' && (
            <SettingsView
              onNavigate={(view) => setActiveView(view as DashboardView)}
            />
          )}

          {/* View: Default Doctor Dashboard (Step 5) */}
          {activeView === 'dashboard' && (
            <>
              {/* Active Search Filter Banner */}
              {searchQuery.trim() && (
                <div className="search-active-bar" role="status">
                  <span>
                    Filtering caseload results for: <strong>"{searchQuery}"</strong> (
                    {filteredAttention.length} attention items, {filteredRecords.length} records found)
                  </span>
                  <button
                    type="button"
                    className="clear-search-btn"
                    onClick={() => setSearchQuery('')}
                  >
                    Clear Search
                  </button>
                </div>
              )}

              {/* Hero Welcome Area (Section 7) */}
              <section className="dashboard-hero-banner" aria-label="Physician Welcome">
                <div className="hero-welcome-col">
                  <div className="hero-greeting-row">
                    <h2 className="hero-greeting-title">Good morning, {doctorGreetingName}</h2>
                    <span className="hero-verified-badge">Clinical Physician Session</span>
                  </div>
                  <p className="hero-subtitle-msg">
                    Review what changed, what remains unresolved, and what needs your attention across your assigned caseload.
                  </p>
                </div>

                {/* UX State Simulation Controls (Section 21 verification) */}
                <div className="hero-meta-col">
                  <div className="hero-state-switcher" role="group" aria-label="Dashboard State Switcher">
                    <button
                      type="button"
                      className={`state-switcher-btn ${uiState === 'normal' ? 'active' : ''}`}
                      onClick={() => setUiState('normal')}
                      title="Default populated dashboard"
                    >
                      Active State
                    </button>
                    <button
                      type="button"
                      className={`state-switcher-btn ${uiState === 'loading' ? 'active' : ''}`}
                      onClick={() => setUiState('loading')}
                      title="Test skeleton loading state"
                    >
                      Loading Skeleton
                    </button>
                    <button
                      type="button"
                      className={`state-switcher-btn ${uiState === 'empty' ? 'active' : ''}`}
                      onClick={() => setUiState('empty')}
                      title="Test all-caught-up empty state"
                    >
                      Empty State
                    </button>
                    <button
                      type="button"
                      className={`state-switcher-btn ${uiState === 'error' ? 'active' : ''}`}
                      onClick={() => setUiState('error')}
                      title="Test error fallback state"
                    >
                      Error State
                    </button>
                  </div>
                </div>
              </section>

              {/* Error State Handler */}
              {uiState === 'error' ? (
                <div className="dashboard-error-banner" role="alert">
                  <div className="error-banner-icon" aria-hidden="true">
                    ⚠️
                  </div>
                  <h3 className="error-banner-title">Unable to load dashboard data</h3>
                  <p className="error-banner-desc">
                    An unexpected connection issue occurred while synchronizing clinical records.
                    Your session remains secure. Please retry or contact system administration.
                  </p>
                  <button
                    type="button"
                    className="error-retry-btn"
                    onClick={() => setUiState('normal')}
                  >
                    Retry Dashboard Sync
                  </button>
                </div>
              ) : (
                <>
                  {/* 1. Key Metric Cards (Section 8) */}
                  <MetricCards
                    metrics={uiState === 'empty' ? [] : DEMO_METRICS}
                    loading={uiState === 'loading'}
                  />

                  {/* 2. Requires Attention Section (Section 9) */}
                  <RequiresAttention
                    items={uiState === 'empty' ? [] : filteredAttention}
                    loading={uiState === 'loading'}
                    onItemAction={handleAttentionAction}
                  />

                  {/* 3. Two-Column Grid: Recent Patient Activity (Section 10) & Recent Records (Section 11) */}
                  <div className="dashboard-split-grid">
                    <RecentActivity
                      activities={uiState === 'empty' ? [] : DEMO_RECENT_ACTIVITY}
                      loading={uiState === 'loading'}
                    />

                    <RecentRecords
                      records={uiState === 'empty' ? [] : filteredRecords}
                      loading={uiState === 'loading'}
                      onRecordAction={handleRecordAction}
                    />
                  </div>

                  {/* 4. Quick Actions Panel (Section 12) */}
                  <QuickActions
                    actions={DEMO_QUICK_ACTIONS}
                    onActionClick={handleQuickActionClick}
                  />

                  {/* 5. Clinical Intelligence Preview & Product Value Message (Sections 13 & 14) */}
                  <IntelligencePreview
                    items={DEMO_INTELLIGENCE_PREVIEWS}
                    onItemClick={handleIntelligenceItemClick}
                  />
                </>
              )}
            </>
          )}
        </main>
      </div>

      {/* ── System & Security Settings Modal ── */}
      <SystemSettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
      />

      {/* ── Roadmap Placeholder Modal (Fallback) ── */}
      {modalState.isOpen && (
        <DashboardPlaceholderModal
          isOpen={modalState.isOpen}
          title={modalState.title}
          stepInfo={modalState.stepInfo}
          description={modalState.description}
          icon={modalState.icon}
          onClose={closePlaceholderModal}
        />
      )}
    </div>
  )
}
