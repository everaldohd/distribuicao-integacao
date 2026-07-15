import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { SSOPage } from './pages/SSOPage'
import { ComoFuncionaPage } from './pages/ComoFuncionaPage'
import { TrocarSenhaPage } from './pages/TrocarSenhaPage'
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
import { EscalaPublicaPage } from './pages/EscalaPublicaPage'
import { AprovarTrocasPage } from './pages/gestor/AprovarTrocasPage'
import { SaldoPage } from './pages/usuario/SaldoPage'
import { isAuthenticated } from './lib/auth'

function RequireAuth({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/sso" element={<SSOPage />} />
      {/* Pública: explica o sistema para quem chega pela primeira vez */}
      <Route path="/como-funciona" element={<ComoFuncionaPage />} />
      {/* Troca de senha obrigatória (1º login) — autenticada, mas fora do layout */}
      <Route path="/trocar-senha" element={<RequireAuth><TrocarSenhaPage /></RequireAuth>} />

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
        <Route path="/gestor/aprovar-trocas" element={<AprovarTrocasPage />} />
        <Route path="/gestor/escala-geral" element={<EscalaPublicaPage />} />
        <Route path="/gestor/auditoria" element={<AuditoriaPage />} />

        {/* Usuário */}
        <Route path="/usuario/agenda" element={<MinhaAgendaPage />} />
        <Route path="/usuario/escala-geral" element={<EscalaPublicaPage />} />
        <Route path="/usuario/escala" element={<Navigate to="/usuario/agenda" replace />} />
        <Route path="/usuario/preferencias" element={<Navigate to="/usuario/agenda" replace />} />
        <Route path="/usuario/trocas" element={<TrocasPage />} />
        <Route path="/usuario/saldo" element={<SaldoPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
