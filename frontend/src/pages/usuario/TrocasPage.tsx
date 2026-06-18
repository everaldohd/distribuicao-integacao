/**
 * Trocas de escala (perito): 1:1, mesmo grupo, com aprovação do gestor.
 * - Meus turnos do mês: colocar à disposição (mural) ou propor troca direta a um colega.
 * - Mural: ofertas abertas de colegas — propor um turno meu do mesmo grupo.
 * - Minhas trocas: acompanhar status; aceitar/recusar (direta) ou cancelar.
 */
import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { getMe } from '../../lib/auth'
import type { Schedule, Assignment, Exchange, ScheduleGroup } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

const STATUS: Record<string, { label: string; color: 'gray' | 'blue' | 'green' | 'red' | 'yellow' }> = {
  open: { label: 'No mural', color: 'blue' },
  awaiting_target: { label: 'Aguardando colega', color: 'yellow' },
  awaiting_manager: { label: 'Aguardando gestor', color: 'yellow' },
  approved: { label: 'Aprovada', color: 'green' },
  rejected: { label: 'Recusada', color: 'red' },
  cancelled: { label: 'Cancelada', color: 'gray' },
  expired: { label: 'Expirada', color: 'gray' },
}

const fmtDate = (d: string | null) => (d ? format(new Date(d + 'T00:00:00'), 'dd/MM (EEE)', { locale: ptBR }) : '—')

