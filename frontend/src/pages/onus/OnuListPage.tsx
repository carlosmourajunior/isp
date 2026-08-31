import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { Info, RotateCw, Trash2 } from 'lucide-react'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { ConfirmDialog, useConfirmDialog } from '@/components/ConfirmDialog'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'
import { useOnuActions } from '@/hooks/useOnuActions'
import { signalStatus, statusStyles } from '@/lib/status'
import type { Onu } from '@/types/api'

/** `live` acrescenta o ponto pulsante (só faz sentido pro estado operacional, não admin). */
function StateBadge({ state, live }: { state: string; live?: boolean }) {
  const normalized = state?.toLowerCase()
  if (normalized === 'up') {
    return (
      <Badge variant="success" className="gap-1.5">
        {live && (
          <span
            className="status-dot-live inline-block size-1.5 rounded-full"
            style={{ color: statusStyles.good.dot }}
          />
        )}
        up
      </Badge>
    )
  }
  if (normalized === 'down') return <Badge variant="destructive">down</Badge>
  return <Badge variant="outline">{state || '—'}</Badge>
}

function SignalValue({ dbm }: { dbm: number | null | undefined }) {
  if (dbm === null || dbm === undefined) return <span className="font-data">—</span>
  const level = signalStatus(dbm)
  const style = statusStyles[level]
  return (
    <span className="font-data" style={level === 'good' ? undefined : { color: style.dot }}>
      {dbm}
    </span>
  )
}

interface OnuListPageProps {
  title: string
  description: string
  endpoint: string
  filters?: Record<string, string>
  emptyMessage?: string
  /** Mostra os dropdowns de Admin/Oper/Cliente Fibra - só faz sentido quando `filters` não já fixa esses campos. */
  showQuickFilters?: boolean
}

export function OnuListPage({
  title,
  description,
  endpoint,
  filters,
  emptyMessage,
  showQuickFilters,
}: OnuListPageProps) {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [adminState, setAdminState] = useState('')
  const [operState, setOperState] = useState('')
  const [clienteFibra, setClienteFibra] = useState('')

  const combinedFilters = showQuickFilters
    ? { ...filters, admin_state: adminState, oper_state: operState, cliente_fibra: clienteFibra }
    : filters

  const { data, isLoading, isFetching } = usePaginatedApi<Onu>({
    endpoint,
    page,
    search,
    filters: combinedFilters,
  })
  const { removeOnu, resetOnu } = useOnuActions()

  const removeDialog = useConfirmDialog<Onu>()
  const resetDialog = useConfirmDialog<Onu>()

  function onuTarget(onu: Onu) {
    return { slot: onu.slot ?? 0, port: onu.port ?? 0, position: onu.position }
  }

  const columns = useMemo<ColumnDef<Onu, unknown>[]>(
    () => [
      { accessorKey: 'pon', header: 'PON', cell: ({ getValue }) => <span className="font-data">{getValue() as string}</span> },
      { accessorKey: 'position', header: 'Posição' },
      { accessorKey: 'serial', header: 'Serial', cell: ({ getValue }) => <span className="font-data">{getValue() as string}</span> },
      {
        accessorKey: 'mac',
        header: 'MAC',
        cell: ({ getValue }) => <span className="font-data">{(getValue() as string) || '—'}</span>,
      },
      {
        accessorKey: 'admin_state',
        header: 'Admin',
        cell: ({ getValue }) => <StateBadge state={getValue() as string} />,
      },
      {
        accessorKey: 'oper_state',
        header: 'Oper',
        cell: ({ getValue }) => <StateBadge state={getValue() as string} live />,
      },
      {
        accessorKey: 'olt_rx_sig',
        header: 'Sinal (dBm)',
        cell: ({ getValue }) => <SignalValue dbm={getValue() as number | null} />,
      },
      { accessorKey: 'desc1', header: 'Descrição' },
      {
        accessorKey: 'cliente_fibra',
        header: 'Cliente Fibra',
        cell: ({ getValue }) =>
          getValue() ? <Badge variant="success">Sim</Badge> : <Badge variant="outline">Não</Badge>,
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => {
          const onu = row.original
          return (
            <div className="flex items-center justify-end gap-1">
              <Link
                to={`/onus/porta/${onu.slot}/${onu.port}`}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                title="Detalhes da porta"
              >
                <Info className="size-4" />
              </Link>
              <button
                onClick={() => resetDialog.open(onu)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                title="Reiniciar ONU"
              >
                <RotateCw className="size-4" />
              </button>
              <button
                onClick={() => removeDialog.open(onu)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="Remover ONU"
              >
                <Trash2 className="size-4" />
              </button>
            </div>
          )
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  return (
    <div>
      <PageHeader title={title} description={description} />

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        isFetching={isFetching}
        searchValue={search}
        onSearchChange={(value) => {
          setSearch(value)
          setPage(1)
        }}
        searchPlaceholder="Buscar por serial, MAC, descrição, PON…"
        page={page}
        onPageChange={setPage}
        count={data?.count}
        emptyMessage={emptyMessage}
        toolbar={
          showQuickFilters && (
            <div className="flex flex-wrap gap-2">
              <SelectFilter
                label="Admin"
                value={adminState}
                onChange={(v) => {
                  setAdminState(v)
                  setPage(1)
                }}
                options={[
                  { label: 'up', value: 'up' },
                  { label: 'down', value: 'down' },
                ]}
              />
              <SelectFilter
                label="Oper"
                value={operState}
                onChange={(v) => {
                  setOperState(v)
                  setPage(1)
                }}
                options={[
                  { label: 'up', value: 'up' },
                  { label: 'down', value: 'down' },
                ]}
              />
              <SelectFilter
                label="Cliente Fibra"
                value={clienteFibra}
                onChange={(v) => {
                  setClienteFibra(v)
                  setPage(1)
                }}
                options={[
                  { label: 'Sim', value: 'true' },
                  { label: 'Não', value: 'false' },
                ]}
              />
            </div>
          )
        }
      />

      <ConfirmDialog
        open={resetDialog.isOpen}
        title="Reiniciar ONU?"
        description={
          resetDialog.target && (
            <>
              A ONU <span className="font-medium text-foreground">{resetDialog.target.serial}</span> ({resetDialog.target.pon}/{resetDialog.target.position}) será reiniciada agora.
            </>
          )
        }
        confirmLabel="Reiniciar"
        isLoading={resetOnu.isPending}
        onCancel={resetDialog.close}
        onConfirm={() => {
          if (!resetDialog.target) return
          resetOnu.mutate(onuTarget(resetDialog.target), { onSettled: resetDialog.close })
        }}
      />

      <ConfirmDialog
        open={removeDialog.isOpen}
        title="Remover ONU?"
        description={
          removeDialog.target && (
            <>
              A ONU <span className="font-medium text-foreground">{removeDialog.target.serial}</span> ({removeDialog.target.pon}/{removeDialog.target.position}) será removida da OLT e do banco de dados. Essa ação não pode ser desfeita.
            </>
          )
        }
        confirmLabel="Remover"
        confirmVariant="destructive"
        isLoading={removeOnu.isPending}
        onCancel={removeDialog.close}
        onConfirm={() => {
          if (!removeDialog.target) return
          removeOnu.mutate(onuTarget(removeDialog.target), { onSettled: removeDialog.close })
        }}
      />
    </div>
  )
}
