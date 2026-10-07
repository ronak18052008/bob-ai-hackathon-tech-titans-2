/**
 * MedBrief AI — Authentication & Role-Based Access Control Types
 * Step 4: Authentication + RBAC
 */

export type UserRole = 'doctor' | 'admin' | string

export interface UserProfile {
  id: string
  email: string
  display_name: string
  role_title?: string | null
  medical_license_id?: string | null
  roles: string[]
  is_active: boolean
}

export type AuthStatus = 'loading' | 'unauthenticated' | 'authenticated'

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserProfile
}

export interface AccessCheckResult {
  status: string
  role?: string
  user_id?: string
  display_name?: string
  scope?: string
  detail?: string
  statusCode?: number
}

export interface PatientAccessCheckResult {
  status: string
  patient_id: string
  user_id: string
  access_granted: boolean
  detail?: string
  statusCode?: number
}

export interface UserPreferences {
  theme: 'light' | 'system'
  reduced_motion: boolean
  density: 'comfortable' | 'compact'
  notify_in_app: boolean
  notify_doc_processing: boolean
  notify_ai_completion: boolean
  notify_follow_up_alerts: boolean
  default_dashboard_view: string
  default_summary_type: string
  results_per_page: number
  date_format: string
}