export function TrocasPage() {
  const qc = useQueryClient()
  const [err, setErr] = useState('')
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe })

  // Meses com escala publicada
  const { data: schedules = [] } = useQuery<Schedule[]>({
    queryKey: ['schedules'],
    queryFn: () => api.get('/schedules/').then((r) => r.data),
  })
  const published = useMemo(
    () => schedules.filter((s) => s.status === 'published').sort((a, b) => (b.year * 100 + b.month) - (a.year * 100 + a.month)),
    [schedules],
  )
  const [sel, setSel] = useState<string>('')
  const current = published.find((s) => `${s.year}-${s.month}` === sel) ?? published[0]

  // Escala completa do mês selecionado (todos os turnos)
  const { data: full } = useQuery<Schedule>({
    queryKey: ['published-schedule', current?.year, current?.month],
    queryFn: () => api.get('/schedules/published', { params: { year: current!.year, month: current!.month } }).then((r) => r.data),
    enabled: !!current,
  })

  // tipo → grupo
  const { data: groups = [] } = useQuery<ScheduleGroup[]>({
    queryKey: ['groups'], queryFn: () => api.get('/profiles/groups').then((r) => r.data),
  })
  const typeToGroup = useMemo(() => {
    const m: Record<string, string> = {}
    groups.forEach((g) => g.types.forEach((t) => { m[t.name] = g.group_name }))
    return m
  }, [groups])
  const groupOf = (a: Assignment) => typeToGroup[a.schedule_type_name] ?? a.schedule_type_name

  const { data: board = [] } = useQuery<Exchange[]>({ queryKey: ['ex-board'], queryFn: () => api.get('/exchanges/board').then((r) => r.data) })
  const { data: mine = [] } = useQuery<Exchange[]>({ queryKey: ['ex-mine'], queryFn: () => api.get('/exchanges/mine').then((r) => r.data) })

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['ex-board'] })
    qc.invalidateQueries({ queryKey: ['ex-mine'] })
  }
  const run = (p: Promise<unknown>) => { setErr(''); return p.then(refresh).catch((e: any) => setErr(e?.response?.data?.detail ?? 'Erro na operação.')) }

  const todayISO = new Date().toISOString().slice(0, 10)
  const myShifts = (full?.assignments ?? []).filter((a) => a.user_id === me?.id && !a.is_gap && a.date >= todayISO)
  const othersShifts = (full?.assignments ?? []).filter((a) => a.user_id && a.user_id !== me?.id && !a.is_gap && a.date >= todayISO)

  // Pickers
  const [directFor, setDirectFor] = useState<Assignment | null>(null)   // meu turno → escolher turno do colega
  const [proposeFor, setProposeFor] = useState<Exchange | null>(null)   // oferta do mural → escolher meu turno

  const offer = useMutation({ mutationFn: (aid: string) => api.post('/exchanges/offer', { requester_assignment_id: aid }) })
  const direct = useMutation({ mutationFn: (b: { requester_assignment_id: string; target_assignment_id: string }) => api.post('/exchanges/direct', b) })
  const propose = useMutation({ mutationFn: (b: { id: string; target_assignment_id: string }) => api.post(`/exchanges/${b.id}/propose`, { target_assignment_id: b.target_assignment_id }) })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Trocas de Escala</h1>
        {published.length > 0 && (
          <select className="rounded-lg border border-gray-300 px-3 py-2 text-sm" value={current ? `${current.year}-${current.month}` : ''} onChange={(e) => setSel(e.target.value)}>
            {published.map((s) => <option key={s.id} value={`${s.year}-${s.month}`}>{MONTHS[s.month - 1]}/{s.year}</option>)}
          </select>
        )}
      </div>

      {err && <p className="text-sm text-red-600">{err}</p>}

      {published.length === 0 ? (
        <Card><CardBody><p className="text-sm text-gray-500">Nenhuma escala publicada para trocar.</p></CardBody></Card>
      ) : (
        <>
          {/* Meus turnos */}
          <Card>
            <CardHeader><p className="font-semibold">Meus turnos em {current && `${MONTHS[current.month - 1]}/${current.year}`}</p></CardHeader>
            {myShifts.length === 0 ? (
              <CardBody><p className="text-sm text-gray-500">Você não tem turnos futuros neste mês.</p></CardBody>
            ) : (
              <table className="w-full text-sm">
                <tbody className="divide-y divide-gray-100">
                  {myShifts.map((a) => (
                    <tr key={a.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-mono">{fmtDate(a.date)}</td>
                      <td className="px-6 py-3">{a.schedule_type_name} <span className="text-xs text-gray-400">({groupOf(a)})</span></td>
                      <td className="px-6 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="secondary" onClick={() => run(offer.mutateAsync(a.id))}>À disposição</Button>
                          <Button size="sm" onClick={() => { setErr(''); setDirectFor(a) }}>Troca direta</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Mural */}
          <Card>
            <CardHeader><p className="font-semibold">Mural — turnos à disposição de colegas</p></CardHeader>
            {board.length === 0 ? (
              <CardBody><p className="text-sm text-gray-500">Nenhuma oferta no mural.</p></CardBody>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase"><tr>
                  <th className="px-6 py-3 text-left">Colega</th><th className="px-6 py-3 text-left">Turno</th><th className="px-6 py-3 text-right">Ação</th>
                </tr></thead>
                <tbody className="divide-y divide-gray-100">
                  {board.map((ex) => (
                    <tr key={ex.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium">{ex.requester_name}</td>
                      <td className="px-6 py-3">{fmtDate(ex.requester_date)} · {ex.requester_type} <span className="text-xs text-gray-400">({ex.group})</span></td>
                      <td className="px-6 py-3 text-right"><Button size="sm" onClick={() => { setErr(''); setProposeFor(ex) }}>Propor troca</Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Minhas trocas */}
          <Card>
            <CardHeader><p className="font-semibold">Minhas trocas</p></CardHeader>
            {mine.length === 0 ? (
              <CardBody><p className="text-sm text-gray-500">Nenhuma troca.</p></CardBody>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase"><tr>
                  <th className="px-6 py-3 text-left">Meu turno</th><th className="px-6 py-3 text-left">Colega / turno</th><th className="px-6 py-3 text-left">Status</th><th className="px-6 py-3 text-right">Ação</th>
                </tr></thead>
                <tbody className="divide-y divide-gray-100">
                  {mine.map((ex) => {
                    const iAmRequester = ex.requester_id === me?.id
                    const myDate = iAmRequester ? ex.requester_date : ex.target_date
                    const myType = iAmRequester ? ex.requester_type : ex.target_type
                    const otherName = iAmRequester ? ex.target_name : ex.requester_name
                    const otherDate = iAmRequester ? ex.target_date : ex.requester_date
                    const otherType = iAmRequester ? ex.target_type : ex.requester_type
                    const st = STATUS[ex.status] ?? { label: ex.status, color: 'gray' as const }
                    return (
                      <tr key={ex.id} className="hover:bg-gray-50">
                        <td className="px-6 py-3 font-mono">{fmtDate(myDate)}<span className="text-xs text-gray-400"> {myType}</span></td>
                        <td className="px-6 py-3">{otherName ? `${otherName} · ${fmtDate(otherDate)} ${otherType ?? ''}` : <span className="text-gray-400 italic">no mural</span>}</td>
                        <td className="px-6 py-3"><Badge label={st.label} color={st.color} /></td>
                        <td className="px-6 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            {!iAmRequester && ex.status === 'awaiting_target' && (
                              <>
                                <Button size="sm" onClick={() => run(api.post(`/exchanges/${ex.id}/accept`))}>Aceitar</Button>
                                <Button size="sm" variant="danger" onClick={() => run(api.post(`/exchanges/${ex.id}/reject`))}>Recusar</Button>
                              </>
                            )}
                            {iAmRequester && ['open', 'awaiting_target', 'awaiting_manager'].includes(ex.status) && (
                              <Button size="sm" variant="danger" onClick={() => run(api.post(`/exchanges/${ex.id}/cancel`))}>Cancelar</Button>
                            )}
                          </div>
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

      {/* Picker: troca direta — escolher turno do colega (mesmo grupo) */}
      {directFor && (
        <Picker
          title={`Trocar meu ${directFor.schedule_type_name} de ${fmtDate(directFor.date)} por:`}
          empty="Nenhum turno de colega do mesmo grupo neste mês."
          items={othersShifts.filter((a) => groupOf(a) === groupOf(directFor)).map((a) => ({
            id: a.id, label: `${a.user_name} · ${fmtDate(a.date)} · ${a.schedule_type_name}`,
          }))}
          onPick={(aid) => run(direct.mutateAsync({ requester_assignment_id: directFor.id, target_assignment_id: aid })).then(() => setDirectFor(null))}
          onClose={() => setDirectFor(null)}
        />
      )}

      {/* Picker: propor no mural — escolher meu turno (mesmo grupo da oferta) */}
      {proposeFor && (
        <Picker
          title={`Propor um turno seu de ${proposeFor.group} para ${proposeFor.requester_name}:`}
          empty="Você não tem turno do mesmo grupo neste mês."
          items={myShifts.filter((a) => groupOf(a) === proposeFor.group).map((a) => ({
            id: a.id, label: `${fmtDate(a.date)} · ${a.schedule_type_name}`,
          }))}
          onPick={(aid) => run(propose.mutateAsync({ id: proposeFor.id, target_assignment_id: aid })).then(() => setProposeFor(null))}
          onClose={() => setProposeFor(null)}
        />
      )}
    </div>
  )
}

function Picker({ title, items, empty, onPick, onClose }: {
  title: string
  items: { id: string; label: string }[]
  empty: string
  onPick: (id: string) => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <p className="font-bold mb-3">{title}</p>
        {items.length === 0 ? (
          <p className="text-sm text-gray-500">{empty}</p>
        ) : (
          <div className="space-y-1">
            {items.map((it) => (
              <button key={it.id} onClick={() => onPick(it.id)} className="w-full text-left rounded-lg border border-gray-200 px-3 py-2 text-sm hover:bg-primary-50 hover:border-primary-300">
                {it.label}
              </button>
            ))}
          </div>
        )}
        <div className="mt-4 flex justify-end"><Button size="sm" variant="secondary" onClick={onClose}>Fechar</Button></div>
      </div>
    </div>
  )
}
