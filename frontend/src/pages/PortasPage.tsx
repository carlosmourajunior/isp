import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { Info } from 'lucide-react'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'
import type { OltUser } from '@/types/api'

export function PortasPage() {
  const [page, setPage] = useState(1)
  const [slot, setSlot] = useState('')

  const { data, isLoading, isFetching } = usePaginatedApi<OltUser>({
    endpoint: '/olt-users/',
    page,
    ordering: '-users_connected',
    filters: { slot },
  })

  const columns = useMemo<ColumnDef<OltUser, unknown>[]>(
    () => [
      {
        id: 'porta',
        header: 'Porta',
        cell: ({ row }) => `1/1/${row.original.slot}/${row.original.port}`,
      },
      { accessorKey: 'users_connected', header: 'Usuários' },
      {
        accessorKey: 'last_updated',
        header: 'Atualizado',
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
    [],
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
        toolbar={
          <SelectFilter
            label="Slot"
            value={slot}
            onChange={(value) => {
              setSlot(value)
              setPage(1)
            }}
            options={[
              { label: '1', value: '1' },
              { label: '2', value: '2' },
            ]}
          />
        }
      />
    </div>
  )
}
