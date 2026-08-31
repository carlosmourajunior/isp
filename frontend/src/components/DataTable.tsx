import { useEffect, useState, type ReactNode } from 'react'
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table'
import { ChevronLeft, ChevronRight, Loader2, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

interface DataTableProps<T> {
  columns: ColumnDef<T, unknown>[]
  data: T[]
  isLoading?: boolean
  isFetching?: boolean
  searchValue: string
  onSearchChange: (value: string) => void
  searchPlaceholder?: string
  page: number
  onPageChange: (page: number) => void
  count?: number
  pageSize?: number
  emptyMessage?: string
  toolbar?: ReactNode
}

export function DataTable<T>({
  columns,
  data,
  isLoading,
  isFetching,
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Buscar…',
  page,
  onPageChange,
  count,
  pageSize = 50,
  emptyMessage = 'Nenhum resultado encontrado.',
  toolbar,
}: DataTableProps<T>) {
  const [localSearch, setLocalSearch] = useState(searchValue)

  useEffect(() => setLocalSearch(searchValue), [searchValue])

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (localSearch !== searchValue) onSearchChange(localSearch)
    }, 400)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [localSearch])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const totalPages = count ? Math.max(1, Math.ceil(count / pageSize)) : undefined

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            placeholder={searchPlaceholder}
            className="pl-8"
          />
        </div>
        {toolbar}
      </div>

      <Card className="gap-0 overflow-hidden py-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="border-b border-border text-left text-xs text-muted-foreground">
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="whitespace-nowrap px-4 py-3 font-medium">
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-10 text-center text-muted-foreground">
                    <Loader2 className="mx-auto size-5 animate-spin" />
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-10 text-center text-muted-foreground">
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="border-b border-border last:border-0 hover:bg-accent/40">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="whitespace-nowrap px-4 py-2.5 text-foreground">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {count !== undefined ? `${count} resultado${count === 1 ? '' : 's'}` : isFetching ? 'Atualizando…' : ''}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-1 disabled:opacity-40"
          >
            <ChevronLeft className="size-4" /> Anterior
          </button>
          <span>
            Página {page}
            {totalPages ? ` de ${totalPages}` : ''}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={totalPages ? page >= totalPages : data.length < pageSize}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-1 disabled:opacity-40"
          >
            Próxima <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
