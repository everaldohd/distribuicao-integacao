import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Exchange } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'

const statusColor: Record<string, 'gray' | 'blue' | 'green' | 'red' | 'yellow'> = {
  OPEN: 'blue',
  ACCEPTED: 'green',
  REJECTED: 'red',
  CANCELLED: 'gray',
}

const statusLabel: Record<string, string> = {
  OPEN: 'Aberta',
  ACCEPTED: 'Aceita',
  REJECTED: 'Recusada',
  CANCELLED: 'Cancelada',
}

export function TrocasPage() {
  const qc = useQueryClient()

  const { data: open = [], isLoading: loadingOpen } = useQuery<Exchange[]>({
    queryKey: ['exchanges-open'],
    queryFn: () => api.get('/exchanges/open').then((r) => r.data),
  })

  const { data: myExchanges = [], isLoading: loadingMine } = useQuery<Exchange[]>({
    queryKey: ['exchanges-mine'],
    queryFn: () => api.get('/exchanges/').then((r) => r.data),
  })

  const accept = useMutation({
    mutationFn: (id: string) => api.post(`/exchanges/${id}/accept`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['exchanges-open'] })
      qc.invalidateQueries({ queryKey: ['exchanges-mine'] })
    },
  })

  const reject = useMutation({
    mutationFn: (id: string) => api.post(`/exchanges/${id}/reject`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['exchanges-open'] })
      qc.invalidateQueries({ queryKey: ['exchanges-mine'] })
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Trocas de Escala</h1>

      <Card>
        <CardHeader><p className="font-semibold">Trocas abertas disponíveis</p></CardHeader>
        {loadingOpen ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : open.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma troca aberta no momento.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Solicitante</th>
                <th className="px-6 py-3 text-left">Data</th>
                <th className="px-6 py-3 text-left">Tipo</th>
                <th className="px-6 py-3 text-left">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {open.map((ex) => (
                <tr key={ex.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium">{ex.requester_name}</td>
                  <td className="px-6 py-3 font-mono">{ex.assignment_date}</td>
                  <td className="px-6 py-3">{ex.assignment_type}</td>
                  <td className="px-6 py-3 flex gap-2">
                    <Button size="sm" loading={accept.isPending} onClick={() => accept.mutate(ex.id)}>Aceitar</Button>
                    <Button size="sm" variant="danger" loading={reject.isPending} onClick={() => reject.mutate(ex.id)}>Recusar</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card>
        <CardHeader><p className="font-semibold">Minhas solicitações</p></CardHeader>
        {loadingMine ? (
          <CardBody><div className="flex justify-center py-4"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : myExchanges.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhuma solicitação de troca enviada.</p></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Data</th>
                <th className="px-6 py-3 text-left">Tipo</th>
                <th className="px-6 py-3 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {myExchanges.map((ex) => (
                <tr key={ex.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono">{ex.assignment_date}</td>
                  <td className="px-6 py-3">{ex.assignment_type}</td>
                  <td className="px-6 py-3">
                    <Badge label={statusLabel[ex.status] ?? ex.status} color={statusColor[ex.status] ?? 'gray'} />
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
