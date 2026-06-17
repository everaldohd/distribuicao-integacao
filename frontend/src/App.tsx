import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { UsuariosPage } from './pages/gestor/UsuariosPage'
import { TiposEscalaPage } from './pages/gestor/TiposEscalaPage'
import { CalendariosPage } from './pages/gestor/CalendariosPage'
import { EscalasPage } from './pages/gestor/EscalasPage'
import { SaldoGestorPage } from './pages/gestor/SaldoGestorPage'
import { MinhaEscalaPage } from './pages/usuario/MinhaEscalaPage'
import { PreferenciasPage } from './pages/usuario/PreferenciasPage'
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

      <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
        {/* Gestor */}
        <Route path="/gestor/usuarios" element={<UsuariosPage />} />
        <Route path="/gestor/tipos-escala" element={<TiposEscalaPage />} />
        <Route path="/gestor/calendarios" element={<CalendariosPage />} />
        <Route path="/gestor/escalas" element={<EscalasPage />} />
        <Route path="/gestor/saldo" element={<SaldoGestorPage />} />

        {/* Usuário */}
        <Route path="/usuario/escala" element={<MinhaEscalaPage />} />
        <Route path="/usuario/preferencias" element={<PreferenciasPage />} />
        <Route path="/usuario/trocas" element={<TrocasPage />} />
        <Route path="/usuario/saldo" element={<SaldoPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
