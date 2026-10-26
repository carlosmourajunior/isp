import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, History, Loader2, Plus, Radio, RotateCcw } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ehAnterior, papelVistoriaLabel, resultadoStyles } from '@/lib/vistoriaStatus'
import type { EventoAoVivo, PortaRegistro, VistoriaDetalhe } from '@/types/vistoria'
import { ClienteLinha } from './ClienteLinha'
import { IdentificacaoAoVivo } from './IdentificacaoAoVivo'
import {
  EscolherCliente,
  PortaCard,
  QuandoRegistrado,
  RegistroCliente,
  type SalvarPorta,
} from './PortaComponentes'

export function VistoriaPage() {
  const { id } = useParams()
  const vistoriaId = Number(id)
  const toast = useToast()
  const queryClient = useQueryClient()
  const [etiquetaPorta, setEtiquetaPorta] = useState<number | null>(null)
  // 0 = painel de desconexão fechado; cada nova identificação troca a key e reinicia o painel.
  const [identificacao, setIdentificacao] = useState(0)

  const navigate = useNavigate()
  const queryKey = useMemo(() => ['/vistorias/', vistoriaId], [vistoriaId])
  const { data: v, isLoading, error } = useQuery({
    queryKey,
    queryFn: async () => (await api.get<VistoriaDetalhe>(`/vistorias/${vistoriaId}/`)).data,
    retry: false,
  })
  // Vistoria antiga da caixa que foi juntada na ficha: vai para a ficha.
  const redirecionar = (error as { response?: { status?: number; data?: { redirecionar_para?: number } } } | null)
    ?.response?.data?.redirecionar_para
  useEffect(() => {
    if (redirecionar) navigate(`/vistorias/${redirecionar}`, { replace: true })
  }, [redirecionar, navigate])
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

  const ajustarCto = useMutation({
    mutationFn: async (acao: { tipo: 'splitter'; portas: 4 | 8 } | { tipo: 'desfazer' } | { tipo: 'porta'; porta: number; inutilizada: boolean }) => {
      if (!v) return
      const base = `/ctos/${v.cto.id}`
      if (acao.tipo === 'splitter') return api.post(`${base}/splitters/`, { portas: acao.portas })
      if (acao.tipo === 'desfazer') return api.delete(`${base}/splitters/`)
      return api.post(`${base}/portas-inutilizadas/`, { porta: acao.porta, inutilizada: acao.inutilizada })
    },
    onSuccess: (_, acao) => {
      if (acao.tipo === 'splitter') toast.success(`Splitter de ${acao.portas} portas adicionado à caixa`)
      if (acao.tipo === 'desfazer') toast.success('Último splitter removido')
      recarregar()
      queryClient.invalidateQueries({ queryKey: ['/ctos/'] })
    },
    onError: (e: unknown) => {
      const erro = (e as { response?: { data?: { error?: string } } }).response?.data?.error
      toast.error('Não foi possível ajustar a caixa', erro)
    },
  })

  const retomar = useMutation({
    mutationFn: async () => (await api.post<{ id: number }>('/vistorias/', { cto: v?.cto.id })).data,
    onSuccess: (r) => {
      toast.success('Vistoria retomada', 'O que já estava registrado aparece como "de vistoria anterior".')
      if (r.id !== vistoriaId) navigate(`/vistorias/${r.id}`)
      else recarregar()
    },
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

  if (error && !redirecionar) {
    return <div className="py-10 text-center text-muted-foreground">Vistoria não encontrada.</div>
  }
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
  const totalPortas = Math.max(v.cto.portas ?? 8, ...comPorta.map((p) => p.porta as number))
  const porNumero = new Map(comPorta.map((p) => [p.porta as number, p]))
  const inutilizadas = new Set(v.cto.portas_inutilizadas)
  const portasLivres = Array.from({ length: totalPortas }, (_, i) => i + 1).filter(
    (n) => !porNumero.has(n) && !inutilizadas.has(n),
  )
  const pendentes = v.candidatos.filter((c) => !c.registrado)
  const anteriores = v.portas.filter((p) => ehAnterior(p, v.sessao_iniciada_em))
  const confirmar = (r: PortaRegistro) =>
    salvar({
      porta: r.porta,
      resultado: r.resultado,
      serial: r.serial || undefined,
      metodo: r.metodo,
      reconexao_confirmada: r.reconexao_confirmada,
      observacao: r.observacao,
    }).catch(() => undefined)
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
          finalizada ? (
            <Button variant="outline" onClick={() => retomar.mutate()} disabled={retomar.isPending}>
              {retomar.isPending ? <Loader2 className="animate-spin" /> : <RotateCcw />} Retomar vistoria
            </Button>
          ) : (
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

      {!finalizada && anteriores.length > 0 && (
        <div className="mb-4 flex items-start gap-2 rounded-md bg-secondary px-3 py-2 text-sm">
          <History className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <span>
            Continuação da vistoria desta caixa: {anteriores.length} registro(s) de vistoria anterior, com borda
            tracejada. Confirme com "Continua assim" ou altere o que mudou; o que não for mexido continua valendo.
          </span>
        </div>
      )}

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
                    <div className="flex flex-col gap-0.5">
                      {r.resultado === 'cliente' ? (
                        <RegistroCliente registro={r} />
                      ) : (
                        <Badge variant={resultadoStyles[r.resultado].badge}>{resultadoStyles[r.resultado].label}</Badge>
                      )}
                      <QuandoRegistrado registro={r} anterior={ehAnterior(r, v.sessao_iniciada_em)} />
                    </div>
                    {!finalizada && (
                      <div className="flex gap-1">
                        {ehAnterior(r, v.sessao_iniciada_em) && (
                          <Button size="sm" variant="outline" onClick={() => confirmar(r)}>
                            Continua assim
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => limpar.mutate(r.id)}>
                          Limpar
                        </Button>
                      </div>
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
                  inutilizada={inutilizadas.has(n)}
                  finalizada={finalizada}
                  onEtiqueta={() => setEtiquetaPorta(n)}
                  onMarcar={(resultado) => salvar({ porta: n, resultado, metodo: 'manual' }).catch(() => undefined)}
                  onLimpar={() => registro && limpar.mutate(registro.id)}
                  onInutilizar={(inutilizada) => ajustarCto.mutate({ tipo: 'porta', porta: n, inutilizada })}
                  anterior={ehAnterior(registro, v.sessao_iniciada_em)}
                  onConfirmar={() => registro && confirmar(registro)}
                />
              )
            })}
          </div>
          <Card className="gap-2 px-4 py-3">
            <div className="text-sm">
              <span className="font-medium">{v.cto.portas ?? '?'} portas</span>
              <span className="text-muted-foreground">
                {' '}
                ({v.cto.portas_base ?? '?'} do projeto
                {v.cto.splitters_extras.map((n, i) => (
                  <span key={i}> + splitter de {n}</span>
                ))}
                ){inutilizadas.size > 0 && ` · ${inutilizadas.size} inutilizada(s)`}
              </span>
            </div>
            {!finalizada && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground">Caixa ampliada? Adicione o splitter instalado:</span>
                <Button size="sm" variant="outline" disabled={ajustarCto.isPending} onClick={() => ajustarCto.mutate({ tipo: 'splitter', portas: 4 })}>
                  <Plus /> Splitter de 4 portas
                </Button>
                <Button size="sm" variant="outline" disabled={ajustarCto.isPending} onClick={() => ajustarCto.mutate({ tipo: 'splitter', portas: 8 })}>
                  <Plus /> Splitter de 8 portas
                </Button>
                {v.cto.splitters_extras.length > 0 && (
                  <Button size="sm" variant="ghost" disabled={ajustarCto.isPending} onClick={() => ajustarCto.mutate({ tipo: 'desfazer' })}>
                    Desfazer último splitter
                  </Button>
                )}
              </div>
            )}
          </Card>
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
