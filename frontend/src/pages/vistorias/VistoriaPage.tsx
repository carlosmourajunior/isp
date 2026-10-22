import { useCallback, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, Loader2, Plus, Radio, Search, Tag } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { papelVistoriaLabel, resultadoStyles } from '@/lib/vistoriaStatus'
import type { ClienteInfo, EventoAoVivo, PortaRegistro, PortaResultado, VistoriaDetalhe } from '@/types/vistoria'
import { ClienteLinha } from './ClienteLinha'
import { IdentificacaoAoVivo } from './IdentificacaoAoVivo'

interface SalvarPorta {
  porta: number | null
  resultado: PortaResultado
  serial?: string
  metodo?: 'etiqueta' | 'desconexao' | 'manual'
  reconexao_confirmada?: boolean
  observacao?: string
}

/** Escolher o cliente da etiqueta: primeiro entre os candidatos, depois busca no cadastro todo. */
function EscolherCliente({
  candidatos,
  porta,
  onEscolher,
  onClose,
}: {
  candidatos: ClienteInfo[]
  porta: number
  onEscolher: (serial: string) => void
  onClose: () => void
}) {
  const [termo, setTermo] = useState('')
  const filtrados = useMemo(() => {
    const t = termo.trim().toLowerCase()
    return t
      ? candidatos.filter(
          (c) =>
            c.cliente_nome.toLowerCase().includes(t) ||
            c.login.toLowerCase().includes(t) ||
            c.serial.toLowerCase().includes(t),
        )
      : candidatos
  }, [candidatos, termo])

  const buscaAtiva = termo.trim().length >= 3
  const { data: foraBruto, isFetching } = useQuery({
    queryKey: ['/vistorias/clientes/', termo],
    queryFn: async () => (await api.get<ClienteInfo[]>('/vistorias/clientes/', { params: { q: termo } })).data,
    enabled: buscaAtiva,
  })
  // Fora da lista = resultados do cadastro todo que não são candidatos desta caixa.
  const fora = useMemo(() => {
    const daCaixa = new Set(candidatos.map((c) => c.serial))
    return (foraBruto ?? []).filter((c) => !daCaixa.has(c.serial))
  }, [foraBruto, candidatos])

  const opcao = (c: ClienteInfo, extra?: React.ReactNode) => (
    <button
      key={c.serial}
      type="button"
      onClick={() => onEscolher(c.serial)}
      className="rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-accent"
    >
      <ClienteLinha c={c} extra={extra} />
      {c.outros_logins.length > 0 && (
        <div className="mt-1 text-xs text-amber-700 dark:text-amber-400">
          Este titular tem outro(s) login(s): {c.outros_logins.map((o) => o.login || o.serial).join(', ')}. Confira qual é o
          desta caixa pela etiqueta - na dúvida, identifique por desconexão.
        </div>
      )}
    </button>
  )

  return (
    <Card className="gap-0 border-primary/50 py-0">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 font-semibold">
          <Tag className="size-4 text-primary" /> Cliente da porta {porta} (etiqueta)
        </div>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
      </div>
      <div className="flex max-h-[28rem] flex-col gap-2 overflow-y-auto px-4 py-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Nome, login da etiqueta ou serial…"
            className="pl-8"
          />
        </div>

        <div className="text-xs font-medium text-muted-foreground">Candidatos desta caixa</div>
        {filtrados.length > 0 ? (
          filtrados.map((c) => opcao(c))
        ) : (
          <div className="text-sm text-muted-foreground">Nenhum candidato com esse nome.</div>
        )}

        {buscaAtiva && (
          <>
            <div className="mt-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
              No cadastro todo (cliente que o IXC coloca em outra caixa)
              {isFetching && <Loader2 className="size-3 animate-spin" />}
            </div>
            {fora.map((c) =>
              opcao(
                c,
                c.cto_provavel && (
                  <span className="text-xs text-muted-foreground">rede aponta {c.cto_provavel.descricao}</span>
                ),
              ),
            )}
            {!isFetching && fora.length === 0 && (
              <div className="text-sm text-muted-foreground">Nenhum outro cliente com esse nome. Tente por desconexão.</div>
            )}
          </>
        )}
        {!buscaAtiva && (
          <div className="text-xs text-muted-foreground">
            Digite 3 letras ou mais para procurar também no cadastro todo.
          </div>
        )}
      </div>
    </Card>
  )
}

