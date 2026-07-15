import { Navigate, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMe } from '../../lib/auth'
import { Sidebar } from './Sidebar'
import { TestBanner } from '../ui/TestBanner'

export function AppLayout() {
  const { data: user, isLoading } = useQuery({ queryKey: ['me'], queryFn: getMe })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    )
  }

  if (!user) return null

  // Troca de senha pendente → nada de navegar pelo sistema antes de trocá-la
  if (user.must_change_password) return <Navigate to="/trocar-senha" replace />

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar user={user} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TestBanner />
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
