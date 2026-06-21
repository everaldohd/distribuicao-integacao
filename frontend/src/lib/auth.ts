import { api, getCookie } from './api'

export interface User {
  id: string
  name: string
  email: string
  is_manager: boolean
  profile_id: string | null
}

// A sessão vive no cookie HttpOnly (não acessível a JS). O cookie csrf_token,
// legível, serve de indicador "estou logado" para o roteamento do front.
const CSRF_COOKIE = 'csrf_token'

export async function login(email: string, password: string): Promise<void> {
  await api.post('/auth/login', { email, password })
  // Cookies (sessão HttpOnly + csrf) são gravados pelo servidor na resposta.
}

// Login delegado pelo NEO: troca o token de handoff pela sessão desta aplicação
export async function ssoLogin(neoToken: string): Promise<void> {
  await api.post('/auth/sso', { token: neoToken })
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/users/me')
  return data
}

export async function logout() {
  try {
    await api.post('/auth/logout') // limpa os cookies no servidor
  } catch {
    // ignora falha de rede no logout — segue para a tela de login
  }
  window.location.href = '/login'
}

// Indicador leve de sessão (a autorização real é sempre do servidor).
export function isAuthenticated(): boolean {
  return getCookie(CSRF_COOKIE) !== null
}
