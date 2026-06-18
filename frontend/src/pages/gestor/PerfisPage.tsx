/**
 * Perfis & Regras (gestor).
 * Configura a cota MÁXIMA por grupo (Plantão/Reserva/Pátio) de cada perfil,
 * permite criar/excluir perfis e ajustar o fator do limite de preferências.
 * Perfis do sistema (is_system) não podem ser excluídos; o Personalizado é por perito.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Profile, ScheduleGroup } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'

function limitOf(p: Profile, group: string): number {
  return p.group_limits.find((g) => g.group_name === group)?.max_quantity ?? 0
}

export function PerfisPage() {
  const qc = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [newProfile, setNewProfile] = useState<{ name: string; limits: Record<string, number> }>({ name: '', limits: {} })

  const { data: groups = [] } = useQuery<ScheduleGroup[]>({
    queryKey: ['groups'],
    queryFn: () => api.get('/profiles/groups').then((r) => r.data),
  })

  // Fator de preferências (limite de dias = cota do grupo × fator)
  const { data: prefCfg } = useQuery<{ preference_factor: number }>({
    queryKey: ['pref-config'],
    queryFn: () => api.get('/preferences/config').then((r) => r.data),
  })
  const [factor, setFactor] = useState<number | null>(null)
  const factorValue = factor ?? prefCfg?.preference_factor ?? 2
  const saveFactor = useMutation({
    mutationFn: (f: number) => api.put('/preferences/config', { preference_factor: f }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pref-config'] }),
  })

  // Antecedência mínima de troca
  const { data: exCfg } = useQuery<{ min_lead_days: number }>({
    queryKey: ['ex-config'],
    queryFn: () => api.get('/exchanges/config').then((r) => r.data),
  })
  const [lead, setLead] = useState<number | null>(null)
  const leadValue = lead ?? exCfg?.min_lead_days ?? 3
  const saveLead = useMutation({
    mutationFn: (d: number) => api.put('/exchanges/config', { min_lead_days: d }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ex-config'] }),
  })
  const { data: profiles = [], isLoading } = useQuery<Profile[]>({
    queryKey: ['profiles'],
    queryFn: () => api.get('/profiles/').then((r) => r.data),
  })

  const save = useMutation({
    mutationFn: (p: { id: string; name: string; limits: Record<string, number> }) =>
      api.put(`/profiles/${p.id}`, { name: p.name, limits: p.limits }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles'] }),
  })
  const create = useMutation({
    mutationFn: (p: { name: string; limits: Record<string, number> }) => api.post('/profiles/', p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profiles'] })
      setCreating(false)
      setNewProfile({ name: '', limits: {} })
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/profiles/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profiles'] }),
  })

  // Estado local editável dos limites por perfil
  const [edited, setEdited] = useState<Record<string, Record<string, number>>>({})
  function getLimit(p: Profile, group: string): number {
    return edited[p.id]?.[group] ?? limitOf(p, group)
  }
  function setLimit(p: Profile, group: string, value: number) {
    setEdited((prev) => ({ ...prev, [p.id]: { ...(prev[p.id] ?? {}), [group]: value } }))
  }
  function saveProfile(p: Profile) {
    const limits: Record<string, number> = {}
    groups.forEach((g) => { limits[g.group_name] = getLimit(p, g.group_name) })
    save.mutate({ id: p.id, name: p.name, limits })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Perfis &amp; Regras de cota</h1>
          <p className="text-sm text-gray-500 mt-1">Limite máximo de cada grupo por perito, por mês.</p>
        </div>
        <Button onClick={() => setCreating(!creating)}>{creating ? 'Cancelar' : '+ Novo perfil'}</Button>
      </div>

      {/* Legenda dos grupos */}
      <Card>
        <CardBody className="py-3">
          <div className="flex flex-wrap gap-4 text-xs text-gray-600">
            <span className="font-semibold text-gray-700">Grupos:</span>
            {groups.map((g) => (
              <span key={g.group_name}>
                <span className="font-medium">{g.group_name}</span>
                {' = '}
                {g.types.map((t) => `${t.name}${t.weight > 1 ? ` (conta ${t.weight})` : ''}`).join(', ')}
              </span>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Fator de preferências */}
      <Card>
        <CardBody className="py-3">
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="font-semibold text-gray-700">Limite de dias de preferência:</span>
            <span className="text-gray-500">cota do grupo ×</span>
            <input
              type="number" min={0}
              className="w-16 rounded-lg border border-gray-300 px-2 py-1 text-center"
              value={factorValue}
              onChange={(e) => setFactor(Number(e.target.value))}
            />
            <Button size="sm" loading={saveFactor.isPending} onClick={() => saveFactor.mutate(factorValue)}>Salvar fator</Button>
            <span className="text-xs text-gray-400">Ex.: fator 2 → grupo com cota 2 permite até 4 dias de preferência (desejo e evitar contam separado).</span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm mt-3 pt-3 border-t border-gray-100">
            <span className="font-semibold text-gray-700">Antecedência mínima de troca:</span>
            <input
              type="number" min={0}
              className="w-16 rounded-lg border border-gray-300 px-2 py-1 text-center"
              value={leadValue}
              onChange={(e) => setLead(Number(e.target.value))}
            />
            <span className="text-gray-500">dia(s)</span>
            <Button size="sm" loading={saveLead.isPending} onClick={() => saveLead.mutate(leadValue)}>Salvar antecedência</Button>
            <span className="text-xs text-gray-400">Trocas só podem envolver turnos a pelo menos N dias no futuro.</span>
          </div>
        </CardBody>
      </Card>

      {creating && (
        <Card>
          <CardHeader><p className="font-semibold">Novo perfil</p></CardHeader>
          <CardBody>
            <div className="flex flex-wrap items-end gap-4">
              <Input label="Nome do perfil" value={newProfile.name} onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })} />
              {groups.map((g) => (
                <div key={g.group_name} className="flex flex-col gap-1">
                  <label className="text-sm font-medium text-gray-700">{g.group_name}</label>
                  <input
                    type="number" min={0}
                    className="w-20 rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    value={newProfile.limits[g.group_name] ?? 0}
                    onChange={(e) => setNewProfile({ ...newProfile, limits: { ...newProfile.limits, [g.group_name]: Number(e.target.value) } })}
                  />
                </div>
              ))}
              <Button loading={create.isPending} disabled={!newProfile.name} onClick={() => create.mutate(newProfile)}>Criar</Button>
            </div>
          </CardBody>
        </Card>
      )}

      <Card>
        {isLoading ? (
          <CardBody><div className="flex justify-center py-6"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div></CardBody>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Perfil</th>
                {groups.map((g) => <th key={g.group_name} className="px-4 py-3 text-center">{g.group_name}</th>)}
                <th className="px-6 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {profiles.map((p) => {
                const isDirty = !!edited[p.id] && groups.some((g) => getLimit(p, g.group_name) !== limitOf(p, g.group_name))
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium">
                      {p.name}
                      {p.is_default && <Badge label="padrão" color="blue" />}
                      {p.is_custom && <Badge label="por perito" color="yellow" />}
                    </td>
                    {groups.map((g) => (
                      <td key={g.group_name} className="px-4 py-3 text-center">
                        {p.is_custom ? (
                          <span className="text-gray-300">—</span>
                        ) : (
                          <input
                            type="number" min={0}
                            className="w-16 rounded-lg border border-gray-300 px-2 py-1 text-sm text-center"
                            value={getLimit(p, g.group_name)}
                            onChange={(e) => setLimit(p, g.group_name, Number(e.target.value))}
                          />
                        )}
                      </td>
                    ))}
                    <td className="px-6 py-3 text-right whitespace-nowrap">
                      {!p.is_custom && (
                        <Button size="sm" disabled={!isDirty} loading={save.isPending && save.variables?.id === p.id} onClick={() => saveProfile(p)}>
                          Salvar
                        </Button>
                      )}
                      {!p.is_system && (
                        <button onClick={() => remove.mutate(p.id)} className="ml-2 text-xs text-red-500 hover:text-red-700">Excluir</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
