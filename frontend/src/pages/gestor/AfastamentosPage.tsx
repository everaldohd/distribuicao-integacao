import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { Card, CardBody } from '../../components/ui/Card'

interface Afastamento {
  id: string
  user_name: string
  start_date: string
  end_date: string
  notes: string | null
  self_requested: boolean
  created_at: string
}

const brDate = (d: string) => d.split('-').reverse().join('/')

export function AfastamentosPage() {
  const qc = useQueryClient()

  const { data: list = [], isLoading } = useQuery<Afastamento[]>({
    queryKey: ['afastamentos-review'],
    queryFn: () => api.get('/unavailabilities').then((r) => r.data),
  })

  const deny = useMutation({
    mutationFn: (id: string) => api.delete(`/unavailabilities/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['afastamentos-review'] }),
  })

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Afastamentos</h1>
        <p className="text-sm text-gray-500">
          Afastamentos lançados pelos peritos. Já estão valendo — negue os que não forem devidos (fica registrado na auditoria).
        </p>
      </div>

      <Card><CardBody>
        {isLoading ? (
          <p className="text-sm text-gray-500 py-4">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="text-sm text-gray-500 py-4">Nenhum afastamento lançado pelos peritos.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-4">Perito</th>
                  <th className="py-2 pr-4">Período</th>
                  <th className="py-2 pr-4">Observação</th>
                  <th className="py-2 pr-4">Solicitado em</th>
                  <th className="py-2 pr-4 text-right">Ação</th>
                </tr>
              </thead>
              <tbody>
                {list.map((a) => (
                  <tr key={a.id} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-medium text-gray-800">{a.user_name}</td>
                    <td className="py-2 pr-4">{brDate(a.start_date)} → {brDate(a.end_date)}</td>
                    <td className="py-2 pr-4 text-gray-500">{a.notes || '—'}</td>
                    <td className="py-2 pr-4 text-gray-400">{new Date(a.created_at).toLocaleDateString('pt-BR')}</td>
                    <td className="py-2 pr-4 text-right">
                      <button
                        onClick={() => { if (confirm(`Negar o afastamento de ${a.user_name}?`)) deny.mutate(a.id) }}
                        className="text-xs px-3 py-1 rounded-lg border border-red-300 text-red-600 hover:bg-red-50"
                      >Negar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody></Card>
    </div>
  )
}
