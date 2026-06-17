import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { BalanceEntry } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'

const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export function SaldoPage() {
  const { data: history = [], isLoading } = useQuery<BalanceEntry[]>({
    queryKey: ['balance-me'],
    queryFn: () => api.get('/balance/me').then((r) => r.data),
  })

  const current = history[history.length - 1]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Meu Saldo</h1>

      {current && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Card>
            <CardBody className="text-center">
              <p className="text-sm text-gray-500">Saldo acumulado</p>
              <p className={`text-4xl font-bold mt-1 ${current.cumulative_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {current.cumulative_balance > 0 ? '+' : ''}{current.cumulative_balance}
              </p>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="text-center">
              <p className="text-sm text-gray-500">Variação último mês</p>
              <p className={`text-4xl font-bold mt-1 ${current.delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {current.delta > 0 ? '+' : ''}{current.delta}
              </p>
            </CardBody>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader><p className="font-semibold">Histórico mensal</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : history.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhum histórico disponível ainda.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Período</th>
                <th className="px-6 py-3 text-right">Variação</th>
                <th className="px-6 py-3 text-right">Saldo acumulado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[...history].reverse().map((entry, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3">{entry.month > 0 ? `${MONTHS[entry.month - 1]} ${entry.year}` : 'Saldo inicial'}</td>
                  <td className={`px-6 py-3 text-right font-mono ${entry.delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.delta > 0 ? '+' : ''}{entry.delta}
                  </td>
                  <td className={`px-6 py-3 text-right font-mono font-semibold ${entry.cumulative_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.cumulative_balance > 0 ? '+' : ''}{entry.cumulative_balance}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
