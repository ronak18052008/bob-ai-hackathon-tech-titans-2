/**
 * MedBrief AI — Clinical Timeline View
 * Step 10: Clinical Timeline
 *
 * Deterministic chronological patient care journey:
 * - Pure code assembly from structured clinical data (Zero LLM calls for sorting)
 * - Strict date precision badges (EXACT, MONTH_YEAR, YEAR_ONLY, APPROXIMATE)
 * - Distinct "Date Not Documented" drawer
 * - Categorical filtering, date range filter, search, and ascending/descending toggling
 * - Grounded source citations with page numbers and expandable verbatim evidence snippets
 */

import React, { useState, useEffect, useCallback } from 'react'
import type { PatientRecord } from '../../types/patient'
import type {
  PatientTimelineResponse,
  TimelineEventItem,
  TimelineFilterParams,
} from '../../types/timeline'
import { fetchPatients } from '../../services/patientApi'
import { fetchPatientTimeline } from '../../services/timelineApi'
import { useDebounce } from '../../hooks/useDebounce'
import './TimelineView.css'

interface TimelineViewProps {
  targetPatient?: PatientRecord
  patients?: PatientRecord[]
  onPatientChange?: (patient: PatientRecord) => void
  onSelectPatient?: () => void
  onInspectDocument?: (documentId: string) => void
}

const CATEGORY_FILTERS = [
  { key: 'ALL', label: 'All Events', icon: '📋' },
  { key: 'consultation', label: 'Consultations', icon: '💬' },
  { key: 'diagnosis', label: 'Diagnoses', icon: '🩺' },
  { key: 'admission', label: 'Admissions', icon: '🏥' },
  { key: 'discharge', label: 'Discharges', icon: '🚪' },
  { key: 'procedure', label: 'Procedures', icon: '🔬' },
  { key: 'investigation', label: 'Investigations', icon: '🧪' },
  { key: 'result', label: 'Results', icon: '📊' },
  { key: 'medication_start', label: 'Med Starts', icon: '💊' },
  { key: 'medication_change', label: 'Med Changes', icon: '🔄' },
  { key: 'follow_up', label: 'Follow-ups', icon: '📅' },
  { key: 'referral', label: 'Referrals', icon: '↗️' },
  { key: 'other', label: 'Observations', icon: '📋' },
]

