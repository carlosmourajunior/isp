import { useState, useMemo } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { usePaginatedApi } from '@/hooks/usePaginatedApi'

interface ClienteFibra {
  id: number
  mac: string
  nome: string
  endereco: string
  id_caixa_ftth: string
  vinculado: boolean
}

export function ClientesFibraPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [vinculado, setVinculado] = useState('')
  const [ordering, setOrdering] = useState('')

  const { data, isLoading, isFetching } = usePaginatedApi<ClienteFibra>({
    endpoint: '/clientes-fibra/interno/',
    page,
    search,
    ordering,
    filters: { vinculado },
  })

  const columns = useMemo<ColumnDef<ClienteFibra, unknown>[]>(
    () => [
      { accessorKey: 'nome', header: 'Nome', meta: { sortKey: 'nome' } },
      {
        accessorKey: 'mac',
        header: 'MAC',
        meta: { sortKey: 'mac' },
        cell: ({ getValue }) => <span className="font-data">{getValue() as string}</span>,
      },
      {
        accessorKey: 'endereco',
        header: 'Endereço',
        meta: { sortKey: 'endereco' },
        cell: ({ getValue }) => (getValue() as string) || '—',
      },
      {
        accessorKey: 'id_caixa_ftth',
        header: 'Caixa FTTH',
        meta: { sortKey: 'id_caixa_ftth' },
        cell: ({ getValue }) => (getValue() as string) || '—',
      },
      {
        accessorKey: 'vinculado',
        header: 'Vinculado a contrato',
        meta: { sortKey: 'vinculado' },
        cell: ({ getValue }) =>
          getValue() ? <Badge variant="success">Sim</Badge> : <Badge variant="warning">Não</Badge>,
      },
    ],
    [],
  )

  return (
    <div>
      <PageHeader
        title="Clientes Fibra"
        description="Lista de clientes fibra cadastrados no sistema (sincronizado do IXC). 'Vinculado' indica se o registro tem um contrato real no IXC por trás — sem isso, nome/endereço vêm do provisionamento da OLT, não do cadastro do cliente."
      />
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
        searchPlaceholder="Buscar por nome, MAC, endereço…"
        page={page}
        onPageChange={setPage}
        count={data?.count}
        ordering={ordering}
        onOrderingChange={(value) => {
          setOrdering(value)
          setPage(1)
        }}
        toolbar={
          <SelectFilter
            label="Vinculado"
            value={vinculado}
            onChange={(value) => {
              setVinculado(value)
              setPage(1)
            }}
            options={[
              { label: 'Sim', value: 'true' },
              { label: 'Não', value: 'false' },
            ]}
          />
        }
      />
    </div>
  )
}
