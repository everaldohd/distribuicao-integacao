import { describe, it, expect, beforeEach } from 'vitest'
import { isAuthenticated } from './auth'

function clearCookies() {
  document.cookie.split(';').forEach((c) => {
    const name = c.split('=')[0].trim()
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
  })
}

beforeEach(clearCookies)

describe('isAuthenticated', () => {
  it('false sem cookie csrf_token (sessão não iniciada)', () => {
    expect(isAuthenticated()).toBe(false)
  })

  it('true com cookie csrf_token presente', () => {
    document.cookie = 'csrf_token=qualquer-valor'
    expect(isAuthenticated()).toBe(true)
  })

  it('não é enganado por outros cookies', () => {
    document.cookie = 'outro_cookie=x'
    expect(isAuthenticated()).toBe(false)
  })
})
