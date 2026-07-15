import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { logout } from '../../lib/auth'
import type { User } from '../../lib/types'

interface Props {
  user: User
}

type Link = { to: string; label: string }

// Itens de administração (só gestor)
const managerLinks: Link[] = [
  { to: '/gestor/usuarios', label: 'Usuários' },
  { to: '/gestor/perfis', label: 'Perfis & Regras' },
  { to: '/gestor/tipos-escala', label: 'Tipos de Escala' },
  { to: '/gestor/calendarios', label: 'Calendários' },
  { to: '/gestor/escalas', label: 'Escalas' },
  { to: '/gestor/aprovar-trocas', label: 'Aprovar Trocas' },
  { to: '/gestor/saldo', label: 'Saldo / Ranking' },
  { to: '/gestor/auditoria', label: 'Auditoria' },
]

// Área do perito — todo usuário (inclusive gestor, que também pode ser escalado)
const userLinks: Link[] = [
  { to: '/usuario/agenda', label: 'Minha Agenda' },
  { to: '/usuario/escala-geral', label: 'Escala Geral' },
  { to: '/usuario/trocas', label: 'Trocas' },
  { to: '/usuario/saldo', label: 'Meu Saldo' },
]

function NavItem({ to, label }: Link) {
  return (
    <NavLink
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
  )
}

export function Sidebar({ user }: Props) {
  return (
    <aside className="flex h-screen w-56 flex-col bg-gray-900 text-white">
      <div className="px-5 py-6 border-b border-gray-700">
        <p className="text-xs uppercase tracking-widest text-gray-400">Gestão de Escalas</p>
        <p className="mt-1 text-sm font-semibold truncate">{user.name}</p>
        <p className="text-xs text-gray-400">{user.is_manager ? 'Gestor' : 'Perito'}</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {/* Minha área (todos). Para o gestor, vem rotulada. */}
        {user.is_manager && (
          <p className="px-3 pt-1 pb-1 text-[10px] uppercase tracking-wider text-gray-500">Minha área</p>
        )}
        {userLinks.map((l) => <NavItem key={l.to} {...l} />)}

        {/* Administração (só gestor) */}
        {user.is_manager && (
          <>
            <p className="px-3 pt-4 pb-1 text-[10px] uppercase tracking-wider text-gray-500">Gestão</p>
            {managerLinks.map((l) => <NavItem key={l.to} {...l} />)}
          </>
        )}
      </nav>

      <div className="px-3 py-4 border-t border-gray-700 space-y-1">
        <NavLink
          to="/como-funciona"
          className="block px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          Como funciona?
        </NavLink>
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
