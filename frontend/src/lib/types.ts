export interface User {
  id: string
  name: string
  email: string
  is_manager: boolean
  profile_id: string | null
}

export interface ScheduleType {
  id: string
  name: string
  requires_rest_day_after: boolean
}

export interface GroupLimit {
  group_name: string
  max_quantity: number
}

export interface Profile {
  id: string
  name: string
  description: string | null
  is_default: boolean
  is_custom: boolean
  is_system: boolean
  group_limits: GroupLimit[]
}

export interface GroupType {
  name: string
  weight: number
}

export interface ScheduleGroup {
  group_name: string
  types: GroupType[]
}

export interface UserLimits {
  profile_id: string | null
  profile_name: string
  is_custom: boolean
  limits: Record<string, number>
}

export interface EligibilityItem {
  schedule_type_id: string
  schedule_type_name: string
  is_eligible: boolean
}

export type UnavailabilityType = 'vacation' | 'bonus_leave' | 'license'

export interface Unavailability {
  id: string
  type: UnavailabilityType
  start_date: string
  end_date: string
  notes: string | null
}

export interface CalendarDay {
  id: string
  date: string
  category: string
  coverages: Coverage[]
}

export interface Coverage {
  id: string
  schedule_type_id: string
  schedule_type_name: string
  quantity: number
  slots: number  // alias de quantity para compatibilidade
}

export interface OperationalCalendar {
  id: string
  year: number
  month: number
  status: string
  days: CalendarDay[]
}

export interface Assignment {
  id: string
  user_id: string | null
  user_name: string | null
  date: string
  schedule_type_id: string
  schedule_type_name: string
  is_gap: boolean
  is_manual?: boolean
}

export type ScheduleStatus = 'draft' | 'simulated' | 'generated' | 'published' | 'archived'

export interface Schedule {
  id: string
  year: number
  month: number
  status: ScheduleStatus
  version: number
  created_at: string
  published_at: string | null
  assignments: Assignment[]
}

export interface Exchange {
  id: string
  requester_id: string
  requester_name: string
  target_user_id: string | null
  target_user_name: string | null
  assignment_id: string
  assignment_date: string
  assignment_type: string
  status: 'OPEN' | 'ACCEPTED' | 'REJECTED' | 'CANCELLED'
  created_at: string
}

export interface BalanceEntry {
  year: number
  month: number
  delta: number
  cumulative_balance: number
}

export interface LeaderboardEntry {
  user_id: string
  user_name: string
  cumulative_balance: number
}

export interface AuditEntry {
  id: string
  performed_by_id: string | null
  performed_by_name: string | null
  action: string
  entity_type: string
  entity_id: string | null
  previous_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  description: string | null
  created_at: string
}

export type PreferenceType = 'desired' | 'avoid'

export interface Preference {
  id: string
  year: number
  month: number
  date: string
  schedule_type_id: string | null
  type: PreferenceType
}

export interface Modality {
  schedule_type_id: string
  name: string
  group_name: string
}

export interface PreferenceOptions {
  factor: number
  modalities: Modality[]
  group_caps: Record<string, number>
  availability: Record<string, string[]>
  preferences: Preference[]
  calendar_open: boolean
}
