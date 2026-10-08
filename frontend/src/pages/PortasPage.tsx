import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { Info } from 'lucide-react'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'
import { useOlts } from '@/hooks/useOlts'
import type { OltUser } from '@/types/api'

export function PortasPage() {
  const [page, setPage] = useState(1)
  const [slot, setSlot] = useState('')
  const [olt, setOlt] = useState('')
  const [ordering, setOrdering] = useState('-users_connected')

  const { data: olts } = useOlts()
  const showOltFilter = (olts?.length ?? 0) > 1

  // Slots possíveis: só os da OLT selecionada no filtro, ou a maior capacidade
  // entre as OLTs ativas quando nenhuma está selecionada - nunca um número fixo,
  // já que cada OLT declara sua própria quantidade de slots (Olt.slot_count).
  const maxSlots = olt
    ? (olts ?? []).find((o) => String(o.id) === olt)?.slot_count ?? 1
    : Math.max(1, ...(olts ?? []).map((o) => o.slot_count))
  const slotOptions = Array.from({ length: maxSlots }, (_, i) => ({
    label: String(i + 1),
    value: String(i + 1),
  }))

  const { data, isLoading, isFetching } = usePaginatedApi<OltUser>({
    endpoint: '/olt-users/',
    page,
    ordering,
    filters: { slot, olt },
  })

  const columns = useMemo<ColumnDef<OltUser, unknown>[]>(
    () => [
      ...(showOltFilter
        ? [
            {
              accessorKey: 'olt_name',
              header: 'OLT',
              meta: { sortKey: 'olt__name' },
              cell: ({ getValue }: { getValue: () => unknown }) => (getValue() as string) || '—',
            } satisfies ColumnDef<OltUser, unknown>,
          ]
        : []),
      {
        id: 'porta',
        header: 'Porta',
        meta: { sortKey: 'slot' },
        cell: ({ row }) => `1/1/${row.original.slot}/${row.original.port}`,
      },
      { accessorKey: 'users_connected', header: 'Usuários', meta: { sortKey: 'users_connected' } },
      {
        accessorKey: 'last_updated',
        header: 'Atualizado',
        meta: { sortKey: 'last_updated' },
        cell: ({ getValue }) => new Date(getValue() as string).toLocaleString('pt-BR'),
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <Link
            to={`/onus/porta/${row.original.slot}/${row.original.port}`}
            className="flex items-center justify-end gap-1 text-xs font-medium text-primary hover:underline"
          >
            <Info className="size-3.5" /> Detalhes
          </Link>
        ),
      },
    ],
    [showOltFilter],
  )

  return (
    <div>
      <PageHeader title="Ocupação de Portas" description="Lista de todas as portas da OLT e suas ocupações." />
      <DataTable
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        isFetching={isFetching}
        page={page}
        onPageChange={setPage}
        count={data?.count}
        ordering={ordering}
        onOrderingChange={(value) => {
          setOrdering(value)
          setPage(1)
        }}
        toolbar={
          <div className="flex flex-wrap gap-2">
            {showOltFilter && (
              <SelectFilter
                label="OLT"
                value={olt}
                onChange={(value) => {
                  setOlt(value)
                  setPage(1)
                }}
                options={(olts ?? []).map((o) => ({ label: o.name, value: String(o.id) }))}
              />
            )}
            <SelectFilter
              label="Slot"
              value={slot}
              onChange={(value) => {
                setSlot(value)
                setPage(1)
              }}
              options={slotOptions}
            />
          </div>
        }
      />
    </div>
  )
}
