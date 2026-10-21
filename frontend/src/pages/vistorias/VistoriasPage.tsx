import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Search } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { useOlts } from '@/hooks/useOlts'
import { ConfirmDialog, useConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { resultadoStyles } from '@/lib/vistoriaStatus'
import type { Cto } from '@/types/ctos'
import type { CorrecaoIxc, Correcoes, PortaResultado, VistoriaBasica } from '@/types/vistoria'

function NovaVistoria({ oltId }: { oltId: string }) {
  const [termo, setTermo] = useState('')
  const [tecnico, setTecnico] = useState('')
  const navigate = useNavigate()
  const toast = useToast()

  const params: Record<string, string> = { search: termo }
  if (oltId) params.olt = oltId
  const { data: ctos, isFetching } = useQuery({
    queryKey: ['/ctos/', params],
    queryFn: async () => (await api.get<Cto[]>('/ctos/', { params })).data.slice(0, 12),
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
                {!oltId && c.olt_nome ? ` · ${c.olt_nome}` : ''}
              </span>
            </Button>
          ))}
        </div>
      )}
      {ctos && ctos.length === 0 && <div className="text-sm text-muted-foreground">Nenhuma caixa com esse nome.</div>}
    </Card>
  )
}

function ListaVistorias({ oltId }: { oltId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['/vistorias/', oltId],
    queryFn: async () => (await api.get<VistoriaBasica[]>('/vistorias/', { params: oltId ? { olt: oltId } : {} })).data,
  })
  if (isLoading) return <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />
  if (!data?.length) return <div className="text-sm text-muted-foreground">Nenhuma vistoria ainda.</div>
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="px-4 py-3 font-medium">Caixa</th>
            <th className="px-4 py-3 font-medium">OLT</th>
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
              <td className="px-4 py-2.5">{v.olt_nome ?? '—'}</td>
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

type ClienteCorrecao = Correcoes['clientes'][number]

const statusCorrecao: Record<CorrecaoIxc['status'], { label: string; badge: 'success' | 'warning' | 'destructive' }> = {
  ok: { label: 'Corrigido no IXC', badge: 'success' },
  alerta: { label: 'Corrigido, com alerta', badge: 'warning' },
  erro: { label: 'Falhou', badge: 'destructive' },
}

