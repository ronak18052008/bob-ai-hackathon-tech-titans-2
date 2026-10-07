/**
 * MedBrief AI — Recent Records Table
 * Step 5: Doctor Dashboard UI
 *
 * Displays clinical records with ingestion status and review actions.
 */

import React from 'react'
import type { RecentRecordItem, RecordStatus } from '../../types/dashboard'
import './RecentRecords.css'

interface RecentRecordsProps {
  records: RecentRecordItem[]
  loading?: boolean
  onRecordAction: (record: RecentRecordItem) => void
}

const getStatusClassName = (status: RecordStatus): string => {
  switch (status) {
    case 'Ready for review':
      return 'ready-for-review'
    case 'Requires review':
      return 'requires-review'
    case 'Processing':
      return 'processing'
    case 'Completed':
      return 'completed'
    default:
      return ''
  }
}

export const RecentRecords: React.FC<RecentRecordsProps> = ({
  records,
  loading = false,
  onRecordAction,
}) => {
  if (loading) {
    return (
      <div className="records-card-container" aria-label="Loading recent records">
        <div className="records-header-row">
          <h3 className="records-title">Recent Medical Records</h3>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton-box" style={{ width: '100%', height: 42 }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="records-card-container" role="region" aria-label="Recent Medical Records">
      <div className="records-header-row">
        <div className="records-title-wrap">
          <span aria-hidden="true">📂</span>
          <h3 className="records-title">Recent Medical Records</h3>
        </div>
        <span className="section-count-badge">Multi-Document Intake</span>
      </div>

      <div className="table-responsive-wrapper">
        <table className="records-table">
          <thead>
            <tr>
              <th scope="col">Patient</th>
              <th scope="col">Record Document</th>
              <th scope="col">Type</th>
              <th scope="col">Last Updated</th>
              <th scope="col">Status</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {records.map((rec) => (
              <tr key={rec.id}>
                <td>
                  <div className="record-patient-cell">
                    <span className="record-patient-name">{rec.patientName}</span>
                    <span className="record-patient-mrn">{rec.patientMrn}</span>
                  </div>
                </td>
                <td>
                  <div className="record-title-cell">
                    <span className="record-filename">{rec.recordTitle}</span>
                    <span className="record-pages">{rec.pageCount} pages</span>
                  </div>
                </td>
                <td>{rec.documentType}</td>
                <td>{rec.lastUpdated}</td>
                <td>
                  <span className={`record-status-pill ${getStatusClassName(rec.status)}`}>
                    {rec.status}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className="record-table-btn"
                    onClick={() => onRecordAction(rec)}
                  >
                    Open Brief
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
