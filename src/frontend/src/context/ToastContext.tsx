import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import './Toast.css'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastMessage {
  id: string
  message: string
  type: ToastType
  durationMs?: number
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType, durationMs?: number) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    (message: string, type: ToastType = 'info', durationMs: number = 4000) => {
      const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      const newToast: ToastMessage = { id, message, type, durationMs }

      setToasts((prev) => [...prev, newToast])

      if (durationMs > 0) {
        setTimeout(() => {
          removeToast(id)
        }, durationMs)
      }
    },
    [removeToast]
  )

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div className="clinical-toast-container" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`clinical-toast ${toast.type}`}
            role="status"
          >
            <span className="toast-icon" aria-hidden="true">
              {toast.type === 'success' && '✓'}
              {toast.type === 'error' && '⚠️'}
              {toast.type === 'warning' && '⚠️'}
              {toast.type === 'info' && 'ℹ️'}
            </span>
            <div className="toast-content">{toast.message}</div>
            <button
              type="button"
              className="toast-close-btn"
              onClick={() => removeToast(toast.id)}
              aria-label="Dismiss alert"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
