import { useState, useMemo } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'

interface FtthBox {
  id_caixa_ftth: string
  client_count: number
}

export function FtthBoxesPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [ordering, setOrdering] = useState('-client_count')

  const { data, isLoading, isFetching } = usePaginatedApi<FtthBox>({
    endpoint: '/olt/ftth-boxes/',
    page,
    search,
    ordering,
  })

  const columns = useMemo<ColumnDef<FtthBox, unknown>[]>(
    () => [
      {
        accessorKey: 'id_caixa_ftth',
        header: 'Caixa FTTH',
        meta: { sortKey: 'id_caixa_ftth' },
        cell: ({ getValue }) => (getValue() as string) || '—',
      },
      { accessorKey: 'client_count', header: 'Clientes', meta: { sortKey: 'client_count' } },
    ],
    [],
  )

  return (
    <div>
      <PageHeader title="Caixas FTTH" description="Caixas FTTH ordenadas por quantidade de clientes conectados." />
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
        searchPlaceholder="Buscar por caixa…"
        page={page}
        onPageChange={setPage}
        count={data?.count}
        ordering={ordering}
        onOrderingChange={(value) => {
          setOrdering(value)
          setPage(1)
        }}
      />
    </div>
  )
}
