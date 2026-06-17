import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { logout } from '../../lib/auth'
import type { User } from '../../lib/types'

interface Props {
  user: User
}

const managerLinks = [
  { to: '/gestor/usuarios', label: 'Usuários' },
  { to: '/gestor/tipos-escala', label: 'Tipos de Escala' },
  { to: '/gestor/calendarios', label: 'Calendários' },
  { to: '/gestor/escalas', label: 'Escalas' },
  { to: '/gestor/saldo', label: 'Saldo / Ranking' },
]

const userLinks = [
  { to: '/usuario/escala', label: 'Minha Escala' },
  { to: '/usuario/preferencias', label: 'Preferências' },
  { to: '/usuario/trocas', label: 'Trocas' },
  { to: '/usuario/saldo', label: 'Meu Saldo' },
]

export function Sidebar({ user }: Props) {
  const links = user.is_manager ? managerLinks : userLinks

  return (
    <aside className="flex h-screen w-56 flex-col bg-gray-900 text-white">
      <div className="px-5 py-6 border-b border-gray-700">
        <p className="text-xs uppercase tracking-widest text-gray-400">Gestão de Escalas</p>
        <p className="mt-1 text-sm font-semibold truncate">{user.name}</p>
        <p className="text-xs text-gray-400">{user.is_manager ? 'Gestor' : 'Usuário'}</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx('flex items-center px-3 py-2 rounded-lg text-sm transition-colors', {
                'bg-primary-600 text-white': isActive,
                'text-gray-300 hover:bg-gray-800': !isActive,
              })
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-700">
        <button
          onClick={logout}
          className="w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          Sair
        </button>
      </div>
    </aside>
  )
}
