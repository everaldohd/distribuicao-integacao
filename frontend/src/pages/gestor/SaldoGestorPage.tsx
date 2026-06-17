import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { LeaderboardEntry } from '../../lib/types'
import { Card, CardHeader } from '../../components/ui/Card'

export function SaldoGestorPage() {
  const { data: leaderboard = [], isLoading } = useQuery<LeaderboardEntry[]>({
    queryKey: ['leaderboard'],
    queryFn: () => api.get('/balance/leaderboard').then((r) => r.data),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Saldo / Ranking</h1>

      <Card>
        <CardHeader><p className="font-semibold">Ranking de compensação</p></CardHeader>
        {isLoading ? (
          <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
        ) : leaderboard.length === 0 ? (
          <div className="px-6 py-4 text-sm text-gray-500">Nenhum dado disponível ainda.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Pos.</th>
                <th className="px-6 py-3 text-left">Usuário</th>
                <th className="px-6 py-3 text-right">Saldo acumulado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {leaderboard.map((entry, i) => (
                <tr key={entry.user_id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-gray-400 font-mono">{i + 1}</td>
                  <td className="px-6 py-3 font-medium">{entry.user_name}</td>
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
