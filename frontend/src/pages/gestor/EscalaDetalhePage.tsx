/**
 * Detalhe da escala (gestor): calendário mensal mostrando quem cobre cada vaga.
 * Em escalas "geradas" o gestor reatribui/esvazia vagas livremente; em escalas
 * "publicadas" a edição é permitida apenas com justificativa (registrada na auditoria).
 */
import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Schedule, Assignment, User } from '../../lib/types'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { getDay, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
const WEEKDAYS = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']

const statusLabel: Record<string, string> = {
  draft: 'Gerando…', simulated: 'Simulada', generated: 'Gerada', published: 'Publicada', archived: 'Arquivada',
}
const statusColor: Record<string, 'gray' | 'blue' | 'green' | 'yellow'> = {
  draft: 'gray', simulated: 'blue', generated: 'yellow', published: 'green', archived: 'gray',
}

// Primeiro nome + inicial do sobrenome, para caber na célula
function shortName(name: string | null): string {
  if (!name) return '—'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0]
  return `${parts[0]} ${parts[parts.length - 1][0]}.`
}

interface EditorProps {
  scheduleId: string
  assignment: Assignment
  peritos: User[]
  isPublished: boolean
  onClose: () => void
}

function AssignmentEditor({ scheduleId, assignment, peritos, isPublished, onClose }: EditorProps) {
  const qc = useQueryClient()
  const [userId, setUserId] = useState<string>(assignment.user_id ?? '')
  const [reason, setReason] = useState('')

  const save = useMutation({
    mutationFn: (uid: string | null) =>
      api.patch(`/schedules/${scheduleId}/assignments/${assignment.id}`, { user_id: uid, reason: reason || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule', scheduleId] })
      onClose()
    },
  })

  const dateLabel = format(new Date(assignment.date + 'T00:00:00'), "dd 'de' MMMM", { locale: ptBR })
  const needsReason = isPublished && !reason.trim()

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="font-bold text-lg">{assignment.schedule_type_name}</p>
            <p className="text-sm text-gray-500">{dateLabel}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        </div>

        {isPublished && (
          <p className="mb-3 text-xs bg-amber-50 text-amber-700 rounded-lg px-3 py-2">
            Esta escala já foi publicada. A alteração exige justificativa e fica registrada na auditoria.
          </p>
        )}

        <label className="text-sm font-medium text-gray-700">Perito designado</label>
        <select
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        >
          <option value="">— Buraco (sem perito) —</option>
          {peritos.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>

        {isPublished && (
          <div className="mt-3">
            <label className="text-sm font-medium text-gray-700">Justificativa <span className="text-red-500">*</span></label>
            <textarea
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Motivo da alteração (ex.: troca por atestado médico)"
            />
          </div>
        )}

        {save.isError && <p className="mt-2 text-xs text-red-600">{(save.error as any)?.response?.data?.detail ?? 'Erro ao salvar.'}</p>}

        <div className="mt-5 flex gap-2 justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" loading={save.isPending} disabled={needsReason} onClick={() => save.mutate(userId || null)}>Salvar</Button>
        </div>
      </div>
    </div>
  )
}

export function EscalaDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [editing, setEditing] = useState<Assignment | null>(null)

  const { data: schedule, isLoading } = useQuery<Schedule>({
    queryKey: ['schedule', id],
    queryFn: () => api.get(`/schedules/${id}`).then((r) => r.data),
    enabled: !!id,
  })

  const { data: allUsers = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: () => api.get('/users/').then((r) => r.data),
  })
  const peritos = useMemo(
    () => allUsers.filter((u) => !u.is_manager).sort((a, b) => a.name.localeCompare(b.name)),
    [allUsers],
  )

  const publish = useMutation({
    mutationFn: () => api.post(`/schedules/${id}/publish`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule', id] })
      qc.invalidateQueries({ queryKey: ['schedules'] })
    },
  })

  // Agrupa atribuições por dia (número) e por tipo
  const byDay = useMemo(() => {
    const m: Record<number, Assignment[]> = {}
    schedule?.assignments.forEach((a) => {
      const dayNum = Number(a.date.slice(8, 10))
      ;(m[dayNum] ??= []).push(a)
    })
    return m
  }, [schedule])

  if (isLoading || !schedule) {
    return <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
  }

  const firstDay = new Date(schedule.year, schedule.month - 1, 1)
  const startOffset = getDay(firstDay)
  const daysInMonth = new Date(schedule.year, schedule.month, 0).getDate()
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)

  const totalSlots = schedule.assignments.length
  const gaps = schedule.assignments.filter((a) => a.is_gap).length
  const peritosCount = new Set(schedule.assignments.filter((a) => a.user_id).map((a) => a.user_id)).size
  const isPublished = schedule.status === 'published'
  const editable = schedule.status === 'generated' || isPublished

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <button onClick={() => navigate('/gestor/escalas')} className="text-sm text-gray-500 hover:text-gray-700 mb-1 flex items-center gap-1">
            ← Escalas
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            Escala {MONTHS[schedule.month - 1]} {schedule.year} <span className="text-gray-400 text-lg">v{schedule.version}</span>
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <Badge label={statusLabel[schedule.status] ?? schedule.status} color={statusColor[schedule.status] ?? 'gray'} />
          {schedule.status === 'generated' && (
            <Button size="sm" loading={publish.isPending} onClick={() => publish.mutate()}>
              Publicar escala
            </Button>
          )}
        </div>
      </div>

      {/* Resumo */}
      <Card>
        <CardBody className="py-3">
          <div className="flex flex-wrap gap-6 text-sm">
            <span><span className="font-semibold text-gray-900">{totalSlots}</span> <span className="text-gray-500">turnos</span></span>
            <span><span className="font-semibold text-gray-900">{peritosCount}</span> <span className="text-gray-500">peritos escalados</span></span>
            <span>
              <span className={`font-semibold ${gaps > 0 ? 'text-red-600' : 'text-green-600'}`}>{gaps}</span>{' '}
              <span className="text-gray-500">buracos</span>
            </span>
            {gaps > 0 && <span className="text-red-600 italic">⚠ Há turnos sem perito disponível</span>}
            {editable && <span className="ml-auto text-gray-400 italic">{isPublished ? 'Clique numa vaga para alterar (exige justificativa)' : 'Clique numa vaga para reatribuir ou esvaziar'}</span>}
          </div>
        </CardBody>
      </Card>

      {/* Calendário */}
      <Card>
        <CardHeader>
          <div className="grid grid-cols-7 text-center text-xs font-semibold text-gray-500 uppercase">
            {WEEKDAYS.map((d) => <div key={d}>{d}</div>)}
          </div>
        </CardHeader>
        <CardBody className="pt-2">
          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: startOffset }).map((_, i) => <div key={`e-${i}`} />)}
            {days.map((dayNum) => {
              const d = new Date(schedule.year, schedule.month - 1, dayNum)
              const isWeekend = [0, 6].includes(getDay(d))
              const items = (byDay[dayNum] ?? []).slice().sort((a, b) =>
                a.schedule_type_name.localeCompare(b.schedule_type_name))

              return (
                <div
                  key={dayNum}
                  className={`rounded-lg p-2 min-h-[110px] text-left ring-1 ring-gray-200 ${isWeekend ? 'bg-blue-50' : 'bg-white'}`}
                >
                  <div className={`text-sm font-bold mb-1 ${isWeekend ? 'text-blue-700' : 'text-gray-800'}`}>{dayNum}</div>
                  <div className="space-y-0.5">
                    {items.length === 0 && <span className="text-[10px] text-gray-300 italic">—</span>}
                    {items.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        disabled={!editable}
                        onClick={() => editable && setEditing(a)}
                        className={`w-full text-left text-[11px] leading-tight rounded px-1 py-0.5 ${a.is_gap ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'} ${editable ? 'hover:ring-1 hover:ring-primary-400 cursor-pointer' : 'cursor-default'}`}
                        title={`${a.schedule_type_name}: ${a.user_name ?? 'SEM PERITO'}`}
                      >
                        <span className="font-medium">{a.is_gap ? '⚠ ' : ''}{shortName(a.user_name)}</span>
                        <span className="block text-[9px] text-gray-400 truncate">{a.schedule_type_name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </CardBody>
      </Card>

      {editing && (
        <AssignmentEditor
          scheduleId={id!}
          assignment={editing}
          peritos={peritos}
          isPublished={isPublished}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}
