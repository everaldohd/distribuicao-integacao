import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ssoLogin, getMe } from '../lib/auth'

/**
 * Ponto de entrada da integração com o NEO.
 * O NEO abre esta aplicação em /sso?token=<JWT assinado com o segredo compartilhado>.
 * Aqui trocamos esse token pela sessão da aplicação e redirecionamos.
 */
export function SSOPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [error, setError] = useState('')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setError('Token de acesso do NEO não informado.')
      return
    }
    ;(async () => {
      try {
        await ssoLogin(token)
        const user = await getMe()
        navigate(user.is_manager ? '/gestor/usuarios' : '/usuario/agenda', { replace: true })
      } catch (e: any) {
        setError(e?.response?.data?.detail ?? 'Não foi possível autenticar pela integração NEO.')
      }
    })()
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        {error ? (
          <div className="max-w-sm">
            <p className="text-red-600 font-medium">{error}</p>
            <a href="/login" className="mt-3 inline-block text-sm text-primary-600 hover:underline">Ir para o login</a>
          </div>
        ) : (
          <>
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            <p className="mt-3 text-sm text-gray-500">Entrando pela integração NEO…</p>
          </>
        )}
      </div>
    </div>
  )
}
