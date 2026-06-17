import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { ScheduleType } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'

export function TiposEscalaPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', requires_rest_day_after: false })

  const { data: types = [], isLoading } = useQuery<ScheduleType[]>({
    queryKey: ['schedule-types'],
    queryFn: () => api.get('/schedule-types/').then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/schedule-types/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule-types'] })
      setShowForm(false)
      setForm({ name: '', requires_rest_day_after: false })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Tipos de Escala</h1>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancelar' : '+ Novo tipo'}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><p className="font-semibold">Novo tipo de escala</p></CardHeader>
          <CardBody>
            <form
              className="flex gap-4 items-end"
              onSubmit={(e) => { e.preventDefault(); create.mutate(form) }}
            >
              <div className="flex-1">
                <Input label="Nome" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer pb-2">
                <input
                  type="checkbox"
                  checked={form.requires_rest_day_after}
                  onChange={(e) => setForm({ ...form, requires_rest_day_after: e.target.checked })}
                  className="rounded"
                />
                Exige interstício (Plantão 12h)
              </label>
              <Button type="submit" loading={create.isPending}>Criar</Button>
            </form>
            {create.isError && <p className="mt-2 text-sm text-red-600">Erro ao criar tipo.</p>}
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader><p className="font-semibold">Tipos cadastrados</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Nome</th>
                <th className="px-6 py-3 text-left">Interstício</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {types.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium">{t.name}</td>
                  <td className="px-6 py-3">
                    {t.requires_rest_day_after
                      ? <Badge label="Sim — bloqueia dia seguinte" color="yellow" />
                      : <Badge label="Não" color="gray" />}
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
