import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { getMe, logout } from '../lib/auth'
import { getApiErrorMessage, PASSWORD_REQUIREMENTS } from '../lib/apiError'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { TestBanner } from '../components/ui/TestBanner'

/**
 * Troca de senha obrigatória no primeiro login.
 * O usuário só segue para o sistema depois de definir a própria senha.
 */
export function TrocarSenhaPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Validação local: feedback imediato, com as mesmas regras do servidor
  function localValidation(): string {
    if (newPassword.length < 8) return 'A nova senha deve ter no mínimo 8 caracteres.'
    if (/^[a-zA-Z0-9]*$/.test(newPassword)) return 'A nova senha deve conter ao menos um caractere especial (ex.: !#-.,*).'
    if (newPassword === currentPassword) return 'A nova senha deve ser diferente da atual.'
    if (newPassword !== confirm) return 'A confirmação não confere com a nova senha.'
    return ''
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const localError = localValidation()
    if (localError) {
      setError(localError)
      return
    }
    setError('')
    setLoading(true)
    try {
      await api.put('/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      // Atualiza o cache do usuário (must_change_password mudou) e segue
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      const user = await getMe()
      navigate(user.is_manager ? '/gestor/usuarios' : '/usuario/agenda', { replace: true })
    } catch (err) {
      setError(getApiErrorMessage(err, 'Não foi possível trocar a senha. Tente novamente.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <TestBanner />
      <div className="flex flex-1 items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <span className="text-3xl" aria-hidden="true">🔑</span>
            <h1 className="mt-2 text-2xl font-bold text-gray-900">Defina a sua senha</h1>
            <p className="mt-2 text-sm text-gray-500">
              Este é o seu primeiro acesso (ou sua senha foi redefinida). Por segurança,
              escolha uma senha só sua antes de continuar.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <Input
              id="current-password"
              label="Senha atual (a que você acabou de usar)"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            <div>
              <Input
                id="new-password"
                label="Nova senha"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
              <p className="mt-1 text-xs text-gray-500">{PASSWORD_REQUIREMENTS}</p>
            </div>
            <Input
              id="confirm-password"
              label="Confirme a nova senha"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
            {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
            <Button type="submit" className="w-full" loading={loading}>
              Salvar nova senha e entrar
            </Button>
          </form>

          <button
            onClick={logout}
            className="mt-4 w-full text-center text-sm text-gray-400 hover:text-gray-600"
          >
            Sair sem trocar
          </button>
        </div>
      </div>
    </div>
  )
}
