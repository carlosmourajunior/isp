import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Loader2, Plus, RefreshCw, UserPlus } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { resultadoStyles } from '@/lib/vistoriaStatus'
import type { CtoDetail } from '@/types/ctos'
import type { VistoriaDetalhe } from '@/types/vistoria'
import {
  EscolherCliente,
  PortaCard,
  QuandoRegistrado,
  RegistroCliente,
  type SalvarPorta,
} from '@/pages/vistorias/PortaComponentes'

type Ajuste =
  | { tipo: 'splitter'; portas: 4 | 8 }
  | { tipo: 'desfazer' }
  | { tipo: 'porta'; porta: number; inutilizada: boolean }
  | { tipo: 'capacidade'; portas: number | null }

function erroDaApi(e: unknown) {
  return (e as { response?: { data?: { error?: string } } }).response?.data?.error
}

/** Edição da caixa no painel da CTO: capacidade e quem está em cada porta (grava na ficha da caixa). */
export function EditorCaixa({ cto }: { cto: CtoDetail }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [escolhendo, setEscolhendo] = useState<{ porta: number | null } | null>(null)
  const [portasTexto, setPortasTexto] = useState(String(cto.portas_base ?? ''))

  const { data: ficha } = useQuery({
    queryKey: ['cto-ficha', cto.id],
    queryFn: async () => (await api.post<{ vistoria_id: number }>(`/ctos/${cto.id}/ficha/`)).data,
    staleTime: Infinity,
  })
  const vid = ficha?.vistoria_id
  const { data: v } = useQuery({
    queryKey: ['/vistorias/', vid],
    queryFn: async () => (await api.get<VistoriaDetalhe>(`/vistorias/${vid}/`)).data,
    enabled: Boolean(vid),
  })

  const recarregar = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['/vistorias/', vid] })
    queryClient.invalidateQueries({ queryKey: ['/ctos/'] })
  }, [queryClient, vid])

  const salvar = useCallback(
    async (dados: SalvarPorta) => {
      try {
        await api.post(`/vistorias/${vid}/portas/`, dados)
        recarregar()
      } catch (e) {
        toast.error('Não foi possível salvar', erroDaApi(e))
        throw e
      }
    },
    [vid, recarregar, toast],
  )

  const limpar = useMutation({
    mutationFn: (registroId: number) => api.delete(`/vistorias/${vid}/registros/${registroId}/`),
    onSuccess: recarregar,
  })

  const ajustar = useMutation({
    mutationFn: async (a: Ajuste) => {
      const base = `/ctos/${cto.id}`
      if (a.tipo === 'splitter') return api.post(`${base}/splitters/`, { portas: a.portas })
      if (a.tipo === 'desfazer') return api.delete(`${base}/splitters/`)
      if (a.tipo === 'capacidade') return api.post(`${base}/capacidade/`, { portas: a.portas })
      return api.post(`${base}/portas-inutilizadas/`, { porta: a.porta, inutilizada: a.inutilizada })
    },
    onSuccess: (r, a) => {
      if (a.tipo === 'capacidade') {
        const base = (r?.data as { portas_base?: number | null } | undefined)?.portas_base
        setPortasTexto(String(base ?? ''))
        toast.success(a.portas === null ? 'Capacidade voltou à do projeto' : `Caixa com ${a.portas} portas`)
      }
      recarregar()
    },
    onError: (e: unknown) => toast.error('Não foi possível ajustar a caixa', erroDaApi(e)),
  })

  const recalcular = useMutation({
    mutationFn: () => api.post(`/vistorias/${vid}/finalizar/`, {}),
    onSuccess: () =>
      toast.success('Recalculando a ocupação', 'Sincroniza com o IXC e refaz a inferência; leva alguns minutos.'),
  })

  if (!v) {
    return (
      <div className="py-10 text-center text-muted-foreground">
        <Loader2 className="mx-auto size-5 animate-spin" />
      </div>
    )
  }

  const comPorta = v.portas.filter((p) => p.porta !== null)
  const semPorta = v.portas.filter((p) => p.porta === null)
  const porNumero = new Map(comPorta.map((p) => [p.porta as number, p]))
  const totalPortas = Math.max(v.cto.portas ?? 8, ...comPorta.map((p) => p.porta as number))
  const inutilizadas = new Set(v.cto.portas_inutilizadas)
  const pendentes = v.candidatos.filter((c) => !c.registrado)
  const ocupadas = v.portas.filter((p) => p.resultado === 'cliente').length
  const portasNumero = Number(portasTexto)
  const capacidadeValida = Number.isInteger(portasNumero) && portasNumero >= 1 && portasNumero <= 64

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-md border border-border p-3">
        <div className="mb-2 text-sm font-semibold">Capacidade</div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Portas da caixa
            <Input
              type="number"
              min={1}
              max={64}
              value={portasTexto}
              onChange={(e) => setPortasTexto(e.target.value)}
              className="h-9 w-24"
            />
          </label>
          <Button
            size="sm"
            disabled={!capacidadeValida || portasNumero === v.cto.portas_base || ajustar.isPending}
            onClick={() => ajustar.mutate({ tipo: 'capacidade', portas: portasNumero })}
          >
            Salvar
          </Button>
          {v.cto.portas_manual !== null && (
            <Button
              size="sm"
              variant="ghost"
              disabled={ajustar.isPending}
              onClick={() => ajustar.mutate({ tipo: 'capacidade', portas: null })}
            >
              Voltar ao projeto ({cto.portas_projeto ?? '?'})
            </Button>
          )}
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          {v.cto.portas ?? '?'} portas no total ({v.cto.portas_base ?? '?'}
          {v.cto.portas_manual !== null ? ' definidas aqui' : ' do projeto'}
          {v.cto.splitters_extras.map((n, i) => (
            <span key={i}> + splitter de {n}</span>
          ))}
          ){inutilizadas.size > 0 && ` · ${inutilizadas.size} inutilizada(s)`} · {ocupadas} com cliente registrado
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={ajustar.isPending} onClick={() => ajustar.mutate({ tipo: 'splitter', portas: 4 })}>
            <Plus /> Splitter de 4
          </Button>
          <Button size="sm" variant="outline" disabled={ajustar.isPending} onClick={() => ajustar.mutate({ tipo: 'splitter', portas: 8 })}>
            <Plus /> Splitter de 8
          </Button>
          {v.cto.splitters_extras.length > 0 && (
            <Button size="sm" variant="ghost" disabled={ajustar.isPending} onClick={() => ajustar.mutate({ tipo: 'desfazer' })}>
              Desfazer último splitter
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold">Quem está em cada porta</div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setEscolhendo({ porta: null })}>
            <UserPlus /> Cliente sem porta
          </Button>
          <Link to={`/vistorias/${v.id}`} className="inline-flex items-center text-xs text-primary hover:underline">
            Abrir vistoria completa
          </Link>
        </div>
      </div>

      {escolhendo && (
        <EscolherCliente
          key={`p-${escolhendo.porta}`}
          candidatos={pendentes}
          porta={escolhendo.porta}
          onClose={() => setEscolhendo(null)}
          onEscolher={(serial) =>
            salvar({ porta: escolhendo.porta, resultado: 'cliente', serial, metodo: 'manual' })
              .then(() => {
                toast.success(escolhendo.porta !== null ? `Porta ${escolhendo.porta} atualizada` : 'Cliente registrado na caixa')
                setEscolhendo(null)
              })
              .catch(() => undefined)
          }
        />
      )}

      {semPorta.length > 0 && (
        <div className="rounded-md border border-border">
          <div className="border-b border-border px-3 py-2 text-xs font-medium text-muted-foreground">
            Na caixa, porta não informada ({semPorta.length})
          </div>
          {semPorta.map((r) => (
            <div key={r.id} className="flex items-center justify-between gap-2 border-b border-border px-3 py-2 last:border-0">
              <div className="flex flex-col gap-0.5">
                {r.resultado === 'cliente' ? (
                  <RegistroCliente registro={r} />
                ) : (
                  <Badge variant={resultadoStyles[r.resultado].badge}>{resultadoStyles[r.resultado].label}</Badge>
                )}
                <QuandoRegistrado registro={r} />
              </div>
              <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => limpar.mutate(r.id)}>
                Tirar
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {Array.from({ length: totalPortas }, (_, i) => i + 1).map((n) => {
          const registro = porNumero.get(n)
          return (
            <PortaCard
              key={n}
              numero={n}
              registro={registro}
              ativa={escolhendo?.porta === n}
              inutilizada={inutilizadas.has(n)}
              finalizada={false}
              onEtiqueta={() => setEscolhendo({ porta: n })}
              onMarcar={(resultado) => salvar({ porta: n, resultado, metodo: 'manual' }).catch(() => undefined)}
              onLimpar={() => registro && limpar.mutate(registro.id)}
              onInutilizar={(inutilizada) => ajustar.mutate({ tipo: 'porta', porta: n, inutilizada })}
            />
          )
        })}
      </div>

      <div className="flex flex-col gap-2 rounded-md bg-secondary px-3 py-2 text-xs text-muted-foreground">
        <span>
          O que você muda aqui vale como vistoria desta caixa: prevalece sobre o cadastro até a correção ir para o IXC
          (aba "Correções para o IXC" em Vistoria de CTO). Clientes colocados aqui saem da ficha de outras caixas.
        </span>
        <Button
          size="sm"
          variant="outline"
          className="w-fit"
          disabled={recalcular.isPending}
          onClick={() => recalcular.mutate()}
        >
          {recalcular.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />} Recalcular ocupação agora
        </Button>
      </div>
    </div>
  )
}
