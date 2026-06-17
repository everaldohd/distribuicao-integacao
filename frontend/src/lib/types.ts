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
}

export interface Schedule {
  id: string
  calendar_id: string
  status: 'DRAFT' | 'GENERATED' | 'PUBLISHED'
  version: number
  created_at: string
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

export interface Preference {
  id: string
  date: string
  type: 'DESIRED' | 'AVOID'
  calendar_id: string
}
