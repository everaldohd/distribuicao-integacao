import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { User } from '../../lib/types'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'

export function UsuariosPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', is_manager: false })

  const { data: users = [], isLoading } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: () => api.get('/users/').then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/users/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setForm({ name: '', email: '', password: '', is_manager: false })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Usuários</h1>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancelar' : '+ Novo usuário'}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><p className="font-semibold">Novo usuário</p></CardHeader>
          <CardBody>
            <form
              className="grid grid-cols-2 gap-4"
              onSubmit={(e) => { e.preventDefault(); create.mutate(form) }}
            >
              <Input label="Nome" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <Input label="E-mail" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              <Input label="Senha" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input type="checkbox" checked={form.is_manager} onChange={(e) => setForm({ ...form, is_manager: e.target.checked })} className="rounded" />
                  É gestor
                </label>
              </div>
              <div className="col-span-2 flex justify-end gap-2">
                <Button type="submit" loading={create.isPending}>Criar usuário</Button>
              </div>
              {create.isError && <p className="col-span-2 text-sm text-red-600">Erro ao criar usuário.</p>}
            </form>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader><p className="font-semibold">Todos os usuários</p></CardHeader>
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-6 py-3 text-left">Nome</th>
                  <th className="px-6 py-3 text-left">E-mail</th>
                  <th className="px-6 py-3 text-left">Papel</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium">{u.name}</td>
                    <td className="px-6 py-3 text-gray-500">{u.email}</td>
                    <td className="px-6 py-3">
                      <Badge label={u.is_manager ? 'Gestor' : 'Usuário'} color={u.is_manager ? 'blue' : 'gray'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  )
}
