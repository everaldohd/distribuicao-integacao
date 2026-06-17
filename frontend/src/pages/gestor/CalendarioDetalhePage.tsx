import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { OperationalCalendar, ScheduleType } from '../../lib/types'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { format, getDay } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
const WEEKDAYS = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']

interface DayEditorProps {
  day: OperationalCalendar['days'][0]
  types: ScheduleType[]
  calendarId: string
  onClose: () => void
}

function DayEditor({ day, types, calendarId, onClose }: DayEditorProps) {
  const qc = useQueryClient()
  const existing: Record<string, number> = {}
  day.coverages.forEach(c => { existing[c.schedule_type_id] = c.quantity })

  const [slots, setSlots] = useState<Record<string, number>>(
    Object.fromEntries(types.map(t => [t.id, existing[t.id] ?? 0]))
  )

  const save = useMutation({
    mutationFn: () => api.patch(`/calendars/${calendarId}/days/${day.id}`, {
      coverage_overrides: slots,
      coverage_reason: 'Configuração manual',
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['calendar', calendarId] })
      onClose()
    },
  })

  const date = new Date(day.date + 'T00:00:00')
  const isWeekend = [0, 6].includes(getDay(date))

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="font-bold text-lg">{format(date, "dd 'de' MMMM", { locale: ptBR })}</p>
            <p className="text-sm text-gray-500">{format(date, 'EEEE', { locale: ptBR })} · {isWeekend ? 'Fim de semana' : 'Dia útil'}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="space-y-3">
          {types.map(t => (
            <div key={t.id} className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <p className="text-sm font-medium">{t.name}</p>
                {t.requires_rest_day_after && <p className="text-xs text-yellow-600">Exige interstício</p>}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSlots(s => ({ ...s, [t.id]: Math.max(0, (s[t.id] ?? 0) - 1) }))}
                  className="w-7 h-7 rounded-full border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100"
                >−</button>
                <span className="w-6 text-center font-mono font-semibold">{slots[t.id] ?? 0}</span>
                <button
                  onClick={() => setSlots(s => ({ ...s, [t.id]: (s[t.id] ?? 0) + 1 }))}
                  className="w-7 h-7 rounded-full border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100"
                >+</button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-5 flex gap-2 justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" loading={save.isPending} onClick={() => save.mutate()}>Salvar</Button>
        </div>
        {save.isError && <p className="mt-2 text-xs text-red-600">Erro ao salvar.</p>}
      </div>
    </div>
  )
}

export function CalendarioDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [editingDay, setEditingDay] = useState<OperationalCalendar['days'][0] | null>(null)

  const { data: calendar, isLoading } = useQuery<OperationalCalendar>({
    queryKey: ['calendar', id],
    queryFn: () => api.get(`/calendars/${id}`).then(r => r.data),
    enabled: !!id,
  })

  const { data: types = [] } = useQuery<ScheduleType[]>({
    queryKey: ['schedule-types'],
    queryFn: () => api.get('/schedule-types/').then(r => r.data),
  })

  const applyDefault = useMutation({
    mutationFn: () => api.post(`/calendars/${id}/apply-default-template`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['calendar', id] }),
  })

  if (isLoading || !calendar) {
    return <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
  }

  // Montar grade: descobrir qual dia da semana começa o mês
  const firstDay = new Date(calendar.year, calendar.month - 1, 1)
  const startOffset = getDay(firstDay) // 0=Dom

  const totalCoverage = (day: OperationalCalendar['days'][0]) =>
    day.coverages.reduce((s, c) => s + c.quantity, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate('/gestor/calendarios')} className="text-sm text-gray-500 hover:text-gray-700 mb-1 flex items-center gap-1">
            ← Calendários
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            {MONTHS[calendar.month - 1]} {calendar.year}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            label={calendar.status === 'draft' ? 'Rascunho' : calendar.status === 'open' ? 'Aberto' : 'Bloqueado'}
            color={calendar.status === 'draft' ? 'gray' : calendar.status === 'open' ? 'green' : 'yellow'}
          />
          {calendar.status === 'draft' && (
            <Button size="sm" variant="secondary" loading={applyDefault.isPending} onClick={() => applyDefault.mutate()}>
              Preencher com padrão (1 de cada)
            </Button>
          )}
        </div>
      </div>

      {/* Legenda dos tipos */}
      <Card>
        <CardBody className="py-3">
          <div className="flex flex-wrap gap-3 text-xs text-gray-600">
            <span className="font-semibold text-gray-700">Tipos:</span>
            {types.map(t => (
              <span key={t.id} className="flex items-center gap-1">
                <span className="font-medium">{t.name}</span>
                {t.requires_rest_day_after && <span className="text-yellow-600">(interstício)</span>}
              </span>
            ))}
            <span className="ml-auto text-gray-400 italic">Clique em qualquer dia para editar a cobertura</span>
          </div>
        </CardBody>
      </Card>

      {/* Grade do calendário */}
      <Card>
        <CardHeader>
          <div className="grid grid-cols-7 text-center text-xs font-semibold text-gray-500 uppercase">
            {WEEKDAYS.map(d => <div key={d}>{d}</div>)}
          </div>
        </CardHeader>
        <CardBody className="pt-2">
          <div className="grid grid-cols-7 gap-1">
            {/* Células vazias para offset */}
            {Array.from({ length: startOffset }).map((_, i) => (
              <div key={`empty-${i}`} />
            ))}

            {/* Dias */}
            {calendar.days.map(day => {
              const d = new Date(day.date + 'T00:00:00')
              const isWeekend = [0, 6].includes(getDay(d))
              const total = totalCoverage(day)
              const hasCoverage = total > 0

              return (
                <button
                  key={day.id}
                  onClick={() => setEditingDay(day)}
                  className={`
                    rounded-lg p-2 text-left transition-all hover:ring-2 hover:ring-primary-400 min-h-[90px]
                    ${isWeekend ? 'bg-blue-50' : 'bg-gray-50'}
                    ${hasCoverage ? 'ring-1 ring-gray-200' : 'border border-dashed border-gray-300'}
                  `}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-sm font-bold ${isWeekend ? 'text-blue-700' : 'text-gray-800'}`}>
                      {format(d, 'd')}
                    </span>
                    {hasCoverage && (
                      <span className="text-xs text-gray-400 font-mono">{total}v</span>
                    )}
                  </div>
                  <div className="space-y-0.5">
                    {day.coverages.filter(c => c.quantity > 0).map(c => (
                      <div key={c.schedule_type_id} className="text-xs leading-tight text-gray-600 truncate">
                        <span className="font-semibold text-gray-800">{c.quantity}×</span> {c.schedule_type_name}
                      </div>
                    ))}
                    {!hasCoverage && (
                      <span className="text-xs text-gray-400 italic">sem cobertura</span>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </CardBody>
      </Card>

      {/* Editor de dia */}
      {editingDay && (
        <DayEditor
          day={editingDay}
          types={types}
          calendarId={id!}
          onClose={() => setEditingDay(null)}
        />
      )}
    </div>
  )
}
