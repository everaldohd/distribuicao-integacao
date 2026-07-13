import { useState, useEffect } from 'react'
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

// --- Importação da planilha macro -----------------------------------------

interface XlsxDayCell {
  day: number
  weekend: boolean
  plantao: string[]
  rm: string; rt: string; pim: string; pit: string
}
interface ParseResult {
  sheet_name: string
  sections_found: string[]
  default_selected: string[]
  types: string[]
  grid: XlsxDayCell[]
}

const IMPORT_TYPES = ['Plantão 12h', 'Reserva Manhã', 'Reserva Tarde', 'Reserva 12h', 'Pátio Manhã', 'Pátio Tarde']

// Extrai uma mensagem legível de um erro do axios/FastAPI. O `detail` de um 422
// vem como array de objetos — renderizá-lo direto quebra o React, então tratamos aqui.
function errMsg(error: any, fallback: string): string {
  const d = error?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((e: any) => e?.msg).filter(Boolean).join('; ') || fallback
  if (d && typeof d === 'object') return d.msg ?? fallback
  return error?.message ?? fallback
}

// Espelha a regra do backend (app/services/xlsx_import.coverage_from_grid) só para o preview.
function previewTotals(grid: XlsxDayCell[], selected: string[]): Record<string, number> {
  const sel = new Set(selected.map(s => s.toUpperCase()))
  const t: Record<string, number> = Object.fromEntries(IMPORT_TYPES.map(x => [x, 0]))
  for (const c of grid) {
    t['Plantão 12h'] += c.plantao.filter(s => sel.has((s || '').toUpperCase())).length
    const rm = (c.rm || '').toUpperCase(), rt = (c.rt || '').toUpperCase()
    if (c.weekend && rm && rm === rt) { if (sel.has(rm)) t['Reserva 12h']++ }
    else { if (sel.has(rm)) t['Reserva Manhã']++; if (sel.has(rt)) t['Reserva Tarde']++ }
    if (sel.has((c.pim || '').toUpperCase())) t['Pátio Manhã']++
    if (sel.has((c.pit || '').toUpperCase())) t['Pátio Tarde']++
  }
  return t
}

function ImportXlsxModal({ calendarId, year, month, onClose }: { calendarId: string; year: number; month: number; onClose: () => void }) {
  const qc = useQueryClient()
  const [parsed, setParsed] = useState<ParseResult | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [dragging, setDragging] = useState(false)

  // Enquanto o modal está aberto, impede que soltar o arquivo fora da área
  // faça o browser navegar para o arquivo (a "piscada").
  useEffect(() => {
    const prevent = (e: DragEvent) => { e.preventDefault() }
    window.addEventListener('dragover', prevent)
    window.addEventListener('drop', prevent)
    return () => {
      window.removeEventListener('dragover', prevent)
      window.removeEventListener('drop', prevent)
    }
  }, [])

  const parse = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      form.append('year', String(year))
      form.append('month', String(month))
      const r = await api.post('/calendars/parse-xlsx', form)
      return r.data as ParseResult
    },
    onSuccess: (data) => { setParsed(data); setSelected(data.default_selected) },
  })

  const apply = useMutation({
    mutationFn: () => api.post(`/calendars/${calendarId}/import-xlsx`, { selected_sections: selected, grid: parsed!.grid }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['calendar', calendarId] }); onClose() },
  })

  const toggle = (s: string) => setSelected(cur => cur.includes(s) ? cur.filter(x => x !== s) : [...cur, s])
  const totals = parsed ? previewTotals(parsed.grid, selected) : null
  const totalVagas = totals ? Object.values(totals).reduce((a, b) => a + b, 0) : 0

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="font-bold text-lg">Importar cobertura de planilha</p>
            <p className="text-sm text-gray-500">Lê a escala macro (.xlsx) e configura os dias com as seções que você escolher.</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        {!parsed && (
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300'}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragEnter={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={e => { e.preventDefault(); setDragging(false) }}
            onDrop={e => {
              e.preventDefault(); setDragging(false)
              const f = e.dataTransfer.files?.[0]
              if (f) parse.mutate(f)
            }}
          >
            <input
              id="xlsx-file" type="file" accept=".xlsx,.xlsm" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) parse.mutate(f) }}
            />
            <label htmlFor="xlsx-file" className="cursor-pointer">
              <div className="text-gray-600 mb-2">
                {parse.isPending ? 'Lendo planilha…' : (dragging ? 'Solte o arquivo aqui' : 'Arraste o .xlsx aqui ou clique para escolher')}
              </div>
              <span className="inline-block px-4 py-2 bg-primary-600 text-white rounded-lg text-sm">Selecionar arquivo</span>
            </label>
            <p className="mt-3 text-xs text-gray-400">Procura automaticamente a aba do mês {String(month).padStart(2, '0')}/{year}.</p>
            {parse.isError && <p className="mt-3 text-sm text-red-600">{errMsg(parse.error, 'Falha ao ler a planilha.')}</p>}
          </div>
        )}

        {parsed && (
          <>
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                Aba <span className="font-mono font-semibold">{parsed.sheet_name}</span> · {parsed.sections_found.length} seções encontradas.
                Marque as seções de interesse:
              </p>
              <div className="flex flex-wrap gap-2">
                {parsed.sections_found.map(s => {
                  const on = selected.includes(s)
                  return (
                    <button key={s} onClick={() => toggle(s)}
                      className={`px-3 py-1 rounded-full text-sm border transition-colors ${on ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'}`}>
                      {on ? '✓ ' : ''}{s}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <p className="text-sm font-semibold text-gray-700 mb-2">Prévia da cobertura ({totalVagas} vagas no mês)</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
                {IMPORT_TYPES.map(t => (
                  <div key={t} className="flex justify-between bg-white rounded px-2 py-1">
                    <span className="text-gray-600 truncate">{t}</span>
                    <span className="font-mono font-semibold">{totals?.[t] ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2 justify-between items-center">
              <button onClick={() => { setParsed(null); setSelected([]) }} className="text-sm text-gray-500 hover:text-gray-700">← Trocar arquivo</button>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={onClose}>Cancelar</Button>
                <Button size="sm" loading={apply.isPending} disabled={totalVagas === 0} onClick={() => apply.mutate()}>
                  Aplicar ao calendário
                </Button>
              </div>
            </div>
            {apply.isError && <p className="mt-2 text-xs text-red-600">{errMsg(apply.error, 'Erro ao aplicar.')}</p>}
          </>
        )}
      </div>
    </div>
  )
}

export function CalendarioDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [editingDay, setEditingDay] = useState<OperationalCalendar['days'][0] | null>(null)
  const [showImport, setShowImport] = useState(false)

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
            label={calendar.status === 'draft' ? 'Rascunho' : calendar.status === 'open' ? 'Aberto' : 'Finalizado'}
            color={calendar.status === 'draft' ? 'gray' : calendar.status === 'open' ? 'green' : 'yellow'}
          />
          <Button size="sm" variant="secondary" onClick={() => setShowImport(true)}>
            Importar planilha (xlsx)
          </Button>
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

      {/* Importar planilha */}
      {showImport && (
        <ImportXlsxModal
          calendarId={id!}
          year={calendar.year}
          month={calendar.month}
          onClose={() => setShowImport(false)}
        />
      )}
    </div>
  )
}
