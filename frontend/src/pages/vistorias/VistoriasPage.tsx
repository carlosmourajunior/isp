import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Search, Undo2 } from 'lucide-react'
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
import type { AlteracaoIxc, Correcoes, LoteResultado, PortaResultado, VistoriaBasica } from '@/types/vistoria'

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
                {c.ocupadas}/{c.portas_uteis ?? '?'}
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

const statusAlteracao: Record<AlteracaoIxc['status'], { badge: 'success' | 'warning' | 'destructive' }> = {
  ok: { badge: 'success' },
  alerta: { badge: 'warning' },
  erro: { badge: 'destructive' },
}

function rotuloStatus(a: AlteracaoIxc) {
  if (a.status === 'erro') return 'Falhou'
  const base = a.tipo === 'reversao' ? 'Revertido no IXC' : 'Corrigido no IXC'
  return a.status === 'alerta' ? `${base}, com alerta` : base
}

function erroDaApi(e: unknown) {
  const dados = (e as { response?: { data?: { mensagem?: string; error?: string } } }).response?.data
  return dados?.mensagem || dados?.error
}

function HistoricoCorrecoes({ oltId, podeEscrever, motivoSemEscrita }: {
  oltId: string
  podeEscrever: boolean
  motivoSemEscrita: string
}) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const confirmar = useConfirmDialog<AlteracaoIxc>()
  const { data } = useQuery({
    queryKey: ['/ixc/correcoes/', oltId],
    queryFn: async () => (await api.get<AlteracaoIxc[]>('/ixc/correcoes/', { params: oltId ? { olt: oltId } : {} })).data,
  })

  const reverter = useMutation({
    mutationFn: async (a: AlteracaoIxc) => (await api.post<AlteracaoIxc>(`/ixc/correcoes/${a.id}/reverter/`)).data,
    onSuccess: (r) => {
      if (r.status === 'ok')
        toast.success(`${r.cliente_nome || r.serial} revertido no IXC`, `Voltou para ${r.caixa_depois?.descricao ?? 'sem caixa'}.`)
      else toast.error('Revertido, mas confira no IXC', r.mensagem)
    },
    onError: (e: unknown) => toast.error('O IXC não foi alterado', erroDaApi(e)),
    onSettled: () => {
      confirmar.close()
      queryClient.invalidateQueries({ queryKey: ['/ixc/correcoes/'] })
      queryClient.invalidateQueries({ queryKey: ['/vistorias/correcoes/'] })
    },
  })

  if (!data?.length) return null
  const alvo = confirmar.target
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="border-b border-border px-4 py-3">
        <div className="font-semibold">Alterações enviadas ao IXC</div>
        <div className="text-xs text-muted-foreground">
          Reverter volta o cliente para a caixa que ele tinha antes da correção. Só funciona se ninguém tiver mudado a
          caixa no IXC depois.
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="px-4 py-2 font-medium">Quando</th>
              <th className="px-4 py-2 font-medium">Cliente</th>
              <th className="px-4 py-2 font-medium">CTO</th>
              <th className="px-4 py-2 font-medium">Por</th>
              <th className="px-4 py-2 font-medium">Resultado</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {data.map((a) => (
              <tr
                key={a.id}
                className={cn('border-b border-border align-top last:border-0', a.revertida && 'text-muted-foreground')}
              >
                <td className="whitespace-nowrap px-4 py-2">{new Date(a.criado_em).toLocaleString('pt-BR')}</td>
                <td className="px-4 py-2">
                  <div className="font-medium">{a.cliente_nome || a.serial}</div>
                  <div className="text-xs text-muted-foreground">{a.serial}</div>
                </td>
                <td className="whitespace-nowrap px-4 py-2">
                  <span className={cn(a.revertida && 'line-through')}>
                    {a.caixa_antes?.descricao ?? 'sem caixa'} → {a.caixa_depois?.descricao ?? 'sem caixa'}
                  </span>
                  {a.tipo === 'reversao' && (
                    <Badge variant="outline" className="ml-1.5">
                      reversão
                    </Badge>
                  )}
                </td>
                <td className="px-4 py-2">{a.usuario}</td>
                <td className="px-4 py-2">
                  <Badge variant={statusAlteracao[a.status].badge}>{rotuloStatus(a)}</Badge>
                  {a.revertida && (
                    <div className="mt-1 text-xs">
                      Revertida em {new Date(a.revertida.em).toLocaleString('pt-BR')} por {a.revertida.por}
                    </div>
                  )}
                  {a.status !== 'ok' && <div className="mt-1 max-w-sm text-xs text-muted-foreground">{a.mensagem}</div>}
                </td>
                <td className="px-4 py-2 text-right">
                  {a.tipo === 'correcao' && a.status !== 'erro' && !a.revertida && (
                    <span title={!podeEscrever ? motivoSemEscrita : (a.motivo_nao_reverter ?? undefined)}>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!podeEscrever || !a.pode_reverter}
                        onClick={() => confirmar.open(a)}
                      >
                        <Undo2 className="size-3.5" /> Reverter
                      </Button>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={confirmar.isOpen}
        title="Reverter a alteração no IXC?"
        description={
          alvo && (
            <>
              <strong>{alvo.cliente_nome || alvo.serial}</strong> volta de{' '}
              <strong>{alvo.caixa_depois?.descricao ?? 'sem caixa'}</strong> para{' '}
              <strong>{alvo.caixa_antes?.descricao ?? 'sem caixa'}</strong> no IXC. Se a vistoria continuar dizendo
              outra caixa, o cliente volta para a lista de correções pendentes.
            </>
          )
        }
        confirmLabel="Reverter no IXC"
        isLoading={reverter.isPending}
        onConfirm={() => alvo && reverter.mutate(alvo)}
        onCancel={confirmar.close}
      />
    </Card>
  )
}

function CorrecoesIxc({ oltId }: { oltId: string }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [confirmarLote, setConfirmarLote] = useState<ClienteCorrecao[] | null>(null)
  const { data, isLoading } = useQuery({
    queryKey: ['/vistorias/correcoes/', oltId],
    queryFn: async () => (await api.get<Correcoes>('/vistorias/correcoes/', { params: oltId ? { olt: oltId } : {} })).data,
  })

  const corrigir = useMutation({
    mutationFn: async (itens: ClienteCorrecao[]) =>
      (
        await api.post<LoteResultado>('/ixc/correcoes/lote/', {
          itens: itens.map((c) => ({ serial: c.serial, cto: c.cto_campo.id })),
        })
      ).data,
    onSuccess: (r) => {
      if (r.resultados.length === 1) {
        const a = r.resultados[0]
        if (a.status === 'ok') toast.success(`${a.cliente_nome || a.serial} corrigido no IXC`, `Agora em ${a.caixa_depois?.descricao}.`)
        else if (a.status === 'alerta') toast.error('Corrigido, mas confira no IXC', a.mensagem)
        else toast.error('O IXC não foi alterado', a.mensagem)
        return
      }
      const resumo = `${r.ok} corrigidos${r.alerta ? `, ${r.alerta} com alerta` : ''}${r.erro ? `, ${r.erro} falharam` : ''}.`
      if (r.erro || r.alerta) toast.error('Lote enviado com pendências', `${resumo} Veja os detalhes no histórico abaixo.`)
      else toast.success('Lote corrigido no IXC', resumo)
    },
    onError: (e: unknown) => toast.error('O IXC não foi alterado', erroDaApi(e)),
    onSettled: () => {
      setConfirmarLote(null)
      setSelecionados(new Set())
      queryClient.invalidateQueries({ queryKey: ['/vistorias/correcoes/'] })
      queryClient.invalidateQueries({ queryKey: ['/ixc/correcoes/'] })
    },
  })

  if (isLoading || !data) return <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />

  const corrigiveis = data.clientes.filter((c) => c.cto_campo.ixc_id)
  // Ignora seleções de itens que sumiram da lista (ex.: corrigidos por outra pessoa).
  const escolhidos = corrigiveis.filter((c) => selecionados.has(c.serial))
  const todos = corrigiveis.length > 0 && escolhidos.length === corrigiveis.length

  function alternar(serial: string) {
    setSelecionados((atual) => {
      const novo = new Set(atual)
      if (novo.has(serial)) novo.delete(serial)
      else novo.add(serial)
      return novo
    })
  }

  return (
    <div className="flex flex-col gap-4">
      {!data.pode_corrigir && (
        <div className="rounded-md bg-secondary px-3 py-2 text-xs text-muted-foreground">
          {data.motivo_sem_escrita}
          {!data.escrita_ixc_permitida && (
            <>
              {' '}
              Para ligar, coloque <code>IXC_PERMITIR_ESCRITA=true</code> no .env do servidor e recrie o container web.
            </>
          )}
        </div>
      )}
      <Card className="gap-0 overflow-hidden py-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <div className="font-semibold">Clientes com CTO errada no IXC ({data.clientes.length})</div>
            <div className="text-xs text-muted-foreground">Encontrados em campo numa caixa diferente da cadastrada.</div>
          </div>
          {data.pode_corrigir && corrigiveis.length > 0 && (
            <Button size="sm" disabled={escolhidos.length === 0} onClick={() => setConfirmarLote(escolhidos)}>
              Corrigir selecionados no IXC ({escolhidos.length})
            </Button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="w-8 px-4 py-2">
                  <input
                    type="checkbox"
                    aria-label="Selecionar todos"
                    className="size-4 accent-primary"
                    checked={todos}
                    disabled={!data.pode_corrigir || corrigiveis.length === 0}
                    onChange={() => setSelecionados(todos ? new Set() : new Set(corrigiveis.map((c) => c.serial)))}
                  />
                </th>
                <th className="px-4 py-2 font-medium">Cliente</th>
                <th className="px-4 py-2 font-medium">Cadastro IXC</th>
                <th className="px-4 py-2 font-medium">Corrigir para</th>
                <th className="px-4 py-2 font-medium">Vistoria</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {data.clientes.map((c) => (
                <tr
                  key={c.serial}
                  className={cn('border-b border-border last:border-0', selecionados.has(c.serial) && 'bg-primary/5')}
                >
                  <td className="px-4 py-2">
                    {c.cto_campo.ixc_id && (
                      <input
                        type="checkbox"
                        aria-label={`Selecionar ${c.cliente_nome || c.serial}`}
                        className="size-4 accent-primary"
                        checked={selecionados.has(c.serial)}
                        disabled={!data.pode_corrigir}
                        onChange={() => alternar(c.serial)}
                      />
                    )}
                  </td>
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
                  <td className="px-4 py-2 text-right">
                    {c.cto_campo.ixc_id ? (
                      <span title={data.pode_corrigir ? undefined : data.motivo_sem_escrita}>
                        <Button size="sm" variant="outline" disabled={!data.pode_corrigir} onClick={() => setConfirmarLote([c])}>
                          Corrigir no IXC
                        </Button>
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">cadastre a caixa no IXC</span>
                    )}
                  </td>
                </tr>
              ))}
              {data.clientes.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                    Nada a corrigir.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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

      <HistoricoCorrecoes oltId={oltId} podeEscrever={data.pode_corrigir} motivoSemEscrita={data.motivo_sem_escrita} />

      <ConfirmDialog
        open={confirmarLote !== null}
        title={confirmarLote?.length === 1 ? 'Alterar a CTO no IXC?' : `Alterar a CTO de ${confirmarLote?.length} clientes no IXC?`}
        description={
          confirmarLote &&
          (confirmarLote.length === 1 ? (
            <>
              <strong>{confirmarLote[0].cliente_nome || confirmarLote[0].serial}</strong> passa de{' '}
              <strong>{confirmarLote[0].cto_cadastro ?? 'sem caixa'}</strong> para{' '}
              <strong>{confirmarLote[0].cto_campo.descricao}</strong> no cadastro de cliente fibra do IXC. Dá para reverter
              pelo histórico.
            </>
          ) : (
            <>
              <ul className="mb-2 max-h-48 overflow-y-auto">
                {confirmarLote.map((c) => (
                  <li key={c.serial}>
                    <strong>{c.cliente_nome || c.serial}</strong>: {c.cto_cadastro ?? 'sem caixa'} → {c.cto_campo.descricao}
                  </li>
                ))}
              </ul>
              Cada um é alterado e conferido separadamente; dá para reverter qualquer um pelo histórico.
            </>
          ))
        }
        confirmLabel={confirmarLote && confirmarLote.length > 1 ? `Alterar ${confirmarLote.length} no IXC` : 'Alterar no IXC'}
        isLoading={corrigir.isPending}
        onConfirm={() => confirmarLote && corrigir.mutate(confirmarLote)}
        onCancel={() => setConfirmarLote(null)}
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
