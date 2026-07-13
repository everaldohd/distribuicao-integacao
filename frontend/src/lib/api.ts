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
  // Uploads: quando o corpo é FormData, remove o Content-Type padrão
  // (application/json) para o browser definir multipart/form-data COM o boundary.
  // Sem isso, o backend recebe o corpo sem os campos e responde 422.
  if (typeof FormData !== 'undefined' && config.data instanceof FormData && config.headers) {
    const h = config.headers as any
    if (typeof h.delete === 'function') h.delete('Content-Type')
    else { delete h['Content-Type']; delete h['content-type'] }
  }

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