function HistoricoCorrecoes({ oltId }: { oltId: string }) {
  const { data } = useQuery({
    queryKey: ['/vistorias/correcoes/historico/', oltId],
    queryFn: async () =>
      (await api.get<CorrecaoIxc[]>('/vistorias/correcoes/historico/', { params: oltId ? { olt: oltId } : {} })).data,
  })
  if (!data?.length) return null
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="border-b border-border px-4 py-3 font-semibold">Alterações enviadas ao IXC</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="px-4 py-2 font-medium">Quando</th>
            <th className="px-4 py-2 font-medium">Cliente</th>
            <th className="px-4 py-2 font-medium">CTO</th>
            <th className="px-4 py-2 font-medium">Por</th>
            <th className="px-4 py-2 font-medium">Resultado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((c) => (
            <tr key={c.id} className="border-b border-border align-top last:border-0">
              <td className="whitespace-nowrap px-4 py-2">{new Date(c.criado_em).toLocaleString('pt-BR')}</td>
              <td className="px-4 py-2">
                <div className="font-medium">{c.cliente_nome || c.serial}</div>
                <div className="text-xs text-muted-foreground">{c.serial}</div>
              </td>
              <td className="whitespace-nowrap px-4 py-2">
                {c.caixa_antes || '—'} → {c.cto?.descricao ?? '—'}
              </td>
              <td className="px-4 py-2">{c.usuario}</td>
              <td className="px-4 py-2">
                <Badge variant={statusCorrecao[c.status].badge}>{statusCorrecao[c.status].label}</Badge>
                {c.status !== 'ok' && <div className="mt-1 max-w-sm text-xs text-muted-foreground">{c.mensagem}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function CorrecoesIxc({ oltId }: { oltId: string }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const confirmar = useConfirmDialog<ClienteCorrecao>()
  const { data, isLoading } = useQuery({
    queryKey: ['/vistorias/correcoes/', oltId],
    queryFn: async () => (await api.get<Correcoes>('/vistorias/correcoes/', { params: oltId ? { olt: oltId } : {} })).data,
  })

  const corrigir = useMutation({
    mutationFn: async (c: ClienteCorrecao) =>
      (await api.post<CorrecaoIxc>('/vistorias/correcoes/aplicar/', { serial: c.serial, cto: c.cto_campo.id })).data,
    onSuccess: (r) => {
      if (r.status === 'ok') toast.success(`${r.cliente_nome || r.serial} corrigido no IXC`, `Agora em ${r.cto?.descricao}.`)
      else toast.error('Corrigido, mas confira no IXC', r.mensagem)
    },
    onError: (e: unknown) => {
      const dados = (e as { response?: { data?: { mensagem?: string; error?: string } } }).response?.data
      toast.error('O IXC não foi alterado', dados?.mensagem || dados?.error)
    },
    onSettled: () => {
      confirmar.close()
      queryClient.invalidateQueries({ queryKey: ['/vistorias/correcoes/'] })
      queryClient.invalidateQueries({ queryKey: ['/vistorias/correcoes/historico/'] })
    },
  })

  if (isLoading || !data) return <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />
  const alvo = confirmar.target
  return (
    <div className="flex flex-col gap-4">
      {!data.escrita_ixc_permitida && (
        <div className="rounded-md bg-secondary px-3 py-2 text-xs text-muted-foreground">
          A correção direto no IXC está desligada. Para ligar, coloque <code>IXC_PERMITIR_ESCRITA=true</code> no .env do
          servidor (só administradores verão o botão).
        </div>
      )}
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
              {data.pode_corrigir && <th className="px-4 py-2" />}
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
                {data.pode_corrigir && (
                  <td className="px-4 py-2 text-right">
                    {c.cto_campo.ixc_id ? (
                      <Button size="sm" variant="outline" onClick={() => confirmar.open(c)}>
                        Corrigir no IXC
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">cadastre a caixa no IXC</span>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {data.clientes.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
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
            <Link key={`${p.cto.id}-${p.porta ?? p.vistoriado_em}`} to={`/vistorias/${p.vistoria_id}`}>
              <Badge variant="destructive">
                {p.cto.descricao} · {p.porta ? `porta ${p.porta}` : 'drop sem porta informada'}
              </Badge>
            </Link>
          ))}
          {data.portas_fantasma.length === 0 && <span className="text-sm text-muted-foreground">Nenhuma.</span>}
        </div>
      </Card>

      <HistoricoCorrecoes oltId={oltId} />

      <ConfirmDialog
        open={confirmar.isOpen}
        title="Alterar a CTO no IXC?"
        description={
          alvo && (
            <>
              <strong>{alvo.cliente_nome || alvo.serial}</strong> passa de{' '}
              <strong>{alvo.cto_cadastro ?? 'sem caixa'}</strong> para <strong>{alvo.cto_campo.descricao}</strong> no
              cadastro de cliente fibra do IXC. O registro original fica guardado no histórico.
            </>
          )
        }
        confirmLabel="Alterar no IXC"
        isLoading={corrigir.isPending}
        onConfirm={() => alvo && corrigir.mutate(alvo)}
        onCancel={confirmar.close}
      />
    </div>
  )
}

export function VistoriasPage() {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') === 'correcoes' ? 'correcoes' : 'vistorias'
  const oltId = params.get('olt') ?? ''
  const { data: olts } = useOlts()

  const atualizar = (mudancas: Record<string, string>) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(mudancas)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    setParams(next)
  }

  return (
    <div>
      <PageHeader
        title="Vistoria de CTO"
        description="Conferência porta a porta com o técnico em campo: identifica cada cliente por etiqueta ou desconexão e acha as portas fantasma."
      />
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div className="flex w-fit gap-1 rounded-lg border border-border p-1">
        {[
          { id: 'vistorias', label: 'Vistorias' },
          { id: 'correcoes', label: 'Correções para o IXC' },
        ].map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => atualizar({ aba: a.id === 'vistorias' ? '' : a.id })}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm',
              aba === a.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent',
            )}
          >
            {a.label}
          </button>
        ))}
      </div>
        <SelectFilter
          label="OLT"
          value={oltId}
          options={(olts ?? []).map((o) => ({ value: String(o.id), label: o.name }))}
          onChange={(v) => atualizar({ olt: v })}
        />
      </div>
      {aba === 'vistorias' ? (
        <div className="flex flex-col gap-4">
          <NovaVistoria oltId={oltId} />
          <ListaVistorias oltId={oltId} />
        </div>
      ) : (
        <CorrecoesIxc oltId={oltId} />
      )}
    </div>
  )
}
