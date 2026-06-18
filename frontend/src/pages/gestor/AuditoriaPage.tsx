/**
 * Auditoria (gestor): trilha de todas as ações registradas no sistema —
 * quem fez, o quê, quando, com descrição e valores anterior/novo (transparência).
 * Permite filtrar por ação e por tipo de entidade, e paginar.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { AuditEntry } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const ACTION_LABEL: Record<string, string> = {
  create: 'Criação', update: 'Alteração', delete: 'Exclusão',
  publish: 'Publicação', generate: 'Geração', simulate: 'Simulação',
  exchange: 'Troca', manual_fill: 'Preenchimento manual',
}
const ACTION_COLOR: Record<string, 'green' | 'yellow' | 'gray' | 'blue'> = {
  create: 'green', update: 'yellow', delete: 'gray',
  publish: 'green', generate: 'blue', manual_fill: 'yellow', exchange: 'blue',
}
const ENTITY_LABEL: Record<string, string> = {
  User: 'Usuário', Profile: 'Perfil', Eligibility: 'Elegibilidade',
  UserGroupLimit: 'Cota individual', Unavailability: 'Indisponibilidade',
  UserPreference: 'Preferência', Schedule: 'Escala', Assignment: 'Atribuição',
  OperationalCalendar: 'Calendário', CalendarDay: 'Dia do calendário', BalanceConfig: 'Config. de saldo',
}

const PAGE = 50

export function AuditoriaPage() {
  const [action, setAction] = useState('')
  const [entity, setEntity] = useState('')
  const [offset, setOffset] = useState(0)

  const { data: rows = [], isLoading, isFetching } = useQuery<AuditEntry[]>({
    queryKey: ['audit', action, entity, offset],
    queryFn: () => api.get('/audit/', {
      params: { limit: PAGE, offset, action: action || undefined, entity_type: entity || undefined },
    }).then((r) => r.data),
  })

  function changeFilter(setter: (v: string) => void, v: string) {
    setter(v); setOffset(0)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Auditoria</h1>
        <p className="text-sm text-gray-500 mt-1">Registro de todas as ações para transparência total.</p>
      </div>

      <Card>
        <CardBody className="py-3">
          <div className="flex flex-wrap items-end gap-3 text-sm">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">Ação</label>
              <select className="rounded-lg border border-gray-300 px-3 py-2 text-sm" value={action} onChange={(e) => changeFilter(setAction, e.target.value)}>
                <option value="">Todas</option>
                {Object.entries(ACTION_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">Entidade</label>
              <select className="rounded-lg border border-gray-300 px-3 py-2 text-sm" value={entity} onChange={(e) => changeFilter(setEntity, e.target.value)}>
                <option value="">Todas</option>
                {Object.entries(ENTITY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Button size="sm" variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>← Recentes</Button>
              <span className="text-xs text-gray-500">{offset + 1}–{offset + rows.length}</span>
              <Button size="sm" variant="secondary" disabled={rows.length < PAGE} onClick={() => setOffset(offset + PAGE)}>Anteriores →</Button>
            </div>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader><p className="font-semibold">Registros {isFetching && <span className="text-xs text-gray-400">(atualizando…)</span>}</p></CardHeader>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-6"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : rows.length === 0 ? (
          <CardBody><p className="text-sm text-gray-500">Nenhum registro para os filtros selecionados.</p></CardBody>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Quando</th>
                  <th className="px-4 py-3 text-left">Quem</th>
                  <th className="px-4 py-3 text-left">Ação</th>
                  <th className="px-4 py-3 text-left">Entidade</th>
                  <th className="px-4 py-3 text-left">Descrição</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 align-top">
                    <td className="px-4 py-3 whitespace-nowrap text-gray-500">
                      {format(new Date(r.created_at), "dd/MM/yy HH:mm", { locale: ptBR })}
                    </td>
                    <td className="px-4 py-3 font-medium">{r.performed_by_name ?? '—'}</td>
                    <td className="px-4 py-3"><Badge label={ACTION_LABEL[r.action] ?? r.action} color={ACTION_COLOR[r.action] ?? 'gray'} /></td>
                    <td className="px-4 py-3 text-gray-600">{ENTITY_LABEL[r.entity_type] ?? r.entity_type}</td>
                    <td className="px-4 py-3 text-gray-700">
                      {r.description || '—'}
                      {(r.previous_value || r.new_value) && (
                        <details className="mt-1">
                          <summary className="text-xs text-primary-600 cursor-pointer">detalhes</summary>
                          <pre className="mt-1 text-[11px] bg-gray-50 rounded p-2 overflow-x-auto">
{r.previous_value ? `antes: ${JSON.stringify(r.previous_value)}\n` : ''}{r.new_value ? `depois: ${JSON.stringify(r.new_value)}` : ''}
                          </pre>
                        </details>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
