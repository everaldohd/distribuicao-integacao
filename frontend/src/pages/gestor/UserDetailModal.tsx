/**
 * Modal de detalhe do perito (gestor), aberto ao clicar numa linha de Usuários.
 * Permite, com salvamento automático: escolher o perfil, marcar elegibilidades,
 * ajustar a cota por grupo (o que move o perito para "Personalizado") e registrar férias.
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { User, Profile, EligibilityItem, Unavailability, UnavailabilityType, ScheduleGroup, UserLimits } from '../../lib/types'
import { Button } from '../../components/ui/Button'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const TIPO_LABEL: Record<UnavailabilityType, string> = {
  vacation: 'Férias',
  bonus_leave: 'Abono',
  license: 'Licença',
}

interface Props {
  user: User
  onClose: () => void
}

export function UserDetailModal({ user, onClose }: Props) {
  const qc = useQueryClient()

  // --- Perfil ---
  const { data: profiles = [] } = useQuery<Profile[]>({
    queryKey: ['profiles'],
    queryFn: () => api.get('/profiles/').then((r) => r.data),
  })
  const [profileId, setProfileId] = useState<string>(user.profile_id ?? '')

  const saveProfile = useMutation({
    mutationFn: (pid: string) => api.put(`/users/${user.id}`, { profile_id: pid || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      qc.invalidateQueries({ queryKey: ['user-limits', user.id] })
    },
  })
  function changeProfile(pid: string) {
    setProfileId(pid)
    saveProfile.mutate(pid)
  }

  // --- Limites por grupo (cota máxima) ---
  const { data: groups = [] } = useQuery<ScheduleGroup[]>({
    queryKey: ['groups'],
    queryFn: () => api.get('/profiles/groups').then((r) => r.data),
  })
  const { data: userLimits } = useQuery<UserLimits>({
    queryKey: ['user-limits', user.id],
    queryFn: () => api.get(`/users/${user.id}/limits`).then((r) => r.data),
  })
  const [limits, setLimits] = useState<Record<string, number>>({})
  useEffect(() => { if (userLimits) setLimits({ ...userLimits.limits }) }, [userLimits])

  const saveLimits = useMutation({
    mutationFn: (lim: Record<string, number>) => api.put(`/users/${user.id}/limits`, { limits: lim }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      qc.invalidateQueries({ queryKey: ['user-limits', user.id] })
    },
  })

  // --- Elegibilidades ---
  const { data: eligibilities = [] } = useQuery<EligibilityItem[]>({
    queryKey: ['eligibilities', user.id],
    queryFn: () => api.get(`/users/${user.id}/eligibilities`).then((r) => r.data),
  })
  const [eligIds, setEligIds] = useState<Set<string>>(new Set())
  useEffect(() => {
    setEligIds(new Set(eligibilities.filter((e) => e.is_eligible).map((e) => e.schedule_type_id)))
  }, [eligibilities])

  const saveElig = useMutation({
    mutationFn: (ids: string[]) => api.put(`/users/${user.id}/eligibilities`, { eligible_type_ids: ids }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['eligibilities', user.id] }),
  })

  // --- Férias / indisponibilidades ---
  const { data: unavs = [] } = useQuery<Unavailability[]>({
    queryKey: ['unavailabilities', user.id],
    queryFn: () => api.get(`/users/${user.id}/unavailabilities`).then((r) => r.data),
  })
  const [vac, setVac] = useState({ type: 'vacation' as UnavailabilityType, start_date: '', end_date: '', notes: '' })

  const addVac = useMutation({
    mutationFn: () => api.post(`/users/${user.id}/unavailabilities`, vac),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unavailabilities', user.id] })
      setVac({ type: 'vacation', start_date: '', end_date: '', notes: '' })
    },
  })
  const removeVac = useMutation({
    mutationFn: (vid: string) => api.delete(`/users/${user.id}/unavailabilities/${vid}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unavailabilities', user.id] }),
  })

  function toggleElig(id: string) {
    setEligIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      saveElig.mutate([...next])
      return next
    })
  }

  const fmt = (d: string) => format(new Date(d + 'T00:00:00'), 'dd/MM/yyyy', { locale: ptBR })

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-5">
          <div>
            <p className="font-bold text-lg text-gray-900">{user.name}</p>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        </div>

        {/* Perfil */}
        <section className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Perfil de distribuição</h3>
            <span className="text-xs">
              {saveProfile.isPending ? <span className="text-gray-400">Salvando…</span>
                : saveProfile.isError ? <span className="text-red-600">Erro ao salvar</span>
                : saveProfile.isSuccess ? <span className="text-green-600">✓ Salvo</span> : null}
            </span>
          </div>
          <select
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={profileId}
            onChange={(e) => changeProfile(e.target.value)}
          >
            <option value="">Sem perfil</option>
            {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <p className="mt-1 text-xs text-gray-400">A alteração é salva automaticamente.</p>
        </section>

        {/* Limites de cota por grupo */}
        <section className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Limite máximo por grupo (no mês)</h3>
            <span className="text-xs">
              {saveLimits.isPending ? <span className="text-gray-400">Salvando…</span>
                : saveLimits.isSuccess ? <span className="text-green-600">✓ Salvo</span> : null}
            </span>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            {groups.map((g) => (
              <div key={g.group_name} className="flex flex-col gap-1">
                <label className="text-xs font-medium text-gray-600">{g.group_name}</label>
                <input
                  type="number" min={0}
                  className="w-20 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-center"
                  value={limits[g.group_name] ?? 0}
                  onChange={(e) => setLimits({ ...limits, [g.group_name]: Number(e.target.value) })}
                />
              </div>
            ))}
            <Button size="sm" loading={saveLimits.isPending} onClick={() => saveLimits.mutate(limits)}>
              Aplicar limites
            </Button>
          </div>
          <p className="mt-1 text-xs text-gray-400">
            {userLimits?.is_custom
              ? 'Perfil Personalizado — limites individuais deste perito.'
              : `Vindo do perfil "${userLimits?.profile_name ?? '—'}". Ao aplicar, o perito passa a Personalizado.`}
          </p>
        </section>

        {/* Elegibilidades */}
        <section className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Tipos de escala que pode fazer</h3>
            <span className="text-xs">
              {saveElig.isPending ? <span className="text-gray-400">Salvando…</span>
                : saveElig.isError ? <span className="text-red-600">Erro ao salvar</span>
                : saveElig.isSuccess ? <span className="text-green-600">✓ Salvo</span> : null}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {eligibilities.map((e) => (
              <label key={e.schedule_type_id} className="flex items-center gap-2 text-sm cursor-pointer rounded-lg border border-gray-200 px-3 py-2 hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={eligIds.has(e.schedule_type_id)}
                  onChange={() => toggleElig(e.schedule_type_id)}
                  className="rounded"
                />
                {e.schedule_type_name}
              </label>
            ))}
          </div>
          <p className="mt-1 text-xs text-gray-400">Marque/desmarque — salva automaticamente.</p>
        </section>

        {/* Férias */}
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Férias / Indisponibilidades</h3>

          {unavs.length === 0 ? (
            <p className="text-xs text-gray-400 mb-3">Nenhum período cadastrado.</p>
          ) : (
            <ul className="mb-3 space-y-1">
              {unavs.map((u) => (
                <li key={u.id} className="flex items-center justify-between text-sm rounded-lg bg-gray-50 px-3 py-2">
                  <span>
                    <span className="font-medium">{TIPO_LABEL[u.type]}</span>{' '}
                    <span className="text-gray-600">{fmt(u.start_date)} → {fmt(u.end_date)}</span>
                    {u.notes && <span className="text-gray-400 italic"> · {u.notes}</span>}
                  </span>
                  <button
                    onClick={() => removeVac.mutate(u.id)}
                    className="text-red-500 hover:text-red-700 text-xs font-medium"
                  >
                    Remover
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="rounded-lg border border-gray-200 p-3 space-y-2">
            <div className="flex gap-2">
              <select
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
                value={vac.type}
                onChange={(e) => setVac({ ...vac, type: e.target.value as UnavailabilityType })}
              >
                <option value="vacation">Férias</option>
                <option value="bonus_leave">Abono</option>
                <option value="license">Licença</option>
              </select>
              <input
                type="date"
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm flex-1"
                value={vac.start_date}
                onChange={(e) => setVac({ ...vac, start_date: e.target.value })}
              />
              <span className="self-center text-gray-400">→</span>
              <input
                type="date"
                className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm flex-1"
                value={vac.end_date}
                onChange={(e) => setVac({ ...vac, end_date: e.target.value })}
              />
            </div>
            <input
              type="text"
              placeholder="Observação (opcional)"
              className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
              value={vac.notes}
              onChange={(e) => setVac({ ...vac, notes: e.target.value })}
            />
            <Button
              size="sm"
              loading={addVac.isPending}
              disabled={!vac.start_date || !vac.end_date}
              onClick={() => addVac.mutate()}
            >
              + Adicionar período
            </Button>
            {addVac.isError && <p className="text-xs text-red-600">Erro ao adicionar (verifique as datas).</p>}
          </div>
        </section>

        <div className="mt-6 flex justify-end">
          <Button variant="secondary" onClick={onClose}>Fechar</Button>
        </div>
      </div>
    </div>
  )
}
