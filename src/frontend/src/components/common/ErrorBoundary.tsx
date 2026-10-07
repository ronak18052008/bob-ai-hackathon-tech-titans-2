/**
 * MedBrief AI — Clinical UI Error Boundary
 * Step 14: Security + Testing + Reliability
 *
 * Catches JavaScript rendering errors in child components, displays a
 * clean clinical recovery interface with reset and refresh actions,
 * and prevents full-application white-screen crashes.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'
import './ErrorBoundary.css'

interface ErrorBoundaryProps {
  children: ReactNode
  fallbackTitle?: string
  fallbackMessage?: string
  onReset?: () => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log safely to console in development without exposing PHI
    if (import.meta.env.DEV) {
      console.warn('[MedBrief UI] ErrorBoundary intercepted error:', error.message, errorInfo.componentStack)
    }
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, error: null })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  private handleReload = (): void => {
    window.location.reload()
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="clinical-error-boundary" role="alert">
          <div className="error-boundary-card">
            <div className="error-boundary-icon" aria-hidden="true">
              ⚠️
            </div>
            <h3 className="error-boundary-title">
              {this.props.fallbackTitle || 'Clinical Workspace Session Interruption'}
            </h3>
            <p className="error-boundary-desc">
              {this.props.fallbackMessage ||
                'An unexpected error occurred while rendering the clinical interface. Your session and patient data remain secure and uncompromised.'}
            </p>
            <div className="error-boundary-actions">
              <button
                type="button"
                className="error-btn primary"
                onClick={this.handleRetry}
              >
                ↻ Retry Workspace View
              </button>
              <button
                type="button"
                className="error-btn secondary"
                onClick={this.handleReload}
              >
                Reload Application
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