export const TimelineView: React.FC<TimelineViewProps> = ({
  targetPatient,
  patients: propPatients,
  onPatientChange,
  onInspectDocument,
}) => {
  const [patients, setPatients] = useState<PatientRecord[]>(propPatients || [])
  const [selectedPatientId, setSelectedPatientId] = useState<string>(targetPatient?.id || '')
  const [currentPatient, setCurrentPatient] = useState<PatientRecord | null>(targetPatient || null)

  // Timeline Data State
  const [timelineData, setTimelineData] = useState<PatientTimelineResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filter States
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const debouncedSearch = useDebounce(searchQuery, 300)
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')

  // UI Interactive States
  const [expandedSnippetId, setExpandedSnippetId] = useState<string | null>(null)
  const [showUndatedDrawer, setShowUndatedDrawer] = useState<boolean>(true)

  // 1. Initial Load of Patients
  useEffect(() => {
    if (propPatients && propPatients.length > 0) {
      setPatients(propPatients)
    } else if (!targetPatient) {
      fetchPatients({ pageSize: 50 })
        .then((res) => {
          if (res.items.length > 0) {
            setPatients(res.items)
            setSelectedPatientId((prev) => prev || res.items[0].id)
            setCurrentPatient((prev) => prev || res.items[0])
          }
        })
        .catch((err) => {
          console.error('Failed to load patient caseload:', err)
        })
    }
  }, [propPatients, targetPatient])

  useEffect(() => {
    if (targetPatient) {
      setSelectedPatientId(targetPatient.id)
      setCurrentPatient(targetPatient)
    }
  }, [targetPatient])

  // 2. Fetch Timeline Data
  const loadTimeline = useCallback(async () => {
    if (!selectedPatientId) return
    setLoading(true)
    setError(null)

    try {
      const params: TimelineFilterParams = {
        event_type: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        search: debouncedSearch.trim() || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort: sortOrder,
        page: 1,
        page_size: 100,
      }
      const data = await fetchPatientTimeline(selectedPatientId, params)
      setTimelineData(data)
    } catch (err: any) {
      console.error('Error fetching clinical timeline:', err)
      setError(err.message || 'Failed to load clinical timeline')
    } finally {
      setLoading(false)
    }
  }, [selectedPatientId, selectedCategory, debouncedSearch, dateFrom, dateTo, sortOrder])

  useEffect(() => {
    loadTimeline()
  }, [loadTimeline])

  // Handle switching patient via dropdown
  const handlePatientChange = (pId: string) => {
    setSelectedPatientId(pId)
    const match = patients.find((p) => p.id === pId)
    if (match) {
      setCurrentPatient(match)
      if (onPatientChange) {
        onPatientChange(match)
      }
    }
    setExpandedSnippetId(null)
  }

  const handleResetFilters = () => {
    setSelectedCategory('ALL')
    setSearchQuery('')
    setDateFrom('')
    setDateTo('')
    setSortOrder('desc')
  }

  const toggleSnippet = (eventId: string) => {
    setExpandedSnippetId((prev) => (prev === eventId ? null : eventId))
  }

  const summary = timelineData?.summary

  return (
    <div className="timeline-view-container" role="main" aria-label="Clinical Timeline View">
      {/* ── Patient Context Header ── */}
      <header className="timeline-header-card">
        <div className="timeline-header-top">
          <div className="timeline-patient-info">
            <div className="patient-avatar-circle" aria-hidden="true">
              {currentPatient?.gender === 'Female' ? '👩' : '👨'}
            </div>
            <div className="patient-details-col">
              <div className="timeline-patient-name-row">
                <h1 className="timeline-patient-name">
                  {currentPatient
                    ? `${currentPatient.first_name} ${currentPatient.last_name}`
                    : timelineData?.patient_name || 'Select Patient'}
                </h1>
                <span className="patient-mrn-badge">
                  MRN: {currentPatient?.mrn || timelineData?.patient_mrn || 'N/A'}
                </span>
              </div>
              <div className="timeline-patient-meta">
                <span>{currentPatient?.gender || 'Gender unrecorded'}</span>
                <span>•</span>
                <span>DOB: {currentPatient?.date_of_birth || 'Unrecorded'}</span>
                <span>•</span>
                <span>Status: {currentPatient?.status || 'ACTIVE'}</span>
              </div>
            </div>
          </div>

          <div className="timeline-header-actions">
            {patients.length > 1 && (
              <select
                className="patient-selector-dropdown"
                value={selectedPatientId}
                onChange={(e) => handlePatientChange(e.target.value)}
                aria-label="Switch patient"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name} ({p.mrn})
                  </option>
                ))}
              </select>
            )}

            <button
              type="button"
              className="btn-timeline-refresh"
              onClick={loadTimeline}
              disabled={loading}
              title="Refresh timeline from clinical data"
            >
              <span>🔄</span> Refresh
            </button>
          </div>
        </div>

        {/* ── Summary Stats Ribbon ── */}
        {summary && (
          <div className="timeline-stats-ribbon" aria-label="Timeline Statistics">
            <div className="timeline-stat-box">
              <span className="stat-label">Total Documented Events</span>
              <span className="stat-value">{summary.total_events}</span>
              <span className="stat-sub">{summary.dated_events_count} dated • {summary.undated_events_count} undated</span>
            </div>

            <div className="timeline-stat-box">
              <span className="stat-label">Earliest Event</span>
              <span className="stat-value">{summary.first_event_date || 'None'}</span>
              <span className="stat-sub">Chronological Anchor</span>
            </div>

            <div className="timeline-stat-box">
              <span className="stat-label">Latest Event</span>
              <span className="stat-value">{summary.last_event_date || 'None'}</span>
              <span className="stat-sub">Most Recent Care Note</span>
            </div>

            <div className="timeline-stat-box">
              <span className="stat-label">Timeline Engine</span>
              <span className="stat-value" style={{ color: '#0284c7' }}>Deterministic</span>
              <span className="stat-sub">0% LLM Sorting Drift</span>
            </div>
          </div>
        )}
      </header>

      {/* ── Filter Controls Bar ── */}
      <section className="timeline-controls-card" aria-label="Timeline Filter Controls">
        <div className="controls-row-top">
          <div className="search-box-wrap">
            <span className="search-icon" aria-hidden="true">🔍</span>
            <input
              type="text"
              className="timeline-search-input"
              placeholder="Search event title, clinical description, or diagnosis..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search timeline events"
            />
          </div>

          <div className="date-range-filter-wrap">
            <span>From:</span>
            <input
              type="date"
              className="date-input"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              aria-label="Filter events from date"
            />
            <span>To:</span>
            <input
              type="date"
              className="date-input"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              aria-label="Filter events to date"
            />
          </div>

          <button
            type="button"
            className="btn-sort-toggle"
            onClick={() => setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))}
            title="Toggle chronological sorting"
          >
            <span>{sortOrder === 'desc' ? '⏳ Newest First' : '⌛ Oldest First'}</span>
          </button>

          {(selectedCategory !== 'ALL' || searchQuery || dateFrom || dateTo || sortOrder !== 'desc') && (
            <button
              type="button"
              className="btn-reset-filters"
              onClick={handleResetFilters}
            >
              Reset Filters
            </button>
          )}
        </div>

        {/* Category Filter Pills */}
        <div className="category-filter-pills" role="tablist" aria-label="Event category filters">
          {CATEGORY_FILTERS.map((cat) => {
            const count =
              cat.key === 'ALL'
                ? summary?.total_events || 0
                : summary?.event_types?.[cat.key] || 0
            const isActive = selectedCategory === cat.key

            return (
              <button
                key={cat.key}
                type="button"
                className={`filter-pill ${isActive ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat.key)}
                role="tab"
                aria-selected={isActive}
              >
                <span>{cat.icon}</span>
                <span>{cat.label}</span>
                <span className="filter-pill-count">{count}</span>
              </button>
            )
          })}
        </div>
      </section>

      {/* ── Timeline Stream Area ── */}
      {loading ? (
        <div className="timeline-skeleton" aria-busy="true" aria-label="Loading clinical events">
          <div className="skeleton-item" />
          <div className="skeleton-item" />
          <div className="skeleton-item" />
        </div>
      ) : error ? (
        <div className="timeline-error-card" role="alert">
          <div className="error-icon">⚠️</div>
          <h2 className="error-title">Unable to Load Clinical Timeline</h2>
          <p className="error-desc">{error}</p>
          <button type="button" className="btn-retry" onClick={loadTimeline}>
            Retry Request
          </button>
        </div>
      ) : !timelineData || (timelineData.groups.length === 0 && timelineData.undated_events.length === 0) ? (
        <div className="timeline-empty-card" role="status">
          <div className="empty-icon">🗓️</div>
          <h2 className="empty-title">No Clinical Events Found</h2>
          <p className="empty-desc">
            {searchQuery || selectedCategory !== 'ALL' || dateFrom || dateTo
              ? 'No clinical events matched your selected filter criteria. Try clearing search filters.'
              : 'No clinical events have been extracted for this patient yet. Upload medical documents or run extraction to populate the timeline.'}
          </p>
          {(searchQuery || selectedCategory !== 'ALL' || dateFrom || dateTo) && (
            <button type="button" className="btn-retry" onClick={handleResetFilters}>
              Clear All Filters
            </button>
          )}
        </div>
      ) : (
        <div className="timeline-stream-container">
          {/* Period Groups (Dated Events) */}
          {timelineData.groups.map((group) => (
            <section key={group.period_key} className="timeline-period-group" aria-label={`Period ${group.period_label}`}>
              {/* Sticky Month / Year Anchor Header */}
              <div className="period-header-sticky">
                <div className="period-badge">
                  <span>📅 {group.period_label}</span>
                  <span className="period-event-count">{group.event_count} events</span>
                </div>
                <div className="period-line" aria-hidden="true" />
              </div>

              {/* Event Cards along the Spine */}
              <div className="period-events-list">
                {group.events.map((ev) => (
                  <TimelineEventCard
                    key={ev.id}
                    event={ev}
                    isExpanded={expandedSnippetId === ev.id}
                    onToggleSnippet={() => toggleSnippet(ev.id)}
                    onInspectDocument={onInspectDocument}
                  />
                ))}
              </div>
            </section>
          ))}

          {/* ── Date Not Documented Section ── */}
          {timelineData.undated_events.length > 0 && (
            <section className="undated-events-section" aria-label="Events with no documented date">
              <div
                className="undated-header-row"
                onClick={() => setShowUndatedDrawer(!showUndatedDrawer)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setShowUndatedDrawer(!showUndatedDrawer)}
                aria-expanded={showUndatedDrawer}
              >
                <div className="undated-title-group">
                  <span className="undated-icon" aria-hidden="true">⏱️</span>
                  <div>
                    <h2 className="undated-title">Date Not Documented</h2>
                    <p className="undated-subtext">
                      Documented clinical facts without an explicit date anchor in the records. Kept separate to prevent timeline hallucination.
                    </p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span className="undated-count-badge">
                    {timelineData.undated_events.length} {timelineData.undated_events.length === 1 ? 'event' : 'events'}
                  </span>
                  <span>{showUndatedDrawer ? '▲' : '▼'}</span>
                </div>
              </div>

              {showUndatedDrawer && (
                <div className="undated-cards-list">
                  {timelineData.undated_events.map((ev) => (
                    <TimelineEventCard
                      key={ev.id}
                      event={ev}
                      isExpanded={expandedSnippetId === ev.id}
                      onToggleSnippet={() => toggleSnippet(ev.id)}
                      onInspectDocument={onInspectDocument}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Sub-component for individual Event Card
 */
interface TimelineEventCardProps {
  event: TimelineEventItem
  isExpanded: boolean
  onToggleSnippet: () => void
  onInspectDocument?: (documentId: string) => void
}

const TimelineEventCard: React.FC<TimelineEventCardProps> = ({
  event,
  isExpanded,
  onToggleSnippet,
  onInspectDocument,
}) => {
  const precisionClass = (event.date_precision || 'exact').toLowerCase()

  return (
    <article className="timeline-event-row">
      {/* Node Icon on Chronological Spine */}
      <div className="event-spine-node" aria-hidden="true">
        {event.event_type_icon}
      </div>

      {/* Card Body */}
      <div className={`event-card ${event.is_conflict ? 'conflict-flagged' : ''}`}>
        <div className="event-top-bar">
          <div className="event-date-row">
            <span className="event-display-date">{event.display_date}</span>
            <span className={`precision-pill ${precisionClass}`}>
              {event.date_precision === 'MONTH_YEAR'
                ? 'Month Only'
                : event.date_precision === 'YEAR_ONLY'
                ? 'Year Only'
                : event.date_precision}
            </span>
          </div>

          <span className={`event-type-badge badge-${event.badge_class}`}>
            <span>{event.event_type_icon}</span>
            <span>{event.event_type_label}</span>
          </span>
        </div>

        <h3 className="event-title">{event.title}</h3>
        <p className="event-description">{event.description}</p>

        {/* Uncertainty / Conflict Flagging */}
        {event.is_conflict && (
          <div className="conflict-alert-box" role="alert">
            <span className="conflict-icon">⚠️</span>
            <div>
              <strong>Conflicting Documentation:</strong>{' '}
              {event.conflict_details || 'Discrepancy noted between source records.'}
            </div>
          </div>
        )}

        {/* Source Attribution Strip */}
        <div className="event-source-strip">
          <div className="source-meta-group">
            {event.source.document_name && (
              <span className="source-doc-pill">
                📄 {event.source.document_name}
              </span>
            )}
            {event.source.page_number !== null && event.source.page_number !== undefined && (
              <span className="source-page-pill">
                Page {event.source.page_number}
              </span>
            )}
            {event.source.source_section && (
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                § {event.source.source_section}
              </span>
            )}
            {event.source.document_id && onInspectDocument && (
              <button
                type="button"
                className="btn-snippet-toggle"
                onClick={() => onInspectDocument(event.source.document_id!)}
              >
                Inspect Doc ↗
              </button>
            )}
          </div>

          {event.source.source_snippet && (
            <button
              type="button"
              className="btn-snippet-toggle"
              onClick={onToggleSnippet}
              aria-expanded={isExpanded}
            >
              {isExpanded ? 'Hide Evidence Excerpt ▲' : 'View Evidence Excerpt ▼'}
            </button>
          )}
        </div>

        {/* Expandable Verbatim Evidence Snippet */}
        {isExpanded && event.source.source_snippet && (
          <div className="verbatim-snippet-box">
            <span className="snippet-tag">Verbatim Ground-Truth Excerpt:</span>
            "{event.source.source_snippet}"
          </div>
        )}
      </div>
    </article>
  )
}
