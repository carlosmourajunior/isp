import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search as SearchIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Onu } from '@/types/api'

interface SearchResponse {
  query: string
  total_resultados: number
  resultados: Onu[]
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')

  const { data, isLoading, isFetched } = useQuery({
    queryKey: ['/onus/search/', submitted],
    queryFn: async () => (await api.get<SearchResponse>('/onus/search/', { params: { q: submitted } })).data,
    enabled: submitted.length > 0,
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitted(query.trim())
  }

  return (
    <div>
      <PageHeader title="Busca" description="Busca por serial, MAC, descrição ou PON." />

      <form onSubmit={handleSubmit} className="mb-4 flex max-w-md gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Digite para buscar…"
          autoFocus
        />
        <Button type="submit">
          <SearchIcon className="size-4" /> Buscar
        </Button>
      </form>

      {isLoading && <p className="text-sm text-muted-foreground">Buscando…</p>}

      {isFetched && data && (
        <>
          <p className="mb-3 text-sm text-muted-foreground">
            {data.total_resultados} resultado{data.total_resultados === 1 ? '' : 's'} para "{data.query}"
          </p>
          <Card className="gap-0 overflow-hidden py-0">
            {data.resultados.length === 0 ? (
              <p className="px-5 py-10 text-center text-sm text-muted-foreground">Nenhum resultado encontrado.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-muted-foreground">
                      <th className="px-4 py-3 font-medium">PON</th>
                      <th className="px-4 py-3 font-medium">Posição</th>
                      <th className="px-4 py-3 font-medium">Serial</th>
                      <th className="px-4 py-3 font-medium">MAC</th>
                      <th className="px-4 py-3 font-medium">Estado</th>
                      <th className="px-4 py-3 font-medium">Descrição</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.resultados.map((onu) => (
                      <tr key={onu.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-2.5 text-foreground">{onu.pon}</td>
                        <td className="px-4 py-2.5">{onu.position}</td>
                        <td className="px-4 py-2.5 text-foreground">{onu.serial}</td>
                        <td className="px-4 py-2.5">{onu.mac || '—'}</td>
                        <td className="px-4 py-2.5">
                          <Badge variant={onu.oper_state === 'up' ? 'success' : 'destructive'}>{onu.oper_state}</Badge>
                        </td>
                        <td className="px-4 py-2.5">{onu.desc1}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
