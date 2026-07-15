import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login, getMe } from '../lib/auth'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { TestBanner } from '../components/ui/TestBanner'

export function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      const user = await getMe()
      if (user.must_change_password) {
        navigate('/trocar-senha', { replace: true })
        return
      }
      navigate(user.is_manager ? '/gestor/usuarios' : '/usuario/agenda')
    } catch {
      setError('E-mail ou senha incorretos.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <TestBanner />
      <div className="flex flex-1 items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Gestão de Escalas</h1>
          <p className="mt-1 text-sm text-gray-500">Entre com suas credenciais</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <Input
            id="email"
            label="Usuário"
            type="text"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
          <Input
            id="password"
            label="Senha"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" loading={loading}>
            Entrar
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Primeira vez aqui?{' '}
          <Link to="/como-funciona" className="font-medium text-primary-600 hover:text-primary-700 hover:underline">
            Veja como o sistema funciona
          </Link>
        </p>
      </div>
      </div>
    </div>
  )
}
