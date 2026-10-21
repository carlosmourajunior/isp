import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, Search } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { resultadoStyles } from '@/lib/vistoriaStatus'
import type { Cto } from '@/types/ctos'
import type { Correcoes, PortaResultado, VistoriaBasica } from '@/types/vistoria'

function NovaVistoria() {
  const [termo, setTermo] = useState('')
  const [tecnico, setTecnico] = useState('')
  const navigate = useNavigate()
  const toast = useToast()

  const { data: ctos, isFetching } = useQuery({
    queryKey: ['/ctos/', { search: termo }],
    queryFn: async () => (await api.get<Cto[]>('/ctos/', { params: { search: termo } })).data.slice(0, 12),
    enabled: termo.trim().length >= 2,
  })

  const iniciar = useMutation({
    mutationFn: async (ctoId: number) =>
      (await api.post<VistoriaBasica>('/vistorias/', { cto: ctoId, tecnico })).data,
    onSuccess: (v) => navigate(`/vistorias/${v.id}`),
    onError: () => toast.error('Não foi possível iniciar a vistoria'),
  })

  return (
    <Card className="gap-3 px-4 py-4">
      <div className="font-semibold">Nova vistoria</div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={termo} onChange={(e) => setTermo(e.target.value)} placeholder="Caixa (ex.: CA_096)…" className="pl-8" />
        </div>
        <Input value={tecnico} onChange={(e) => setTecnico(e.target.value)} placeholder="Técnico em campo (opcional)" className="sm:w-64" />
      </div>
      {isFetching && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
      {ctos && ctos.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {ctos.map((c) => (
            <Button key={c.id} variant="outline" size="sm" disabled={iniciar.isPending} onClick={() => iniciar.mutate(c.id)}>
              {c.descricao}
              <span className="text-xs text-muted-foreground">
                {c.ocupadas}/{c.portas ?? '?'}
              </span>
            </Button>
          ))}
        </div>
      )}
      {ctos && ctos.length === 0 && <div className="text-sm text-muted-foreground">Nenhuma caixa com esse nome.</div>}
    </Card>
  )
}

function ListaVistorias() {
  const { data, isLoading } = useQuery({
    queryKey: ['/vistorias/'],
    queryFn: async () => (await api.get<VistoriaBasica[]>('/vistorias/')).data,
  })
  if (isLoading) return <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />
  if (!data?.length) return <div className="text-sm text-muted-foreground">Nenhuma vistoria ainda.</div>
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="px-4 py-3 font-medium">Caixa</th>
            <th className="px-4 py-3 font-medium">Início</th>
            <th className="px-4 py-3 font-medium">Técnico</th>
            <th className="px-4 py-3 font-medium">Portas</th>
            <th className="px-4 py-3 font-medium">Situação</th>
          </tr>
        </thead>
        <tbody>
          {data.map((v) => (
            <tr key={v.id} className="border-b border-border last:border-0 hover:bg-accent/40">
              <td className="px-4 py-2.5">
                <Link to={`/vistorias/${v.id}`} className="font-medium text-primary hover:underline">
                  {v.cto.descricao}
                </Link>
              </td>
              <td className="px-4 py-2.5">{new Date(v.iniciada_em).toLocaleString('pt-BR')}</td>
              <td className="px-4 py-2.5">{v.tecnico || '—'}</td>
              <td className="px-4 py-2.5">
                <div className="flex flex-wrap gap-1">
                  {Object.entries(v.resumo ?? {}).map(([r, n]) => (
                    <Badge key={r} variant={resultadoStyles[r as PortaResultado].badge}>
                      {n} {resultadoStyles[r as PortaResultado].label.toLowerCase()}
                    </Badge>
                  ))}
                </div>
              </td>
              <td className="px-4 py-2.5">
                {v.finalizada_em ? <Badge variant="success">Finalizada</Badge> : <Badge variant="warning">Em andamento</Badge>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function CorrecoesIxc() {
  const { data, isLoading } = useQuery({
    queryKey: ['/vistorias/correcoes/'],
    queryFn: async () => (await api.get<Correcoes>('/vistorias/correcoes/')).data,
  })
  if (isLoading || !data) return <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />
  return (
    <div className="flex flex-col gap-4">
      <Card className="gap-0 overflow-hidden py-0">
        <div className="border-b border-border px-4 py-3">
          <div className="font-semibold">Clientes com CTO errada no IXC ({data.clientes.length})</div>
          <div className="text-xs text-muted-foreground">Encontrados em campo numa caixa diferente da cadastrada.</div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="px-4 py-2 font-medium">Cliente</th>
              <th className="px-4 py-2 font-medium">Cadastro IXC</th>
              <th className="px-4 py-2 font-medium">Corrigir para</th>
              <th className="px-4 py-2 font-medium">Vistoria</th>
            </tr>
          </thead>
          <tbody>
            {data.clientes.map((c) => (
              <tr key={c.serial} className="border-b border-border last:border-0">
                <td className="px-4 py-2">
                  <div className="font-medium">{c.cliente_nome || '(sem cliente no IXC)'}</div>
                  <div className="text-xs text-muted-foreground">{c.serial}</div>
                </td>
                <td className="px-4 py-2">{c.cto_cadastro ?? <span className="text-muted-foreground">sem caixa</span>}</td>
                <td className="px-4 py-2 font-medium">
                  {c.cto_campo.descricao}
                  {!c.cto_campo.ixc_id && <Badge variant="outline" className="ml-1">caixa fora do IXC</Badge>}
                </td>
                <td className="px-4 py-2">
                  <Link to={`/vistorias/${c.vistoria_id}`} className="text-primary hover:underline">
                    {new Date(c.vistoriado_em).toLocaleDateString('pt-BR')}
                  </Link>
                </td>
              </tr>
            ))}
            {data.clientes.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
                  Nada a corrigir.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card className="gap-0 overflow-hidden py-0">
        <div className="border-b border-border px-4 py-3">
          <div className="font-semibold">Portas fantasma - a liberar ({data.portas_fantasma.length})</div>
          <div className="text-xs text-muted-foreground">Com drop ligado, mas nenhuma ONT ativa do outro lado.</div>
        </div>
        <div className="flex flex-wrap gap-2 px-4 py-3">
          {data.portas_fantasma.map((p) => (
            <Link key={`${p.cto.id}-${p.porta}`} to={`/vistorias/${p.vistoria_id}`}>
              <Badge variant="destructive">
                {p.cto.descricao} · porta {p.porta}
              </Badge>
            </Link>
          ))}
          {data.portas_fantasma.length === 0 && <span className="text-sm text-muted-foreground">Nenhuma.</span>}
        </div>
      </Card>
    </div>
  )
}

export function VistoriasPage() {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') === 'correcoes' ? 'correcoes' : 'vistorias'
  return (
    <div>
      <PageHeader
        title="Vistoria de CTO"
        description="Conferência porta a porta com o técnico em campo: identifica cada cliente por etiqueta ou desconexão e acha as portas fantasma."
      />
      <div className="mb-4 flex w-fit gap-1 rounded-lg border border-border p-1">
        {[
          { id: 'vistorias', label: 'Vistorias' },
          { id: 'correcoes', label: 'Correções para o IXC' },
        ].map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => setParams(a.id === 'vistorias' ? {} : { aba: a.id })}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm',
              aba === a.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent',
            )}
          >
            {a.label}
          </button>
        ))}
      </div>
      {aba === 'vistorias' ? (
        <div className="flex flex-col gap-4">
          <NovaVistoria />
          <ListaVistorias />
        </div>
      ) : (
        <CorrecoesIxc />
      )}
    </div>
  )
}
