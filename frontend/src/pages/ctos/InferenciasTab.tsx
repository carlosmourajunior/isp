import { useMemo, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/DataTable'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'
import { statusInferenciaStyles } from '@/lib/ctoStatus'
import type { CtoInferencia, CtoRef, InferenciaStatus } from '@/types/ctos'

interface InferenciasTabProps {
  oltId: string
  onSelectCto: (id: number) => void
}

const statusOptions = (Object.keys(statusInferenciaStyles) as InferenciaStatus[]).map((s) => ({
  value: s,
  label: statusInferenciaStyles[s].label,
}))

/** Fila de inferência por ONT - por padrão os divergentes (cadastro a corrigir no IXC). */
export function InferenciasTab({ oltId, onSelectCto }: InferenciasTabProps) {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFiltro, setStatusFiltro] = useState<string>('divergente')
  const [ordering, setOrdering] = useState('pon')

  const { data, isLoading, isFetching } = usePaginatedApi<CtoInferencia>({
    endpoint: '/cto-inferencias/',
    page,
    search,
    ordering,
    filters: { status: statusFiltro, olt: oltId },
  })

  const columns = useMemo<ColumnDef<CtoInferencia, unknown>[]>(() => {
    const ctoCell = (cto: CtoRef | null) =>
      cto ? (
        <button type="button" className="text-primary hover:underline" onClick={() => onSelectCto(cto.id)}>
          {cto.descricao}
        </button>
      ) : (
        <span className="text-muted-foreground">—</span>
      )

    return [
      {
        accessorKey: 'cliente_nome',
        header: 'Cliente',
        meta: { sortKey: 'cliente_nome' },
        cell: ({ row }) => (
          <div>
            <div className="font-medium">{row.original.cliente_nome || '(sem cliente no IXC)'}</div>
            <div className="text-xs text-muted-foreground">{row.original.serial}</div>
          </div>
        ),
      },
      {
        id: 'pon',
        header: 'PON/pos',
        meta: { sortKey: 'pon' },
        cell: ({ row }) => `${row.original.pon}/${row.original.position}`,
      },
      {
        accessorKey: 'distance_km',
        header: 'Dist.',
        meta: { sortKey: 'distance_km' },
        cell: ({ getValue }) => {
          const v = getValue() as number | null
          return v !== null ? `${v.toFixed(1)} km` : '—'
        },
      },
      { id: 'cadastro', header: 'CTO no cadastro', cell: ({ row }) => ctoCell(row.original.cto_cadastro) },
      { id: 'provavel', header: 'CTO provável', cell: ({ row }) => ctoCell(row.original.cto_provavel) },
      {
        accessorKey: 'status',
        header: 'Status',
        meta: { sortKey: 'status' },
        cell: ({ getValue }) => {
          const s = statusInferenciaStyles[getValue() as InferenciaStatus]
          return <Badge variant={s.badge}>{s.label}</Badge>
        },
      },
      {
        id: 'motivo',
        header: 'Por quê',
        cell: ({ row }) => {
          const m = row.original.motivos
          const texto = (row.original.status === 'divergente' ? m.cadastro : m.provavel) ?? []
          return (
            <span className="block max-w-md truncate text-xs text-muted-foreground" title={texto.join('; ')}>
              {texto.join('; ') || '—'}
            </span>
          )
        },
      },
    ]
  }, [onSelectCto])

  return (
    <DataTable
      columns={columns}
      data={data?.results ?? []}
      isLoading={isLoading}
      isFetching={isFetching}
      searchValue={search}
      onSearchChange={(v) => {
        setSearch(v)
        setPage(1)
      }}
      searchPlaceholder="Buscar cliente, serial ou CTO…"
      page={page}
      onPageChange={setPage}
      count={data?.count}
      ordering={ordering}
      onOrderingChange={(v) => {
        setOrdering(v)
        setPage(1)
      }}
      emptyMessage="Nenhuma ONT nesse status."
      toolbar={
        <SelectFilter
          label="Status"
          value={statusFiltro}
          options={statusOptions}
          onChange={(v) => {
            setStatusFiltro(v)
            setPage(1)
          }}
        />
      }
    />
  )
}
