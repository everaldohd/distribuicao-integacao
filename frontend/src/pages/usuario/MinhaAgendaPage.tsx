import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { getMe } from '../../lib/auth'
import type { PreferenceType, PreferenceOptions, Schedule } from '../../lib/types'
import { Card, CardBody } from '../../components/ui/Card'
import { getDay, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
const WEEKDAYS = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']

// Paleta de cores por modalidade (índice)
const PALETTE = ['#2563eb', '#16a34a', '#9333ea', '#ea580c', '#0891b2', '#db2777', '#65a30d', '#475569']

export function MinhaAgendaPage() {
  const qc = useQueryClient()
  const today = new Date()
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() + 1 })
  const [mode, setMode] = useState<PreferenceType>('desired')
  const [activeModality, setActiveModality] = useState<string | null>(null)
  const [error, setError] = useState('')

  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe })

  // Detecta escala publicada do mês
  const { data: schedules = [] } = useQuery<Schedule[]>({
    queryKey: ['schedules'],
    queryFn: () => api.get('/schedules/').then((r) => r.data),
  })
  const publishedSched = schedules
    .filter((s) => s.year === cursor.year && s.month === cursor.month && s.status === 'published')
    .sort((a, b) => b.version - a.version)[0]
  const isPublished = !!publishedSched

  const { data: fullSched } = useQuery<Schedule>({
    queryKey: ['schedule', publishedSched?.id],
    queryFn: () => api.get(`/schedules/${publishedSched!.id}`).then((r) => r.data),
    enabled: isPublished,
  })
  const myShiftByDate = useMemo(() => {
    const m: Record<string, string> = {}
    fullSched?.assignments.filter((a) => a.user_id === me?.id && !a.is_gap).forEach((a) => { m[a.date] = a.schedule_type_name })
    return m
  }, [fullSched, me])

  // Opções de preferência (modalidades, limites, disponibilidade) — carrega sempre,
  // pois as marcações continuam visíveis (travadas) mesmo após a publicação.
  const { data: options } = useQuery<PreferenceOptions>({
    queryKey: ['pref-options', cursor.year, cursor.month],
    queryFn: () => api.get('/preferences/options', { params: { year: cursor.year, month: cursor.month } }).then((r) => r.data),
  })

  const modalities = options?.modalities ?? []
  const colorOf = (typeId: string) => {
    const i = modalities.findIndex((m) => m.schedule_type_id === typeId)
    return i >= 0 ? PALETTE[i % PALETTE.length] : '#94a3b8'
  }
  const groupOf = (typeId: string) => modalities.find((m) => m.schedule_type_id === typeId)?.group_name ?? ''

  // Garante uma modalidade ativa
  const effectiveModality = activeModality && modalities.some((m) => m.schedule_type_id === activeModality)
    ? activeModality
    : modalities[0]?.schedule_type_id ?? null

  const create = useMutation({
    mutationFn: (b: { date: string; schedule_type_id: string; type: PreferenceType }) =>
      api.post('/preferences/', { year: cursor.year, month: cursor.month, ...b }),
  })
  const remove = useMutation({ mutationFn: (id: string) => api.delete(`/preferences/${id}`) })

  const [pendingKey, setPendingKey] = useState<string | null>(null)

  async function toggle(iso: string) {
    if (!effectiveModality) return
    setError('')
    const existing = options?.preferences.find(
      (p) => p.date === iso && p.schedule_type_id === effectiveModality && p.type === mode,
    )
    const key = `${iso}-${effectiveModality}-${mode}`
    setPendingKey(key)
    try {
      if (existing) await remove.mutateAsync(existing.id)
      else await create.mutateAsync({ date: iso, schedule_type_id: effectiveModality, type: mode })
      await qc.invalidateQueries({ queryKey: ['pref-options', cursor.year, cursor.month] })
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Não foi possível salvar.')
    } finally {
      setPendingKey(null)
    }
  }

  function move(delta: number) {
    setError('')
    setCursor((c) => {
      let m = c.month + delta, y = c.year
      if (m < 1) { m = 12; y -= 1 }
      if (m > 12) { m = 1; y += 1 }
      return { year: y, month: m }
    })
  }

  // Uso por grupo no modo atual (para mostrar restante)
  const usedByGroup = useMemo(() => {
    const u: Record<string, number> = {}
    options?.preferences.filter((p) => p.type === mode && p.schedule_type_id).forEach((p) => {
      const g = groupOf(p.schedule_type_id!)
      u[g] = (u[g] ?? 0) + 1
    })
    return u
  }, [options, mode])

  const firstDay = new Date(cursor.year, cursor.month - 1, 1)
  const startOffset = getDay(firstDay)
  const daysInMonth = new Date(cursor.year, cursor.month, 0).getDate()
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)

  const availSet = (typeId: string | null) => new Set(typeId ? (options?.availability[typeId] ?? []) : [])
  const activeAvail = availSet(effectiveModality)

  const myShiftsCount = Object.keys(myShiftByDate).length

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">Minha Agenda</h1>

      {/* Navegação de mês */}
      <div className="flex items-center justify-between">
        <button onClick={() => move(-1)} className="flex items-center justify-center w-12 h-12 rounded-full bg-white border border-gray-200 shadow-sm text-2xl text-gray-600 hover:bg-gray-50 hover:text-primary-600" aria-label="Mês anterior">‹</button>
        <div className="text-center">
          <p className="text-xl font-bold text-gray-900">{MONTHS[cursor.month - 1]} {cursor.year}</p>
          {isPublished
            ? <p className="text-sm text-amber-600 font-medium">Escala publicada — {myShiftsCount} turno(s) seus</p>
            : <p className="text-sm text-gray-500">Preferências abertas</p>}
        </div>
        <button onClick={() => move(1)} className="flex items-center justify-center w-12 h-12 rounded-full bg-white border border-gray-200 shadow-sm text-2xl text-gray-600 hover:bg-gray-50 hover:text-primary-600" aria-label="Próximo mês">›</button>
      </div>

      {/* ===== Mês publicado: somente leitura (dourado) ===== */}
      {isPublished ? (
        <>
          <Card><CardBody className="py-3">
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
              <span className="flex items-center gap-2"><span className="inline-block w-4 h-4 rounded bg-amber-400" /> Dia em que você foi escalado</span>
              <span className="flex items-center gap-2"><span className="inline-block w-3 h-3 rounded-full bg-gray-400" /> suas preferências (apenas registro)</span>
              <span className="ml-auto text-gray-400 italic">Escala publicada — somente leitura</span>
            </div>
          </CardBody></Card>
          <Card><CardBody>
            <div className="grid grid-cols-7 text-center text-xs font-semibold text-gray-500 uppercase mb-2">
              {WEEKDAYS.map((d) => <div key={d}>{d}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: startOffset }).map((_, i) => <div key={`e-${i}`} />)}
              {days.map((dayNum) => {
                const iso = `${cursor.year}-${String(cursor.month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`
                const isWeekend = [0, 6].includes(getDay(new Date(cursor.year, cursor.month - 1, dayNum)))
                const shift = myShiftByDate[iso]
                const dayPrefs = (options?.preferences ?? []).filter((p) => p.date === iso)
                return (
                  <div key={iso} className={`rounded-lg min-h-[80px] p-2 ring-1 ring-gray-100 ${shift ? 'bg-amber-400 text-amber-950 shadow-sm' : isWeekend ? 'bg-blue-50' : 'bg-gray-50'}`}>
                    <span className="text-sm font-bold">{dayNum}</span>
                    {shift && <span className="block text-[11px] font-semibold mt-1 leading-tight">{shift}</span>}
                    {dayPrefs.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {dayPrefs.map((p) => (
                          <span
                            key={p.id}
                            title={`${modalities.find((m) => m.schedule_type_id === p.schedule_type_id)?.name ?? 'Preferência'} — ${p.type === 'desired' ? 'desejo' : 'evitar'}`}
                            className="inline-block w-3 h-3 rounded-full"
                            style={{
                              backgroundColor: p.type === 'desired' ? colorOf(p.schedule_type_id ?? '') : '#fff',
                              border: `2px solid ${colorOf(p.schedule_type_id ?? '')}`,
                            }}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </CardBody></Card>
        </>
      ) : modalities.length === 0 ? (
        <Card><CardBody><p className="text-sm text-gray-500">Seu perfil não permite registrar preferências (cotas zeradas). Fale com o gestor.</p></CardBody></Card>
      ) : (
        <>
          {/* Controles: modo + modalidades */}
          <Card><CardBody className="space-y-3">
            {/* Modo desejo/evitar */}
            <div className="inline-flex rounded-lg border border-gray-200 overflow-hidden">
              <button onClick={() => setMode('desired')} className={`px-4 py-2 text-sm font-medium ${mode === 'desired' ? 'bg-green-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>Desejo trabalhar</button>
              <button onClick={() => setMode('avoid')} className={`px-4 py-2 text-sm font-medium ${mode === 'avoid' ? 'bg-red-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>Prefiro não</button>
            </div>

            {/* Botões de modalidade */}
            <div>
              <p className="text-xs text-gray-500 mb-2">Escolha a modalidade e clique nos dias disponíveis:</p>
              <div className="flex flex-wrap gap-2">
                {modalities.map((m) => {
                  const active = m.schedule_type_id === effectiveModality
                  const cap = options?.group_caps[m.group_name] ?? 0
                  const used = usedByGroup[m.group_name] ?? 0
                  const color = colorOf(m.schedule_type_id)
                  return (
                    <button
                      key={m.schedule_type_id}
                      onClick={() => setActiveModality(m.schedule_type_id)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border transition-all ${active ? 'text-white shadow' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                      style={active ? { backgroundColor: color, borderColor: color } : { borderColor: color }}
                    >
                      <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: active ? '#fff' : color }} />
                      {m.name}
                      <span className={`text-xs ${active ? 'text-white/80' : 'text-gray-400'}`}>({used}/{cap})</span>
                    </button>
                  )
                })}
              </div>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </CardBody></Card>

          {/* Calendário */}
          <Card><CardBody>
            <div className="grid grid-cols-7 text-center text-xs font-semibold text-gray-500 uppercase mb-2">
              {WEEKDAYS.map((d) => <div key={d}>{d}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: startOffset }).map((_, i) => <div key={`e-${i}`} />)}
              {days.map((dayNum) => {
                const iso = `${cursor.year}-${String(cursor.month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`
                const isWeekend = [0, 6].includes(getDay(new Date(cursor.year, cursor.month - 1, dayNum)))
                const available = activeAvail.has(iso)
                const dayPrefs = (options?.preferences ?? []).filter((p) => p.date === iso)
                const isPending = pendingKey?.startsWith(`${iso}-`)
                const selectedHere = dayPrefs.some((p) => p.schedule_type_id === effectiveModality && p.type === mode)

                return (
                  <button
                    key={iso}
                    onClick={() => available && toggle(iso)}
                    disabled={!available || isPending}
                    className={`relative rounded-lg min-h-[84px] p-2 text-left transition-all ring-1
                      ${available ? 'cursor-pointer ring-gray-200 hover:ring-primary-400' : 'ring-gray-100 opacity-40 cursor-not-allowed'}
                      ${isWeekend ? 'bg-blue-50' : 'bg-white'} ${selectedHere ? 'ring-2 ring-offset-1' : ''} ${isPending ? 'opacity-50' : ''}`}
                  >
                    <span className="text-sm font-bold text-gray-800">{dayNum}</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {dayPrefs.map((p) => (
                        <span
                          key={p.id}
                          title={`${modalities.find((m) => m.schedule_type_id === p.schedule_type_id)?.name} — ${p.type === 'desired' ? 'desejo' : 'evitar'}`}
                          className="inline-block w-3 h-3 rounded-full"
                          style={{
                            backgroundColor: p.type === 'desired' ? colorOf(p.schedule_type_id ?? '') : '#fff',
                            border: `2px solid ${colorOf(p.schedule_type_id ?? '')}`,
                          }}
                        />
                      ))}
                    </div>
                  </button>
                )
              })}
            </div>
            <p className="mt-3 text-xs text-gray-400">
              Bolinha cheia = desejo · contorno vazado = evitar · cor = modalidade. Dias apagados não têm essa modalidade no calendário.
            </p>
          </CardBody></Card>
        </>
      )}
    </div>
  )
}
