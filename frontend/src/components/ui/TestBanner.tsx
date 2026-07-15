import { Link } from 'react-router-dom'

/**
 * Aviso fixo de fase de testes.
 * Aparece em todas as telas: o sistema está em avaliação antes da adoção oficial.
 */
export function TestBanner() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900">
      <span aria-hidden="true">🧪</span>
      <span>
        <strong className="font-semibold">Versão de teste</strong> — o sistema está em fase de avaliação.
        Encontrou um problema? Avise o gestor.
      </span>
      <Link
        to="/como-funciona"
        className="font-semibold text-amber-900 underline decoration-amber-400 underline-offset-2 hover:text-amber-700"
      >
        Entenda como funciona →
      </Link>
    </div>
  )
}
