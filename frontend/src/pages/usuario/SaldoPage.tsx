import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { BalanceEntry } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'

const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

const round = (n: number) => Math.round(n)

function meaning(saldo: number): { titulo: string; texto: string; cor: string } {
  if (saldo > 0) return {
    titulo: 'Você está sendo compensado a seu favor',
    texto: 'Seu saldo é positivo: você foi mais sobrecarregado que a média (datas que pediu para evitar, mais turnos). Por isso tem prioridade para folgar e para receber as datas que deseja.',
    cor: 'text-emerald-600',
  }
  if (saldo < 0) return {
    titulo: 'Você foi mais poupado que a média',
    texto: 'Seu saldo é negativo: você trabalhou menos ou recebeu datas que desejava. Para equilibrar, você tende a ser mais escalado nos próximos meses.',
    cor: 'text-amber-600',
  }
  return { titulo: 'Você está em equilíbrio', texto: 'Seu saldo está zerado em relação à média da equipe.', cor: 'text-gray-600' }
}

// Resumo amigável do que aconteceu no mês (sem expor a matemática de normalização)
function resumoMes(e: BalanceEntry): string {
  const partes: string[] = []
  if ((e.events_count_avoided_assigned ?? 0) > 0) partes.push(`${e.events_count_avoided_assigned} turno(s) em data que você queria evitar`)
  if ((e.events_count_desired_fulfilled ?? 0) > 0) partes.push(`${e.events_count_desired_fulfilled} data(s) desejada(s) atendida(s)`)
  if ((e.events_count_no_schedule ?? 0) > 0) partes.push('mês sem escala')
  return partes.length ? partes.join(' · ') : 'turnos comuns'
}

export function SaldoPage() {
  const { data: history = [], isLoading } = useQuery<BalanceEntry[]>({
    queryKey: ['balance-me'],
    queryFn: () => api.get('/balance/me').then((r) => r.data),
  })

  const current = history[history.length - 1]
  const saldo = current ? round(current.cumulative_balance) : 0
  const m = meaning(saldo)
  const meses = history.filter((e) => e.month > 0)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Meu Saldo</h1>

      {!current ? (
        <Card><CardBody><p className="text-sm text-gray-500">Você ainda não tem saldo — ele começa a contar após a primeira escala publicada.</p></CardBody></Card>
      ) : (
        <>
          {/* Saldo atual + significado */}
          <Card>
            <CardBody className="text-center py-8">
              <p className="text-sm text-gray-500">Seu saldo de compensação</p>
              <p className={`text-5xl font-bold mt-1 ${m.cor}`}>{saldo > 0 ? '+' : ''}{saldo}</p>
              <p className={`mt-3 font-semibold ${m.cor}`}>{m.titulo}</p>
              <p className="mt-1 text-sm text-gray-500 max-w-xl mx-auto">{m.texto}</p>
            </CardBody>
          </Card>

          {/* Como funciona */}
          <Card>
            <CardBody className="py-4 text-sm text-gray-600 space-y-1">
              <p className="font-semibold text-gray-700">Como o saldo funciona</p>
              <p>• <span className="text-emerald-600 font-medium">Saldo positivo</span> = você foi prejudicado → será <strong>poupado</strong> (folgas e datas desejadas).</p>
              <p>• <span className="text-amber-600 font-medium">Saldo negativo</span> = você foi poupado → será <strong>mais escalado</strong>.</p>
              <p>• Todo mês o saldo é comparado com a média da equipe, sempre puxando todos para o equilíbrio (zero).</p>
            </CardBody>
          </Card>

          {/* Histórico por eventos */}
          <Card>
            <CardHeader><p className="font-semibold">Histórico mês a mês</p></CardHeader>
            {isLoading ? (
              <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
            ) : meses.length === 0 ? (
              <CardBody><p className="text-sm text-gray-500">Nenhuma escala publicada ainda.</p></CardBody>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="px-6 py-3 text-left">Mês</th>
                    <th className="px-6 py-3 text-left">O que aconteceu</th>
                    <th className="px-6 py-3 text-right">Saldo ao fim do mês</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {[...meses].reverse().map((e, i) => {
                    const s = round(e.cumulative_balance)
                    return (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-6 py-3 whitespace-nowrap">{MONTHS[e.month - 1]} {e.year}</td>
                        <td className="px-6 py-3 text-gray-600">{resumoMes(e)}</td>
                        <td className={`px-6 py-3 text-right font-mono font-semibold ${s > 0 ? 'text-emerald-600' : s < 0 ? 'text-amber-600' : 'text-gray-500'}`}>
                          {s > 0 ? '+' : ''}{s}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
