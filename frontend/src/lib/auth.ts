import { api } from './api'

export interface User {
  id: string
  name: string
  email: string
  is_manager: boolean
  profile_id: string | null
}

export async function login(email: string, password: string): Promise<string> {
  const { data } = await api.post<{ access_token: string }>('/auth/login', { email, password })
  localStorage.setItem('token', data.access_token)
  return data.access_token
}

// Login delegado pelo NEO: troca o token de handoff pela sessão desta aplicação
export async function ssoLogin(neoToken: string): Promise<string> {
  const { data } = await api.post<{ access_token: string }>('/auth/sso', { token: neoToken })
  localStorage.setItem('token', data.access_token)
  return data.access_token
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/users/me')
  return data
}

export function logout() {
  localStorage.removeItem('token')
  window.location.href = '/login'
}

export function getToken() {
  return localStorage.getItem('token')
}
