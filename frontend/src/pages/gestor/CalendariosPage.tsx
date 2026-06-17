import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import type { OperationalCalendar } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'

const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export function CalendariosPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const currentYear = new Date().getFullYear()
  const [form, setForm] = useState({ year: currentYear, month: new Date().getMonth() + 1 })
  const [showForm, setShowForm] = useState(false)

  const { data: calendars = [], isLoading } = useQuery<OperationalCalendar[]>({
    queryKey: ['calendars'],
    queryFn: () => api.get('/calendars/').then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (data: { year: number; month: number }) => api.post('/calendars/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['calendars'] })
      setShowForm(false)
    },
  })

  const applyTemplate = useMutation({
    mutationFn: (calendarId: string) => api.post(`/calendars/${calendarId}/apply-default-template`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['calendars'] }),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Calendários</h1>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancelar' : '+ Novo calendário'}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><p className="font-semibold">Criar calendário do mês</p></CardHeader>
          <CardBody>
            <form
              className="flex gap-4 items-end"
              onSubmit={(e) => { e.preventDefault(); create.mutate(form) }}
            >
              <Input
                label="Ano"
                type="number"
                value={form.year}
                onChange={(e) => setForm({ ...form, year: Number(e.target.value) })}
                min={2024}
                max={2099}
              />
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700">Mês</label>
                <select
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  value={form.month}
                  onChange={(e) => setForm({ ...form, month: Number(e.target.value) })}
                >
                  {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                </select>
              </div>
              <Button type="submit" loading={create.isPending}>Criar</Button>
            </form>
            {create.isError && <p className="mt-2 text-sm text-red-600">Erro ao criar calendário.</p>}
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader><p className="font-semibold">Calendários cadastrados</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : calendars.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhum calendário criado ainda.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Período</th>
                <th className="px-6 py-3 text-left">Status</th>
                <th className="px-6 py-3 text-left">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {calendars.map((cal) => (
                <tr key={cal.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium">{MONTHS[cal.month - 1]} / {cal.year}</td>
                  <td className="px-6 py-3">
                    <Badge
                      label={cal.status === 'draft' ? '① Rascunho' : cal.status === 'open' ? '② Aberto' : '③ Bloqueado'}
                      color={cal.status === 'draft' ? 'gray' : cal.status === 'open' ? 'green' : 'yellow'}
                    />
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => navigate(`/gestor/calendarios/${cal.id}`)}
                      >
                        Configurar dias →
                      </Button>
                      {cal.status === 'draft' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={applyTemplate.isPending}
                          onClick={() => applyTemplate.mutate(cal.id)}
                        >
                          Preencher padrão
                        </Button>
                      )}
                    </div>
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
