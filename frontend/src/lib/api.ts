import axios from 'axios'

// Lê um cookie pelo nome (o cookie de sessão é HttpOnly e NÃO aparece aqui;
// apenas o csrf_token, que é legível de propósito).
export function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

const CSRF_COOKIE = 'csrf_token'
const SAFE_METHODS = ['get', 'head', 'options']

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // envia/recebe o cookie de sessão HttpOnly
})

api.interceptors.request.use((config) => {
  // Double-submit: reflete o cookie CSRF no header para métodos que alteram estado.
  const method = (config.method || 'get').toLowerCase()
  if (!SAFE_METHODS.includes(method)) {
    const csrf = getCookie(CSRF_COOKIE)
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)
