import { useState, useMemo } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'

interface ClienteFibra {
  id: number
  mac: string
  nome: string
  endereco: string
  id_caixa_ftth: string
}

export function ClientesFibraPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const { data, isLoading, isFetching } = usePaginatedApi<ClienteFibra>({
    endpoint: '/clientes-fibra/',
    page,
    search,
  })

  const columns = useMemo<ColumnDef<ClienteFibra, unknown>[]>(
    () => [
      { accessorKey: 'nome', header: 'Nome' },
      { accessorKey: 'mac', header: 'MAC' },
      { accessorKey: 'endereco', header: 'Endereço', cell: ({ getValue }) => (getValue() as string) || '—' },
      { accessorKey: 'id_caixa_ftth', header: 'Caixa FTTH', cell: ({ getValue }) => (getValue() as string) || '—' },
    ],
    [],
  )

  return (
    <div>
      <PageHeader title="Clientes Fibra" description="Lista de clientes fibra cadastrados no sistema (sincronizado do IXC)." />
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
        searchPlaceholder="Buscar por nome, MAC…"
        page={page}
        onPageChange={setPage}
        count={data?.count}
      />
    </div>
  )
}
