import { useMemo, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Server, Trash2 } from 'lucide-react'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { ConfirmDialog, useConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'
import { OLT_VENDOR_LABELS, type Olt, type OltFormValues, type OltVendor } from '@/types/api'

const DEVICE_TYPE_BY_VENDOR: Record<OltVendor, string> = {
  nokia_alcatel: 'alcatel_aos',
}

const EMPTY_FORM: OltFormValues = {
  name: '',
  vendor: 'nokia_alcatel',
  device_type: DEVICE_TYPE_BY_VENDOR.nokia_alcatel,
  host: '',
  username: '',
  password: '',
  ssh_port: 22,
  slot_count: 2,
  is_active: true,
}

function OltFormDialog({
  open,
  editing,
  onClose,
}: {
  open: boolean
  editing: Olt | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [values, setValues] = useState<OltFormValues>(EMPTY_FORM)

  // Reabre o formulário sempre limpo (criar) ou preenchido (editar) - sem useEffect,
  // a key no componente pai (ver render abaixo) já força a remontagem.
  useMemo(() => {
    setValues(
      editing
        ? {
            name: editing.name,
            vendor: editing.vendor,
            device_type: editing.device_type,
            host: editing.host,
            username: editing.username,
            password: '',
            ssh_port: editing.ssh_port,
            slot_count: editing.slot_count,
            is_active: editing.is_active,
          }
        : EMPTY_FORM,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing])

  function invalidateOlts() {
    queryClient.invalidateQueries({
      predicate: (query) => typeof query.queryKey[0] === 'string' && query.queryKey[0] === '/olts/',
    })
  }

  const save = useMutation({
    mutationFn: (payload: OltFormValues) => {
      const body: Partial<OltFormValues> = { ...payload }
      if (editing && !body.password) delete body.password
      return editing ? api.patch(`/olts/${editing.id}/`, body) : api.post('/olts/', body)
    },
    onSuccess: () => {
      toast.success(editing ? 'OLT atualizada com sucesso' : 'OLT cadastrada com sucesso')
      invalidateOlts()
      onClose()
    },
    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: Record<string, string[]> } })?.response?.data
      const firstError = detail && Object.values(detail).flat()[0]
      toast.error('Erro ao salvar OLT', firstError || 'Verifique os dados e se você tem permissão de administrador.')
    },
  })

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <form
        className="relative flex w-full max-w-md flex-col gap-4 rounded-xl border border-border bg-card p-5 shadow-lg"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(values)
        }}
      >
        <h2 className="text-base font-semibold text-foreground">{editing ? 'Editar OLT' : 'Nova OLT'}</h2>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Nome</span>
          <Input
            required
            value={values.name}
            onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
            placeholder="Ex: OLT 2 - Bairro Norte"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Fabricante</span>
          <select
            value={values.vendor}
            onChange={(e) => {
              const vendor = e.target.value as OltVendor
              setValues((v) => ({ ...v, vendor, device_type: DEVICE_TYPE_BY_VENDOR[vendor] }))
            }}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {Object.entries(OLT_VENDOR_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <div className="grid grid-cols-3 gap-3">
          <label className="col-span-2 flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground">Host / IP</span>
            <Input
              required
              value={values.host}
              onChange={(e) => setValues((v) => ({ ...v, host: e.target.value }))}
              placeholder="192.168.1.1"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground">Porta SSH</span>
            <Input
              required
              type="number"
              value={values.ssh_port}
              onChange={(e) => setValues((v) => ({ ...v, ssh_port: Number(e.target.value) }))}
            />
          </label>
        </div>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Usuário SSH</span>
          <Input
            required
            value={values.username}
            onChange={(e) => setValues((v) => ({ ...v, username: e.target.value }))}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">
            Senha SSH {editing && <span className="text-xs">(deixe em branco para manter a atual)</span>}
          </span>
          <Input
            type="password"
            required={!editing}
            value={values.password}
            onChange={(e) => setValues((v) => ({ ...v, password: e.target.value }))}
            placeholder={editing ? '••••••••' : ''}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Quantidade de slots</span>
          <Input
            required
            type="number"
            min={1}
            value={values.slot_count}
            onChange={(e) => setValues((v) => ({ ...v, slot_count: Number(e.target.value) }))}
          />
          <span className="text-xs text-muted-foreground">
            Maior slot físico da OLT, mesmo que nem todos estejam instalados hoje — define até onde o sistema varre a OLT.
          </span>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={values.is_active}
            onChange={(e) => setValues((v) => ({ ...v, is_active: e.target.checked }))}
            className="size-4 rounded border-input"
          />
          <span className="text-foreground">Ativa</span>
        </label>

        <div className="mt-1 flex justify-end gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={save.isPending}>
            Cancelar
          </Button>
          <Button type="submit" size="sm" disabled={save.isPending}>
            {save.isPending ? 'Salvando…' : 'Salvar'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export function OltsPage() {
  const [page, setPage] = useState(1)
  const [ordering, setOrdering] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Olt | null>(null)
  const deleteDialog = useConfirmDialog<Olt>()
  const queryClient = useQueryClient()
  const toast = useToast()

  const { data, isLoading, isFetching } = usePaginatedApi<Olt>({ endpoint: '/olts/', page, ordering })

  const remove = useMutation({
    mutationFn: (olt: Olt) => api.delete(`/olts/${olt.id}/`),
    onSuccess: () => {
      toast.success('OLT removida com sucesso')
      queryClient.invalidateQueries({
        predicate: (query) => typeof query.queryKey[0] === 'string' && query.queryKey[0] === '/olts/',
      })
    },
    onError: () => toast.error('Erro ao remover OLT', 'Verifique se você tem permissão de administrador.'),
  })

  function openCreate() {
    setEditing(null)
    setFormOpen(true)
  }

  function openEdit(olt: Olt) {
    setEditing(olt)
    setFormOpen(true)
  }

  const columns = useMemo<ColumnDef<Olt, unknown>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'Nome',
        meta: { sortKey: 'name' },
        cell: ({ row }) => (
          <span className="flex items-center gap-2 font-medium text-foreground">
            <Server className="size-3.5 text-muted-foreground" />
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: 'vendor',
        header: 'Fabricante',
        meta: { sortKey: 'vendor' },
        cell: ({ getValue }) => OLT_VENDOR_LABELS[getValue() as OltVendor],
      },
      {
        id: 'host',
        header: 'Host',
        meta: { sortKey: 'host' },
        cell: ({ row }) => <span className="font-data">{row.original.host}:{row.original.ssh_port}</span>,
      },
      { accessorKey: 'slot_count', header: 'Slots', meta: { sortKey: 'slot_count' } },
      {
        accessorKey: 'is_active',
        header: 'Status',
        meta: { sortKey: 'is_active' },
        cell: ({ getValue }) =>
          getValue() ? <Badge variant="success">Ativa</Badge> : <Badge variant="outline">Inativa</Badge>,
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <button
              onClick={() => openEdit(row.original)}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              title="Editar OLT"
            >
              <Pencil className="size-4" />
            </button>
            <button
              onClick={() => deleteDialog.open(row.original)}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              title="Remover OLT"
            >
              <Trash2 className="size-4" />
            </button>
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  return (
    <div>
      <PageHeader
        title="OLTs"
        description="OLTs cadastradas no sistema. As credenciais de acesso SSH ficam criptografadas no banco."
        action={
          <Button size="sm" onClick={openCreate}>
            <Plus className="size-4" />
            Nova OLT
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        isFetching={isFetching}
        page={page}
        onPageChange={setPage}
        count={data?.count}
        emptyMessage="Nenhuma OLT cadastrada ainda."
        ordering={ordering}
        onOrderingChange={(value) => {
          setOrdering(value)
          setPage(1)
        }}
      />

      {formOpen && (
        <OltFormDialog
          key={editing?.id ?? 'new'}
          open={formOpen}
          editing={editing}
          onClose={() => setFormOpen(false)}
        />
      )}

      <ConfirmDialog
        open={deleteDialog.isOpen}
        title="Remover OLT?"
        description={
          deleteDialog.target && (
            <>
              A OLT <span className="font-medium text-foreground">{deleteDialog.target.name}</span> será removida.
              Todo o histórico de ONUs, portas e sensores ligados a ela também será apagado (a remoção é em cascata).
              Essa ação não pode ser desfeita.
            </>
          )
        }
        confirmLabel="Remover"
        confirmVariant="destructive"
        isLoading={remove.isPending}
        onCancel={deleteDialog.close}
        onConfirm={() => {
          if (!deleteDialog.target) return
          remove.mutate(deleteDialog.target, { onSettled: deleteDialog.close })
        }}
      />
    </div>
  )
}
