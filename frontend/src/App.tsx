import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { SSOPage } from './pages/SSOPage'
import { UsuariosPage } from './pages/gestor/UsuariosPage'
import { TiposEscalaPage } from './pages/gestor/TiposEscalaPage'
import { CalendariosPage } from './pages/gestor/CalendariosPage'
import { PerfisPage } from './pages/gestor/PerfisPage'
import { AuditoriaPage } from './pages/gestor/AuditoriaPage'
import { CalendarioDetalhePage } from './pages/gestor/CalendarioDetalhePage'
import { EscalasPage } from './pages/gestor/EscalasPage'
import { EscalaDetalhePage } from './pages/gestor/EscalaDetalhePage'
import { SaldoGestorPage } from './pages/gestor/SaldoGestorPage'
import { MinhaAgendaPage } from './pages/usuario/MinhaAgendaPage'
import { TrocasPage } from './pages/usuario/TrocasPage'
import { SaldoPage } from './pages/usuario/SaldoPage'
import { getToken } from './lib/auth'

function RequireAuth({ children }: { children: React.ReactNode }) {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/sso" element={<SSOPage />} />

      <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
        {/* Gestor */}
        <Route path="/gestor/usuarios" element={<UsuariosPage />} />
        <Route path="/gestor/perfis" element={<PerfisPage />} />
        <Route path="/gestor/tipos-escala" element={<TiposEscalaPage />} />
        <Route path="/gestor/calendarios" element={<CalendariosPage />} />
        <Route path="/gestor/calendarios/:id" element={<CalendarioDetalhePage />} />
        <Route path="/gestor/escalas" element={<EscalasPage />} />
        <Route path="/gestor/escalas/:id" element={<EscalaDetalhePage />} />
        <Route path="/gestor/saldo" element={<SaldoGestorPage />} />
        <Route path="/gestor/auditoria" element={<AuditoriaPage />} />

        {/* Usuário */}
        <Route path="/usuario/agenda" element={<MinhaAgendaPage />} />
        <Route path="/usuario/escala" element={<Navigate to="/usuario/agenda" replace />} />
        <Route path="/usuario/preferencias" element={<Navigate to="/usuario/agenda" replace />} />
        <Route path="/usuario/trocas" element={<TrocasPage />} />
        <Route path="/usuario/saldo" element={<SaldoPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
