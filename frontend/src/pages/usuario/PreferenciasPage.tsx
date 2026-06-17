import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Preference, OperationalCalendar } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'

export function PreferenciasPage() {
  const qc = useQueryClient()
  const [form, setForm] = useState({ date: '', type: 'DESIRED' as 'DESIRED' | 'AVOID', calendar_id: '' })

  const { data: calendars = [] } = useQuery<OperationalCalendar[]>({
    queryKey: ['calendars'],
    queryFn: () => api.get('/calendars/').then((r) => r.data),
  })

  const { data: preferences = [], isLoading } = useQuery<Preference[]>({
    queryKey: ['preferences'],
    queryFn: () => api.get('/preferences/').then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/preferences/', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['preferences'] }); setForm({ date: '', type: 'DESIRED', calendar_id: '' }) },
  })

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/preferences/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['preferences'] }),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Preferências</h1>

      <Card>
        <CardHeader><p className="font-semibold">Registrar preferência</p></CardHeader>
        <CardBody>
          <form className="flex flex-wrap gap-3 items-end" onSubmit={(e) => { e.preventDefault(); create.mutate(form) }}>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Calendário</label>
              <select className="rounded-lg border border-gray-300 px-3 py-2 text-sm" value={form.calendar_id} onChange={(e) => setForm({ ...form, calendar_id: e.target.value })} required>
                <option value="">Selecione...</option>
                {calendars.map((c) => <option key={c.id} value={c.id}>{c.month}/{c.year}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Data</label>
              <input type="date" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Tipo</label>
              <select className="rounded-lg border border-gray-300 px-3 py-2 text-sm" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as 'DESIRED' | 'AVOID' })}>
                <option value="DESIRED">Desejo trabalhar</option>
                <option value="AVOID">Prefiro não trabalhar</option>
              </select>
            </div>
            <Button type="submit" loading={create.isPending}>Adicionar</Button>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader><p className="font-semibold">Minhas preferências</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : preferences.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma preferência registrada.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Data</th>
                <th className="px-6 py-3 text-left">Tipo</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {preferences.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono">{p.date}</td>
                  <td className="px-6 py-3">
                    <Badge label={p.type === 'DESIRED' ? 'Desejo trabalhar' : 'Prefiro não trabalhar'} color={p.type === 'DESIRED' ? 'green' : 'yellow'} />
                  </td>
                  <td className="px-6 py-3 text-right">
                    <Button size="sm" variant="danger" onClick={() => remove.mutate(p.id)}>Remover</Button>
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
