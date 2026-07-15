import { describe, it, expect, beforeEach } from 'vitest'
import { api, getCookie } from './api'

// O interceptor de request é testado invocando o handler registrado no axios
// (mesma função que roda em produção), sem precisar de servidor HTTP.
type Handler = { fulfilled: (config: unknown) => unknown }
function runRequestInterceptor(config: Record<string, unknown>) {
  const handler = (api.interceptors.request as unknown as { handlers: Handler[] }).handlers[0]
  return handler.fulfilled(config) as Record<string, any>
}

function clearCookies() {
  document.cookie.split(';').forEach((c) => {
    const name = c.split('=')[0].trim()
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
  })
}

beforeEach(clearCookies)

describe('getCookie', () => {
  it('retorna null quando o cookie não existe', () => {
    expect(getCookie('csrf_token')).toBeNull()
  })

  it('retorna o valor do cookie quando existe', () => {
    document.cookie = 'csrf_token=abc123'
    expect(getCookie('csrf_token')).toBe('abc123')
  })

  it('decodifica valores URI-encoded', () => {
    document.cookie = 'csrf_token=' + encodeURIComponent('a+b/c=')
    expect(getCookie('csrf_token')).toBe('a+b/c=')
  })
})

describe('interceptor CSRF (double-submit)', () => {
  it('reflete o cookie csrf_token no header X-CSRF-Token em métodos mutantes', () => {
    document.cookie = 'csrf_token=tok-1'
    const config = runRequestInterceptor({ method: 'post', headers: {} })
    expect(config.headers['X-CSRF-Token']).toBe('tok-1')
  })

  it('não adiciona o header em métodos seguros (GET)', () => {
    document.cookie = 'csrf_token=tok-1'
    const config = runRequestInterceptor({ method: 'get', headers: {} })
    expect(config.headers['X-CSRF-Token']).toBeUndefined()
  })

  it('não adiciona o header quando não há cookie (sessão não iniciada)', () => {
    const config = runRequestInterceptor({ method: 'delete', headers: {} })
    expect(config.headers['X-CSRF-Token']).toBeUndefined()
  })
})

describe('interceptor de uploads (FormData)', () => {
  it('remove o Content-Type para o browser definir multipart com boundary', () => {
    const config = runRequestInterceptor({
      method: 'post',
      data: new FormData(),
      headers: { 'Content-Type': 'application/json' },
    })
    expect(config.headers['Content-Type']).toBeUndefined()
    expect(config.headers['content-type']).toBeUndefined()
  })

  it('mantém o Content-Type JSON quando o corpo não é FormData', () => {
    const config = runRequestInterceptor({
      method: 'post',
      data: { a: 1 },
      headers: { 'Content-Type': 'application/json' },
    })
    expect(config.headers['Content-Type']).toBe('application/json')
  })
})
