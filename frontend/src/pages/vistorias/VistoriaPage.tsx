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

type Acao = { tipo: 'etiqueta' | 'desconexao'; porta: number } | null

interface SalvarPorta {
  porta: number
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
      ? candidatos.filter((c) => c.cliente_nome.toLowerCase().includes(t) || c.serial.toLowerCase().includes(t))
      : candidatos
  }, [candidatos, termo])

  const { data: fora, isFetching } = useQuery({
    queryKey: ['/vistorias/clientes/', termo],
    queryFn: async () => (await api.get<ClienteInfo[]>('/vistorias/clientes/', { params: { q: termo } })).data,
    enabled: termo.trim().length >= 3 && filtrados.length === 0,
  })

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
      <div className="flex flex-col gap-2 px-4 py-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Nome que o técnico leu na etiqueta…"
            className="pl-8"
          />
        </div>
        {filtrados.length > 0 ? (
          <div className="flex max-h-80 flex-col gap-1 overflow-y-auto">
            {filtrados.map((c) => (
              <button
                key={c.serial}
                type="button"
                onClick={() => onEscolher(c.serial)}
                className="rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-accent"
              >
                <ClienteLinha c={c} />
              </button>
            ))}
          </div>
        ) : termo.trim().length >= 3 ? (
          <div className="flex flex-col gap-1">
            <div className="text-xs text-amber-700 dark:text-amber-400">
              Não está entre os candidatos desta caixa - o cadastro dele aponta outra CTO. Resultados no cadastro todo:
            </div>
            {isFetching && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
            {(fora ?? []).map((c) => (
              <button
                key={c.serial}
                type="button"
                onClick={() => onEscolher(c.serial)}
                className="rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-accent"
              >
                <ClienteLinha
                  c={c}
                  extra={c.cto_provavel && <span className="text-xs text-muted-foreground">rede aponta {c.cto_provavel.descricao}</span>}
                />
              </button>
            ))}
            {!isFetching && fora?.length === 0 && (
              <div className="text-sm text-muted-foreground">Nenhum cliente com esse nome. Tente por desconexão.</div>
            )}
          </div>
        ) : (
          <div className="text-xs text-muted-foreground">Digite pelo menos 3 letras para buscar fora da lista.</div>
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
  onAcao,
  onMarcar,
  onLimpar,
}: {
  numero: number
  registro?: PortaRegistro
  ativa: boolean
  finalizada: boolean
  onAcao: (tipo: 'etiqueta' | 'desconexao') => void
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

      {registro?.resultado === 'cliente' && (
        <div className="text-sm">
          <div className="font-medium">{registro.cliente_nome || registro.serial}</div>
          <div className="text-xs text-muted-foreground">
            {registro.serial} · {registro.metodo === 'desconexao' ? 'por desconexão' : 'por etiqueta'}
            {registro.reconexao_confirmada && (
              <span className="ml-1 inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-3" /> voltou
              </span>
            )}
          </div>
        </div>
      )}

      {!finalizada && (
        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="outline" onClick={() => onAcao('etiqueta')}>
            <Tag /> Etiqueta
          </Button>
          <Button size="sm" variant="outline" onClick={() => onAcao('desconexao')}>
            <Radio /> Desconexão
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

export function VistoriaPage() {
  const { id } = useParams()
  const vistoriaId = Number(id)
  const toast = useToast()
  const queryClient = useQueryClient()
  const [acao, setAcao] = useState<Acao>(null)
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
        toast.error('Não foi possível salvar a porta')
        throw new Error('falha ao salvar')
      }
    },
    [vistoriaId, recarregar, toast],
  )

  const limpar = useMutation({
    mutationFn: (porta: number) => api.delete(`/vistorias/${vistoriaId}/portas/${porta}/`),
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

  if (isLoading || !v) {
    return (
      <div className="py-10 text-center text-muted-foreground">
        <Loader2 className="mx-auto size-5 animate-spin" />
      </div>
    )
  }

  const finalizada = Boolean(v.finalizada_em)
  const totalPortas = Math.max(v.cto.portas ?? 8, ...v.portas.map((p) => p.porta)) + portasExtras
  const porNumero = new Map(v.portas.map((p) => [p.porta, p]))
  const pendentes = v.candidatos.filter((c) => c.porta_registrada === null)
  const fantasmas = pendentes.filter((c) => c.fantasma_provavel)
  const registradas = v.portas.length

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
            <Button onClick={() => finalizar.mutate()} disabled={finalizar.isPending || registradas === 0}>
              {finalizar.isPending ? <Loader2 className="animate-spin" /> : <CheckCircle2 />} Finalizar vistoria
            </Button>
          )
        }
      />

      {!finalizada && fantasmas.length > 0 && (
        <div className="mb-4 rounded-md bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
          {fantasmas.length} cliente(s) desta caixa com ONT offline e contrato inativo ou parado há dias - prováveis portas a
          liberar. Ao identificar, use "Desconexão": se nada cair, a porta é fantasma.
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="flex min-w-0 flex-col gap-4">
          {acao?.tipo === 'desconexao' && (
            <IdentificacaoAoVivo
              key={`d-${acao.porta}`}
              vistoriaId={vistoriaId}
              porta={acao.porta}
              onIdentificado={(e: EventoAoVivo) =>
                salvar({ porta: acao.porta, resultado: 'cliente', serial: e.serial, metodo: 'desconexao' })
              }
              onReconectado={(e: EventoAoVivo) =>
                salvar({
                  porta: acao.porta,
                  resultado: 'cliente',
                  serial: e.serial,
                  metodo: 'desconexao',
                  reconexao_confirmada: true,
                })
              }
              onSemOntAtiva={() =>
                salvar({ porta: acao.porta, resultado: 'sem_ont_ativa', metodo: 'desconexao' })
                  .then(() => setAcao(null))
                  .catch(() => undefined)
              }
              onClose={() => setAcao(null)}
            />
          )}
          {acao?.tipo === 'etiqueta' && (
            <EscolherCliente
              key={`e-${acao.porta}`}
              candidatos={pendentes}
              porta={acao.porta}
              onClose={() => setAcao(null)}
              onEscolher={(serial) =>
                salvar({ porta: acao.porta, resultado: 'cliente', serial, metodo: 'etiqueta' })
                  .then(() => {
                    toast.success(`Porta ${acao.porta} registrada`)
                    setAcao(null)
                  })
                  .catch(() => undefined)
              }
            />
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 2xl:grid-cols-4">
            {Array.from({ length: totalPortas }, (_, i) => i + 1).map((n) => (
              <PortaCard
                key={n}
                numero={n}
                registro={porNumero.get(n)}
                ativa={acao?.porta === n}
                finalizada={finalizada}
                onAcao={(tipo) => setAcao({ tipo, porta: n })}
                onMarcar={(resultado) => salvar({ porta: n, resultado, metodo: 'manual' }).catch(() => undefined)}
                onLimpar={() => limpar.mutate(n)}
              />
            ))}
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
              {pendentes.length} ainda não conferido(s) · {registradas} porta(s) registrada(s)
            </div>
          </div>
          <div className="flex max-h-[70vh] flex-col divide-y divide-border overflow-y-auto">
            {v.candidatos.map((c) => (
              <div key={c.serial} className={cn('px-4 py-2.5 text-sm', c.porta_registrada !== null && 'opacity-60')}>
                <ClienteLinha
                  c={c}
                  extra={
                    c.porta_registrada !== null ? (
                      <Badge variant="success">Porta {c.porta_registrada}</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">{papelVistoriaLabel[c.papel]}</span>
                    )
                  }
                />
              </div>
            ))}
            {v.candidatos.length === 0 && (
              <div className="px-4 py-6 text-sm text-muted-foreground">
                Nenhum cliente associado a esta caixa pelo cadastro ou pela rede. Use "Desconexão" porta a porta.
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
