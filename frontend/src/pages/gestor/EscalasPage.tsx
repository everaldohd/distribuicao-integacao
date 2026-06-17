import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Schedule, OperationalCalendar } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const statusColor: Record<string, 'gray' | 'blue' | 'green' | 'yellow'> = {
  DRAFT: 'gray',
  GENERATED: 'yellow',
  PUBLISHED: 'green',
}

const statusLabel: Record<string, string> = {
  DRAFT: 'Rascunho',
  GENERATED: 'Gerada',
  PUBLISHED: 'Publicada',
}

export function EscalasPage() {
  const qc = useQueryClient()

  const { data: calendars = [] } = useQuery<OperationalCalendar[]>({
    queryKey: ['calendars'],
    queryFn: () => api.get('/calendars/').then((r) => r.data),
  })

  const { data: schedules = [], isLoading } = useQuery<Schedule[]>({
    queryKey: ['schedules'],
    queryFn: () => api.get('/schedules/').then((r) => r.data),
  })

  const generate = useMutation({
    mutationFn: (calendarId: string) => api.post(`/schedules/generate/${calendarId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  const publish = useMutation({
    mutationFn: (scheduleId: string) => api.post(`/schedules/${scheduleId}/publish`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Escalas</h1>

      {calendars.length > 0 && (
        <Card>
          <CardHeader><p className="font-semibold">Gerar nova escala</p></CardHeader>
          <CardBody>
            <div className="flex flex-wrap gap-2">
              {calendars.map((cal) => (
                <Button
                  key={cal.id}
                  variant="secondary"
                  size="sm"
                  loading={generate.isPending}
                  onClick={() => generate.mutate(cal.id)}
                >
                  Gerar {cal.month}/{cal.year}
                </Button>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader><p className="font-semibold">Histórico de escalas</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : schedules.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma escala gerada ainda.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Versão</th>
                <th className="px-6 py-3 text-left">Status</th>
                <th className="px-6 py-3 text-left">Criada em</th>
                <th className="px-6 py-3 text-left">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {schedules.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium">v{s.version}</td>
                  <td className="px-6 py-3">
                    <Badge label={statusLabel[s.status] ?? s.status} color={statusColor[s.status] ?? 'gray'} />
                  </td>
                  <td className="px-6 py-3 text-gray-500">
                    {format(new Date(s.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                  </td>
                  <td className="px-6 py-3">
                    {s.status === 'GENERATED' && (
                      <Button size="sm" loading={publish.isPending} onClick={() => publish.mutate(s.id)}>
                        Publicar
                      </Button>
                    )}
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
