import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Schedule } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export function MinhaEscalaPage() {
  const { data: schedules = [], isLoading } = useQuery<Schedule[]>({
    queryKey: ['schedules-published'],
    queryFn: () => api.get('/schedules/?status=PUBLISHED').then((r) => r.data),
  })

  const published = schedules.filter((s) => s.status === 'PUBLISHED')
  const latest = published[0]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Minha Escala</h1>

      {isLoading ? (
        <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
      ) : !latest ? (
        <Card><CardBody><p className="text-sm text-gray-500">Nenhuma escala publicada no momento.</p></CardBody></Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <p className="font-semibold">Escala publicada — v{latest.version}</p>
              <Badge label="Publicada" color="green" />
            </div>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-6 py-3 text-left">Data</th>
                  <th className="px-6 py-3 text-left">Tipo</th>
                  <th className="px-6 py-3 text-left">Usuário</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {latest.assignments
                  .filter((a) => !a.is_gap)
                  .map((a) => (
                    <tr key={a.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-mono">
                        {format(new Date(a.date + 'T00:00:00'), 'dd/MM/yyyy (EEE)', { locale: ptBR })}
                      </td>
                      <td className="px-6 py-3">{a.schedule_type_name}</td>
                      <td className="px-6 py-3 font-medium">{a.user_name ?? '—'}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
