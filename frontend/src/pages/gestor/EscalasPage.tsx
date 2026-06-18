import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import type { Schedule, OperationalCalendar } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

const statusColor: Record<string, 'gray' | 'blue' | 'green' | 'yellow'> = {
  draft: 'gray',
  simulated: 'blue',
  generated: 'yellow',
  published: 'green',
  archived: 'gray',
}

const statusLabel: Record<string, string> = {
  draft: 'Gerando…',
  simulated: 'Simulada',
  generated: 'Gerada',
  published: 'Publicada',
  archived: 'Arquivada',
}

export function EscalasPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { data: calendars = [] } = useQuery<OperationalCalendar[]>({
    queryKey: ['calendars'],
    queryFn: () => api.get('/calendars/').then((r) => r.data),
  })

  const { data: schedules = [], isLoading } = useQuery<Schedule[]>({
    queryKey: ['schedules'],
    queryFn: () => api.get('/schedules/').then((r) => r.data),
    // Enquanto houver escala em geração (draft), atualiza a cada 2s
    refetchInterval: (q) =>
      (q.state.data ?? []).some((s) => s.status === 'draft') ? 2000 : false,
  })

  const generate = useMutation({
    mutationFn: (calendarId: string) => api.post(`/schedules/generate/${calendarId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  const publish = useMutation({
    mutationFn: (scheduleId: string) => api.post(`/schedules/${scheduleId}/publish`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  const discard = useMutation({
    mutationFn: (scheduleId: string) => api.delete(`/schedules/${scheduleId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  const emPreparacao = schedules.filter((s) => s.status !== 'published' && s.status !== 'archived')
  const publicadas = schedules.filter((s) => s.status === 'published')

  function renderRow(s: Schedule) {
    return (
      <tr key={s.id} className="hover:bg-gray-50">
        <td className="px-6 py-3 font-medium">{MONTHS[s.month - 1]}/{s.year}</td>
        <td className="px-6 py-3 font-medium">v{s.version}</td>
        <td className="px-6 py-3">
          <Badge label={statusLabel[s.status] ?? s.status} color={statusColor[s.status] ?? 'gray'} />
        </td>
        <td className="px-6 py-3 text-gray-500">
          {format(new Date(s.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
        </td>
        <td className="px-6 py-3">
          <div className="flex items-center gap-2">
            {(s.status === 'generated' || s.status === 'published') && (
              <Button size="sm" variant="secondary" onClick={() => navigate(`/gestor/escalas/${s.id}`)}>
                {s.status === 'published' ? 'Ver / editar →' : 'Ver escala →'}
              </Button>
            )}
            {s.status === 'generated' && (
              <Button size="sm" loading={publish.isPending} onClick={() => publish.mutate(s.id)}>
                Publicar
              </Button>
            )}
            {s.status !== 'published' && (
              <Button
                size="sm"
                variant="danger"
                loading={discard.isPending && discard.variables === s.id}
                onClick={() => {
                  if (window.confirm(`Apagar a escala ${MONTHS[s.month - 1]}/${s.year} v${s.version}? Esta ação não pode ser desfeita.`))
                    discard.mutate(s.id)
                }}
              >
                Apagar
              </Button>
            )}
          </div>
        </td>
      </tr>
    )
  }

  const tableHead = (
    <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
      <tr>
        <th className="px-6 py-3 text-left">Período</th>
        <th className="px-6 py-3 text-left">Versão</th>
        <th className="px-6 py-3 text-left">Status</th>
        <th className="px-6 py-3 text-left">Criada em</th>
        <th className="px-6 py-3 text-left">Ações</th>
      </tr>
    </thead>
  )

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

      {/* Em preparação: rascunho / gerada (ainda não publicada) */}
      <Card>
        <CardHeader><p className="font-semibold">Em preparação</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : emPreparacao.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma escala aguardando publicação.</p></CardBody>
        ) : (
          <table className="w-full text-sm">{tableHead}<tbody className="divide-y divide-gray-100">{emPreparacao.map(renderRow)}</tbody></table>
        )}
      </Card>

      {/* Histórico: somente publicadas */}
      <Card>
        <CardHeader><p className="font-semibold">Escalas publicadas</p></CardHeader>
        {publicadas.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma escala publicada ainda.</p></CardBody>
        ) : (
          <table className="w-full text-sm">{tableHead}<tbody className="divide-y divide-gray-100">{publicadas.map(renderRow)}</tbody></table>
        )}
      </Card>
    </div>
  )
}
