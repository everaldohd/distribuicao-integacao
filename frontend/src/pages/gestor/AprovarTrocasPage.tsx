/**
 * Aprovação de trocas (gestor): lista as trocas que os peritos já acertaram entre si
 * (aguardando gestor) e permite aprovar — executando o swap — ou recusar. Tudo auditado.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Exchange } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const fmtDate = (d: string | null) => (d ? format(new Date(d + 'T00:00:00'), 'dd/MM (EEE)', { locale: ptBR }) : '—')

export function AprovarTrocasPage() {
  const qc = useQueryClient()
  const [err, setErr] = useState('')

  const { data: pending = [], isLoading } = useQuery<Exchange[]>({
    queryKey: ['ex-pending'],
    queryFn: () => api.get('/exchanges/pending-approval').then((r) => r.data),
  })

  const act = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'manager-reject' }) =>
      api.post(`/exchanges/${id}/${action}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ex-pending'] }),
    onError: (e: any) => setErr(e?.response?.data?.detail ?? 'Erro ao processar.'),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Aprovar Trocas</h1>
        <p className="text-sm text-gray-500 mt-1">Trocas acertadas entre peritos, aguardando sua aprovação.</p>
      </div>
      {err && <p className="text-sm text-red-600">{err}</p>}

      <Card>
        <CardHeader><p className="font-semibold">Aguardando aprovação</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-6"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : pending.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma troca aguardando aprovação.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase"><tr>
              <th className="px-6 py-3 text-left">Grupo</th>
              <th className="px-6 py-3 text-left">Sai</th>
              <th className="px-6 py-3 text-left">Entra</th>
              <th className="px-6 py-3 text-right">Ação</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {pending.map((ex) => (
                <tr key={ex.id} className="hover:bg-gray-50 align-top">
                  <td className="px-6 py-3">{ex.group}</td>
                  <td className="px-6 py-3">
                    <div className="font-medium">{ex.requester_name}</div>
                    <div className="text-xs text-gray-500">{fmtDate(ex.requester_date)} · {ex.requester_type}</div>
                  </td>
                  <td className="px-6 py-3">
                    <div className="font-medium">{ex.target_name}</div>
                    <div className="text-xs text-gray-500">{fmtDate(ex.target_date)} · {ex.target_type}</div>
                  </td>
                  <td className="px-6 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" loading={act.isPending} onClick={() => act.mutate({ id: ex.id, action: 'approve' })}>Aprovar</Button>
                      <Button size="sm" variant="danger" loading={act.isPending} onClick={() => act.mutate({ id: ex.id, action: 'manager-reject' })}>Recusar</Button>
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
