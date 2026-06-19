import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { LeaderboardEntry, BalanceConfig } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { InfoTip } from '../../components/ui/InfoTip'

// Campos da configuração, com rótulo e explicação (tooltip)
const SALDO_FIELDS: { key: keyof BalanceConfig; label: string; tip: string }[] = [
  { key: 'avoided_date_assigned', label: 'Data evitada atribuída', tip: 'Pontos quando o perito é escalado numa data que pediu para EVITAR. Positivo = ele foi prejudicado e será poupado depois.' },
  { key: 'month_no_schedule', label: 'Mês sem escala', tip: 'Pontos quando o perito passa o mês sem nenhuma escala. Negativo faz quem não trabalha "ficar devendo" (será escalado mais).' },
  { key: 'desired_date_fulfilled', label: 'Data desejada atendida', tip: 'Pontos quando o perito é escalado numa data que DESEJAVA. Negativo = consome o "crédito" dele.' },
  { key: 'common_schedule', label: 'Turno comum', tip: 'Pontos por um turno comum (nem desejado nem evitado). Normalmente 0.' },
]

const PESO_FIELDS: { key: keyof BalanceConfig; label: string; tip: string }[] = [
  { key: 'weight_gap', label: 'Evitar buracos', tip: 'Quanto o solver evita deixar vaga vazia. Bem alto = quase nunca deixa vaga sem perito (prioridade máxima).' },
  { key: 'weight_balance', label: 'Justiça (saldo)', tip: 'Força da justiça por saldo. Quanto maior, mais o saldo manda na distribuição (poupa quem tem saldo alto).' },
  { key: 'weight_desired', label: 'Atender desejos', tip: 'Força para atender os pedidos de "desejo trabalhar".' },
  { key: 'weight_avoid', label: 'Respeitar "evitar"', tip: 'Força para NÃO escalar em datas marcadas como "prefiro não".' },
  { key: 'weight_load_equity', label: 'Equilíbrio de carga', tip: 'Força para deixar todos com número parecido de turnos (desempate).' },
]

export function SaldoGestorPage() {
  const qc = useQueryClient()

  const { data: leaderboard = [], isLoading } = useQuery<LeaderboardEntry[]>({
    queryKey: ['leaderboard'],
    queryFn: () => api.get('/balance/leaderboard').then((r) => r.data),
  })

  const { data: config } = useQuery<BalanceConfig>({
    queryKey: ['balance-config'],
    queryFn: () => api.get('/balance/config').then((r) => r.data),
  })
  const [form, setForm] = useState<BalanceConfig | null>(null)
  useEffect(() => { if (config) setForm({ ...config }) }, [config])

  const save = useMutation({
    mutationFn: (cfg: BalanceConfig) => api.put('/balance/config', cfg),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['balance-config'] }),
  })

  function field(f: { key: keyof BalanceConfig; label: string; tip: string }) {
    return (
      <div key={f.key} className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600 flex items-center">
          {f.label}<InfoTip text={f.tip} />
        </label>
        <input
          type="number"
          className="w-28 rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          value={form ? form[f.key] : 0}
          onChange={(e) => form && setForm({ ...form, [f.key]: Number(e.target.value) })}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Saldo / Ranking</h1>

      {/* Configuração */}
      <Card>
        <CardHeader>
          <p className="font-semibold flex items-center">
            Regras de distribuição e saldo
            <InfoTip text="Controlam como a escala é distribuída (pesos) e como o saldo de compensação evolui (pontos por evento). Passe o mouse em cada campo." />
          </p>
        </CardHeader>
        <CardBody className="space-y-4">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Pontos de saldo por evento</p>
            <div className="flex flex-wrap gap-4">{SALDO_FIELDS.map(field)}</div>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Prioridade da distribuição (pesos)</p>
            <div className="flex flex-wrap gap-4">{PESO_FIELDS.map(field)}</div>
          </div>
          <div className="flex items-center gap-3">
            <Button size="sm" loading={save.isPending} disabled={!form} onClick={() => form && save.mutate(form)}>
              Salvar configuração
            </Button>
            {save.isSuccess && <span className="text-xs text-green-600">✓ Salvo</span>}
            <span className="text-xs text-gray-400">Vale para as próximas gerações de escala.</span>
          </div>
        </CardBody>
      </Card>

      {/* Ranking */}
      <Card>
        <CardHeader>
          <p className="font-semibold flex items-center">
            Ranking de compensação
            <InfoTip text="Saldo acumulado por perito. Positivo = foi prejudicado (será poupado); negativo = foi poupado (será escalado mais)." />
          </p>
        </CardHeader>
        {isLoading ? (
          <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
        ) : leaderboard.length === 0 ? (
          <div className="px-6 py-4 text-sm text-gray-500">Nenhum dado disponível ainda.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Pos.</th>
                <th className="px-6 py-3 text-left">Usuário</th>
                <th className="px-6 py-3 text-right">Saldo acumulado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {leaderboard.map((entry, i) => (
                <tr key={entry.user_id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-gray-400 font-mono">{i + 1}</td>
                  <td className="px-6 py-3 font-medium">{entry.user_name}</td>
                  <td className={`px-6 py-3 text-right font-mono font-semibold ${entry.cumulative_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.cumulative_balance > 0 ? '+' : ''}{entry.cumulative_balance}
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