function PortaCard({
  numero,
  registro,
  ativa,
  finalizada,
  onEtiqueta,
  onMarcar,
  onLimpar,
}: {
  numero: number
  registro?: PortaRegistro
  ativa: boolean
  finalizada: boolean
  onEtiqueta: () => void
  onMarcar: (resultado: PortaResultado) => void
  onLimpar: () => void
}) {
  return (
    <div className={cn('flex flex-col gap-2 rounded-lg border border-border p-3', ativa && 'border-primary ring-1 ring-primary')}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">Porta {numero}</span>
        {registro ? (
          <Badge variant={resultadoStyles[registro.resultado].badge}>{resultadoStyles[registro.resultado].label}</Badge>
        ) : (
          <Badge variant="outline">Pendente</Badge>
        )}
      </div>

      {registro?.resultado === 'cliente' && <RegistroCliente registro={registro} />}

      {!finalizada && (
        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="outline" onClick={onEtiqueta}>
            <Tag /> Etiqueta
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onMarcar('vazia')}>
            Vazia
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onMarcar('sem_ont_ativa')}>
            Fantasma
          </Button>
          {registro && (
            <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={onLimpar}>
              Limpar
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

function RegistroCliente({ registro }: { registro: PortaRegistro }) {
  return (
    <div className="text-sm">
      <div className="font-medium">{registro.cliente_nome || registro.serial}</div>
      <div className="text-xs text-muted-foreground">
        {registro.serial}
        {registro.pon && ` · PON ${registro.pon}`} · {registro.metodo === 'desconexao' ? 'por desconexão' : 'por etiqueta'}
        {registro.reconexao_confirmada && (
          <span className="ml-1 inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="size-3" /> voltou
          </span>
        )}
      </div>
    </div>
  )
}

export function VistoriaPage() {
  const { id } = useParams()
  const vistoriaId = Number(id)
  const toast = useToast()
  const queryClient = useQueryClient()
  const [etiquetaPorta, setEtiquetaPorta] = useState<number | null>(null)
  // 0 = painel de desconexão fechado; cada nova identificação troca a key e reinicia o painel.
  const [identificacao, setIdentificacao] = useState(0)
  const [portasExtras, setPortasExtras] = useState(0)

  const queryKey = useMemo(() => ['/vistorias/', vistoriaId], [vistoriaId])
  const { data: v, isLoading } = useQuery({
    queryKey,
    queryFn: async () => (await api.get<VistoriaDetalhe>(`/vistorias/${vistoriaId}/`)).data,
  })
  const recarregar = useCallback(() => queryClient.invalidateQueries({ queryKey }), [queryClient, queryKey])

  const salvar = useCallback(
    async (dados: SalvarPorta) => {
      try {
        await api.post(`/vistorias/${vistoriaId}/portas/`, dados)
        await recarregar()
      } catch {
        toast.error('Não foi possível salvar o registro')
        throw new Error('falha ao salvar')
      }
    },
    [vistoriaId, recarregar, toast],
  )

  const limpar = useMutation({
    mutationFn: (registroId: number) => api.delete(`/vistorias/${vistoriaId}/registros/${registroId}/`),
    onSuccess: () => recarregar(),
  })

  const finalizar = useMutation({
    mutationFn: () => api.post(`/vistorias/${vistoriaId}/finalizar/`, {}),
    onSuccess: () => {
      toast.success('Vistoria finalizada', 'O mapa de CTOs é recalculado com o resultado de campo.')
      recarregar()
    },
    onError: () => toast.error('Erro ao finalizar a vistoria'),
  })

  const onIdentificado = useCallback(
    (e: EventoAoVivo, porta: number | null) =>
      salvar({ porta, resultado: 'cliente', serial: e.serial, metodo: 'desconexao' }),
    [salvar],
  )
  const onReconectado = useCallback(
    (e: EventoAoVivo, porta: number | null) =>
      salvar({ porta, resultado: 'cliente', serial: e.serial, metodo: 'desconexao', reconexao_confirmada: true }),
    [salvar],
  )

  if (isLoading || !v) {
    return (
      <div className="py-10 text-center text-muted-foreground">
        <Loader2 className="mx-auto size-5 animate-spin" />
      </div>
    )
  }

  const finalizada = Boolean(v.finalizada_em)
  const comPorta = v.portas.filter((p) => p.porta !== null)
  const semPorta = v.portas.filter((p) => p.porta === null)
  const totalPortas = Math.max(v.cto.portas ?? 8, ...comPorta.map((p) => p.porta as number)) + portasExtras
  const porNumero = new Map(comPorta.map((p) => [p.porta as number, p]))
  const portasLivres = Array.from({ length: totalPortas }, (_, i) => i + 1).filter((n) => !porNumero.has(n))
  const pendentes = v.candidatos.filter((c) => !c.registrado)
  const fantasmas = pendentes.filter((c) => c.fantasma_provavel)

  return (
    <div>
      <Link to="/vistorias" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Vistorias
      </Link>
      <PageHeader
        title={`Vistoria ${v.cto.descricao}`}
        description={[
          v.olt_nome,
          v.cto.ramal,
          v.pons.length ? `PON ${v.pons.join(', ')}` : null,
          v.tecnico ? `Técnico: ${v.tecnico}` : null,
          finalizada ? `Finalizada em ${new Date(v.finalizada_em as string).toLocaleString('pt-BR')}` : null,
        ]
          .filter(Boolean)
          .join(' · ')}
        action={
          !finalizada && (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => setIdentificacao((n) => n + 1)}>
                <Radio /> Identificar por desconexão
              </Button>
              <Button onClick={() => finalizar.mutate()} disabled={finalizar.isPending || v.portas.length === 0}>
                {finalizar.isPending ? <Loader2 className="animate-spin" /> : <CheckCircle2 />} Finalizar vistoria
              </Button>
            </div>
          )
        }
      />

      {!finalizada && fantasmas.length > 0 && (
        <div className="mb-4 rounded-md bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
          {fantasmas.length} cliente(s) desta caixa com ONT offline e contrato inativo ou parado há dias - prováveis portas a
          liberar. Desconecte os drops sem etiqueta: se nada cair na PON da caixa, é drop fantasma.
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="flex min-w-0 flex-col gap-4">
          {identificacao > 0 && !finalizada && (
            <IdentificacaoAoVivo
              key={identificacao}
              vistoriaId={vistoriaId}
              portasLivres={portasLivres}
              onIdentificado={onIdentificado}
              onReconectado={onReconectado}
              onSemOntAtiva={(porta) =>
                salvar({ porta, resultado: 'sem_ont_ativa', metodo: 'desconexao' })
                  .then(() => {
                    toast.success('Drop fantasma registrado')
                    setIdentificacao(0)
                  })
                  .catch(() => undefined)
              }
              onNovaIdentificacao={() => setIdentificacao((n) => n + 1)}
              onClose={() => setIdentificacao(0)}
            />
          )}
          {etiquetaPorta !== null && (
            <EscolherCliente
              key={`e-${etiquetaPorta}`}
              candidatos={pendentes}
              porta={etiquetaPorta}
              onClose={() => setEtiquetaPorta(null)}
              onEscolher={(serial) =>
                salvar({ porta: etiquetaPorta, resultado: 'cliente', serial, metodo: 'etiqueta' })
                  .then(() => {
                    toast.success(`Porta ${etiquetaPorta} registrada`)
                    setEtiquetaPorta(null)
                  })
                  .catch(() => undefined)
              }
            />
          )}

          {semPorta.length > 0 && (
            <Card className="gap-0 py-0">
              <div className="border-b border-border px-4 py-2.5 text-sm font-semibold">
                Identificados nesta caixa, porta não informada ({semPorta.length})
              </div>
              <div className="flex flex-col divide-y divide-border">
                {semPorta.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    {r.resultado === 'cliente' ? (
                      <RegistroCliente registro={r} />
                    ) : (
                      <Badge variant={resultadoStyles[r.resultado].badge}>{resultadoStyles[r.resultado].label}</Badge>
                    )}
                    {!finalizada && (
                      <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => limpar.mutate(r.id)}>
                        Limpar
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              <div className="px-4 pb-2.5 text-xs text-muted-foreground">
                Para indicar a porta depois, use "Etiqueta" na porta e escolha o mesmo cliente.
              </div>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 2xl:grid-cols-4">
            {Array.from({ length: totalPortas }, (_, i) => i + 1).map((n) => {
              const registro = porNumero.get(n)
              return (
                <PortaCard
                  key={n}
                  numero={n}
                  registro={registro}
                  ativa={etiquetaPorta === n}
                  finalizada={finalizada}
                  onEtiqueta={() => setEtiquetaPorta(n)}
                  onMarcar={(resultado) => salvar({ porta: n, resultado, metodo: 'manual' }).catch(() => undefined)}
                  onLimpar={() => registro && limpar.mutate(registro.id)}
                />
              )
            })}
          </div>
          {!finalizada && (
            <Button variant="ghost" size="sm" className="w-fit" onClick={() => setPortasExtras((x) => x + 1)}>
              <Plus /> Porta a mais (caixa ampliada)
            </Button>
          )}
        </div>

        <Card className="gap-0 self-start py-0">
          <div className="border-b border-border px-4 py-3">
            <div className="font-semibold">Quem deveria estar nesta caixa</div>
            <div className="text-xs text-muted-foreground">
              {pendentes.length} ainda não conferido(s) · {v.portas.length} registro(s)
            </div>
          </div>
          <div className="flex max-h-[70vh] flex-col divide-y divide-border overflow-y-auto">
            {v.candidatos.map((c) => (
              <div key={c.serial} className={cn('px-4 py-2.5 text-sm', c.registrado && 'opacity-60')}>
                <ClienteLinha
                  c={c}
                  extra={
                    c.registrado ? (
                      <Badge variant="success">{c.porta_registrada ? `Porta ${c.porta_registrada}` : 'Identificado'}</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">{papelVistoriaLabel[c.papel]}</span>
                    )
                  }
                />
              </div>
            ))}
            {v.candidatos.length === 0 && (
              <div className="px-4 py-6 text-sm text-muted-foreground">
                Nenhum cliente associado a esta caixa pelo cadastro ou pela rede. Use "Identificar por desconexão" drop a drop.
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
