import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/DataTable'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardValue } from '@/components/ui/card'
import { useOlts } from '@/hooks/useOlts'
import { situacaoStyles } from '@/lib/ctoStatus'
import { cn } from '@/lib/utils'
import type { Cto, CtoResumo, CtoSituacao } from '@/types/ctos'
import { CtoMap } from './CtoMap'
import { CtoDetailPanel } from './CtoDetailPanel'
import { InferenciasTab } from './InferenciasTab'

type Aba = 'mapa' | 'lista' | 'inferencias'

const abas: { id: Aba; label: string }[] = [
  { id: 'mapa', label: 'Mapa' },
  { id: 'lista', label: 'Lista de CTOs' },
  { id: 'inferencias', label: 'Clientes x CTO' },
]

const situacaoOptions = (Object.keys(situacaoStyles) as CtoSituacao[]).map((s) => ({
  value: s,
  label: situacaoStyles[s].label,
}))

const PAGE_SIZE = 50

export function CtosPage() {
  const [params, setParams] = useSearchParams()
  const aba = (params.get('aba') as Aba) || 'mapa'
  const oltId = params.get('olt') ?? ''
  const ramal = params.get('ramal') ?? ''
  const situacao = params.get('situacao') ?? ''
  const selectedId = params.get('cto') ? Number(params.get('cto')) : null

  /** Atualiza vários parâmetros da URL numa só navegação ('' remove o parâmetro). */
  const setManyParams = useCallback(
    (updates: Record<string, string>, replace = false) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [key, value] of Object.entries(updates)) {
            if (value) next.set(key, value)
            else next.delete(key)
          }
          return next
        },
        { replace },
      )
    },
    [setParams],
  )
  const setParam = useCallback(
    (key: string, value: string) => setManyParams({ [key]: value }, key === 'cto'),
    [setManyParams],
  )
  const selectCto = useCallback((id: number) => setParam('cto', String(id)), [setParam])

  const { data: olts } = useOlts()

  const filtros: Record<string, string> = {}
  if (oltId) filtros.olt = oltId
  if (ramal) filtros.ramal = ramal
  if (situacao) filtros.situacao = situacao

  const { data: ctos = [], isLoading } = useQuery({
    queryKey: ['/ctos/', filtros],
    queryFn: async () => (await api.get<Cto[]>('/ctos/', { params: filtros })).data,
  })

  const { data: resumo } = useQuery({
    queryKey: ['/cto-inferencias/resumo/', oltId],
    queryFn: async () =>
      (await api.get<CtoResumo>('/cto-inferencias/resumo/', { params: oltId ? { olt: oltId } : {} })).data,
  })

  // Ramais da OLT selecionada (só os que existem nos dados, já filtrados por OLT).
  const { data: todasDaOlt = [] } = useQuery({
    queryKey: ['/ctos/', { olt: oltId }],
    queryFn: async () => (await api.get<Cto[]>('/ctos/', { params: oltId ? { olt: oltId } : {} })).data,
  })
  const ramalOptions = useMemo(
    () =>
      [...new Set(todasDaOlt.map((c) => c.ramal).filter(Boolean))]
        .sort()
        .map((r) => ({ value: r, label: r })),
    [todasDaOlt],
  )

  const contagemSituacao = useMemo(() => {
    const c: Partial<Record<CtoSituacao, number>> = {}
    for (const cto of todasDaOlt) c[cto.situacao] = (c[cto.situacao] ?? 0) + 1
    return c
  }, [todasDaOlt])

  // Lista: busca/ordenação/paginação no cliente (o endpoint devolve tudo para o mapa).
  const [busca, setBusca] = useState('')
  const [ordering, setOrdering] = useState('-ocupacao')
  const [page, setPage] = useState(1)
  const listaOrdenada = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    const filtrada = termo ? ctos.filter((c) => c.descricao.toLowerCase().includes(termo)) : ctos
    const desc = ordering.startsWith('-')
    const campo = ordering.replace('-', '')
    const valor = (c: Cto): number | string => {
      if (campo === 'ocupacao') return c.portas_uteis ? c.ocupadas / c.portas_uteis : -1
      if (campo === 'descricao') return c.descricao
      if (campo === 'ocupadas') return c.ocupadas
      if (campo === 'suspeitos') return c.suspeitos
      if (campo === 'offline') return c.offline
      return c.descricao
    }
    return [...filtrada].sort((a, b) => {
      const va = valor(a)
      const vb = valor(b)
      const r = va < vb ? -1 : va > vb ? 1 : 0
      return desc ? -r : r
    })
  }, [ctos, busca, ordering])

  const colunasLista = useMemo<ColumnDef<Cto, unknown>[]>(
    () => [
      {
        accessorKey: 'descricao',
        header: 'CTO',
        meta: { sortKey: 'descricao' },
        cell: ({ row }) => (
          <button type="button" className="font-medium text-primary hover:underline" onClick={() => selectCto(row.original.id)}>
            {row.original.descricao}
          </button>
        ),
      },
      { accessorKey: 'ramal', header: 'Ramal', cell: ({ getValue }) => (getValue() as string) || '—' },
      {
        id: 'ocupacao',
        header: 'Ocupadas / portas',
        meta: { sortKey: 'ocupacao' },
        cell: ({ row }) => {
          const c = row.original
          return (
            <span>
              {c.ocupadas}/{c.portas_uteis ?? '?'}
              {c.possiveis > 0 && <span className="text-muted-foreground"> (+{c.possiveis} possíveis)</span>}
            </span>
          )
        },
      },
      {
        accessorKey: 'situacao',
        header: 'Situação',
        cell: ({ getValue }) => {
          const s = situacaoStyles[getValue() as CtoSituacao]
          return <Badge variant={s.badge}>{s.label}</Badge>
        },
      },
      { accessorKey: 'offline', header: 'Offline', meta: { sortKey: 'offline' } },
      { accessorKey: 'suspeitos', header: 'Prov. em outra', meta: { sortKey: 'suspeitos' } },
      {
        accessorKey: 'cadastro_ixc',
        header: 'Cadastro IXC',
        cell: ({ row }) => (row.original.ixc_id ? row.original.cadastro_ixc : <Badge variant="outline">fora do IXC</Badge>),
      },
    ],
    [selectCto],
  )

  const porStatus = resumo?.por_status

  return (
    <div>
      <PageHeader
        title="CTOs"
        description="Ocupação estimada de cada caixa, cruzando cadastro do IXC, projeto (KMZ), PON, distância óptica e quedas simultâneas."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Card className="gap-1 py-4">
          <CardHeader>
            <CardTitle>CTOs com portas livres</CardTitle>
            <CardValue>{contagemSituacao.livre ?? 0}</CardValue>
          </CardHeader>
        </Card>
        <Card className="gap-1 py-4">
          <CardHeader>
            <CardTitle>Cheias / acima</CardTitle>
            <CardValue>{(contagemSituacao.cheia ?? 0) + (contagemSituacao.acima ?? 0)}</CardValue>
          </CardHeader>
        </Card>
        <Card className="gap-1 py-4">
          <CardHeader>
            <CardTitle>Clientes confirmados</CardTitle>
            <CardValue>{porStatus ? porStatus.confirmado + (porStatus.vistoriado ?? 0) : '—'}</CardValue>
          </CardHeader>
        </Card>
        <Card className="gap-1 py-4">
          <CardHeader>
            <CardTitle>Localizados sem cadastro</CardTitle>
            <CardValue>{porStatus?.provavel ?? '—'}</CardValue>
          </CardHeader>
        </Card>
        <Card className="gap-1 py-4">
          <CardHeader>
            <CardTitle>Cadastros a revisar</CardTitle>
            <CardValue>
              <button type="button" className="hover:underline" onClick={() => setParam('aba', 'inferencias')}>
                {porStatus?.divergente ?? '—'}
              </button>
            </CardValue>
          </CardHeader>
        </Card>
      </div>

      <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex gap-1 rounded-lg border border-border p-1">
          {abas.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setParam('aba', a.id === 'mapa' ? '' : a.id)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm',
                aba === a.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent',
              )}
            >
              {a.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <SelectFilter
            label="OLT"
            value={oltId}
            options={(olts ?? []).map((o) => ({ value: String(o.id), label: o.name }))}
            onChange={(v) => setManyParams({ olt: v, ramal: '', cto: '' })}
          />
          {aba !== 'inferencias' && (
            <>
              <SelectFilter label="Ramal" value={ramal} options={ramalOptions} onChange={(v) => setParam('ramal', v)} />
              <SelectFilter label="Situação" value={situacao} options={situacaoOptions} onChange={(v) => setParam('situacao', v)} />
            </>
          )}
        </div>
      </div>

      <div className={cn('grid gap-4', selectedId && 'xl:grid-cols-[minmax(0,1fr)_480px]')}>
        <div className="min-w-0">
          {aba === 'mapa' &&
            (isLoading ? (
              <div className="py-10 text-center text-muted-foreground">Carregando CTOs…</div>
            ) : (
              <CtoMap ctos={ctos} selectedId={selectedId} onSelect={selectCto} />
            ))}

          {aba === 'lista' && (
            <DataTable
              columns={colunasLista}
              data={listaOrdenada.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)}
              isLoading={isLoading}
              searchValue={busca}
              onSearchChange={(v) => {
                setBusca(v)
                setPage(1)
              }}
              searchPlaceholder="Buscar CTO…"
              page={page}
              onPageChange={setPage}
              count={listaOrdenada.length}
              pageSize={PAGE_SIZE}
              ordering={ordering}
              onOrderingChange={(v) => {
                setOrdering(v)
                setPage(1)
              }}
              emptyMessage="Nenhuma CTO com esses filtros."
            />
          )}

          {aba === 'inferencias' && <InferenciasTab oltId={oltId} onSelectCto={selectCto} />}
        </div>

        {selectedId && (
          <div className="min-w-0">
            <CtoDetailPanel ctoId={selectedId} onClose={() => setParam('cto', '')} onSelect={selectCto} />
          </div>
        )}
      </div>
    </div>
  )
}
