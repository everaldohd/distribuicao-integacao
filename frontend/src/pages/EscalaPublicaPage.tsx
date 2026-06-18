/**
 * Escala geral (pública) — calendário do mês publicado visível a qualquer perito.
 * Mostra todos os turnos de todos os peritos. É a base para identificar quem
 * trabalha quando e disparar trocas.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Schedule } from '../lib/types'
import { Card, CardBody } from '../components/ui/Card'
import { getDay } from 'date-fns'

const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
const WEEKDAYS = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']

function shortName(name: string | null): string {
  if (!name) return '—'
  const p = name.trim().split(/\s+/)
  return p.length === 1 ? p[0] : `${p[0]} ${p[p.length - 1][0]}.`
}

export function EscalaPublicaPage() {
  const today = new Date()
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() + 1 })

  const { data: schedule, isLoading, isError } = useQuery<Schedule>({
    queryKey: ['published-schedule', cursor.year, cursor.month],
    queryFn: () => api.get('/schedules/published', { params: { year: cursor.year, month: cursor.month } }).then((r) => r.data),
    retry: false,
  })

  function move(delta: number) {
    setCursor((c) => {
      let m = c.month + delta, y = c.year
      if (m < 1) { m = 12; y -= 1 }
      if (m > 12) { m = 1; y += 1 }
      return { year: y, month: m }
    })
  }

  const firstDay = new Date(cursor.year, cursor.month - 1, 1)
  const startOffset = getDay(firstDay)
  const daysInMonth = new Date(cursor.year, cursor.month, 0).getDate()
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)

  const byDay: Record<number, Schedule['assignments']> = {}
  schedule?.assignments.forEach((a) => {
    const d = Number(a.date.slice(8, 10))
    ;(byDay[d] ??= []).push(a)
  })

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">Escala geral</h1>

      <div className="flex items-center justify-between">
        <button onClick={() => move(-1)} className="flex items-center justify-center w-12 h-12 rounded-full bg-white border border-gray-200 shadow-sm text-2xl text-gray-600 hover:bg-gray-50 hover:text-primary-600" aria-label="Mês anterior">‹</button>
        <p className="text-xl font-bold text-gray-900">{MONTHS[cursor.month - 1]} {cursor.year}</p>
        <button onClick={() => move(1)} className="flex items-center justify-center w-12 h-12 rounded-full bg-white border border-gray-200 shadow-sm text-2xl text-gray-600 hover:bg-gray-50 hover:text-primary-600" aria-label="Próximo mês">›</button>
      </div>

      <Card>
        <CardBody>
          {isLoading ? (
            <div className="flex justify-center py-10"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
          ) : isError || !schedule ? (
            <p className="text-sm text-gray-500 py-6 text-center">Nenhuma escala publicada para {MONTHS[cursor.month - 1]} {cursor.year}.</p>
          ) : (
            <>
              <div className="grid grid-cols-7 text-center text-xs font-semibold text-gray-500 uppercase mb-2">
                {WEEKDAYS.map((d) => <div key={d}>{d}</div>)}
              </div>
              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: startOffset }).map((_, i) => <div key={`e-${i}`} />)}
                {days.map((dayNum) => {
                  const isWeekend = [0, 6].includes(getDay(new Date(cursor.year, cursor.month - 1, dayNum)))
                  const items = (byDay[dayNum] ?? []).slice().sort((a, b) => a.schedule_type_name.localeCompare(b.schedule_type_name))
                  return (
                    <div key={dayNum} className={`rounded-lg p-2 min-h-[110px] ring-1 ring-gray-100 ${isWeekend ? 'bg-blue-50' : 'bg-white'}`}>
                      <div className={`text-sm font-bold mb-1 ${isWeekend ? 'text-blue-700' : 'text-gray-800'}`}>{dayNum}</div>
                      <div className="space-y-0.5">
                        {items.map((a) => (
                          <div key={a.id} className={`text-[11px] leading-tight rounded px-1 py-0.5 ${a.is_gap ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}
                               title={`${a.schedule_type_name}: ${a.user_name ?? 'SEM PERITO'}`}>
                            <span className="font-medium">{a.is_gap ? '⚠ ' : ''}{shortName(a.user_name)}</span>
                            <span className="block text-[9px] text-gray-400 truncate">{a.schedule_type_name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
