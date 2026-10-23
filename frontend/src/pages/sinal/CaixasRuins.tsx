import { lazy, Suspense, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Cable, ChevronDown, ChevronRight, GitFork, MapPin, Network, Split, User, Waypoints } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardValue } from '@/components/ui/card'
import type { AchadoCaixa, SinalCaixas } from '@/types/sinal'

// Leaflet só carrega quando abre o mapa.
const CaixasMapa = lazy(() => import('./CaixasMapa').then((m) => ({ default: m.CaixasMapa })))

const NIVEIS: Record<AchadoCaixa['nivel'], { label: string; icon: typeof MapPin }> = {
  backbone: { label: 'Cabo de backbone', icon: Cable },
  pon: { label: 'PON inteira', icon: Waypoints },
  ceo: { label: 'Splitter da CEO', icon: Split },
  ramal: { label: 'Ramal', icon: Network },
  cabo: { label: 'Cabo após fusão', icon: GitFork },
  cto: { label: 'Caixa', icon: MapPin },
  clientes: { label: 'Clientes isolados', icon: User },
  sem_caixa: { label: 'Sem caixa', icon: User },
}

const SEVERIDADE: Record<AchadoCaixa['severidade'], { label: string; variant: 'destructive' | 'warning' | 'outline' }> = {
  alta: { label: 'Provável defeito', variant: 'destructive' },
  media: { label: 'Verificar', variant: 'warning' },
  baixa: { label: 'Baixa prioridade', variant: 'outline' },
}

function db(v: number | null | undefined) {
  return v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${v} dB`
}

function Achado({ a, limiar }: { a: AchadoCaixa; limiar: number }) {
  const [aberto, setAberto] = useState(false)
  const Icone = NIVEIS[a.nivel].icon
  return (
    <Card className="gap-0 py-0">
      <button className="flex w-full flex-col gap-2 px-4 py-3 text-left" onClick={() => setAberto((v) => !v)}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 font-medium text-foreground">
            {aberto ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
            <Icone className="size-4 text-muted-foreground" />
            {a.referencia}
            {(a.nivel === 'pon' || a.nivel === 'ceo') && a.alimentacao ? (
              <span className="font-normal text-muted-foreground">· alimentação {a.alimentacao}</span>
            ) : null}
            {a.nivel === 'cto' || a.nivel === 'clientes' ? (
              <span className="font-normal text-muted-foreground">
                · PON {a.pon}
                {a.ramal && ` · ${a.ramal}`}
                {a.cto?.splitter && ` · splitter ${a.cto.splitter}`}
                {a.ceo && ` · sai de ${a.ceo}`}
              </span>
            ) : null}
            {a.olt_nome && <span className="text-xs font-normal text-muted-foreground">({a.olt_nome})</span>}
          </span>
          <span className="flex items-center gap-1.5">
            <Badge variant="outline">{NIVEIS[a.nivel].label}</Badge>
            <Badge variant={SEVERIDADE[a.severidade].variant}>{SEVERIDADE[a.severidade].label}</Badge>
          </span>
        </div>
        <p className="text-sm">{a.diagnostico}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>
            Ruins: <strong className="text-foreground">{a.ruins}</strong> de {a.clientes}
          </span>
          <span>
            Mediana: <span className="font-data text-foreground">{a.mediana} dBm</span> (pior {a.pior})
          </span>
          {a.mediana_referencia !== null && (
            <span>
              Vizinhas: <span className="font-data">{a.mediana_referencia} dBm</span>
              {a.delta_ajustado !== null && (
                <>
                  {' '}
                  · diferença ajustada <span className="font-data">{db(a.delta_ajustado)}</span>
                </>
              )}
            </span>
          )}
          {a.tendencia && <span>Tendência: {a.tendencia.texto}</span>}
        </div>
      </button>
      {aberto && (
        <div className="border-t border-border px-4 py-3">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th className="py-1 pr-3 font-medium">Cliente</th>
                <th className="py-1 pr-3 text-right font-medium">Sinal na OLT</th>
                <th className="py-1 pr-3 text-right font-medium">Sinal na ONU</th>
                <th className="py-1 text-right font-medium">Distância</th>
              </tr>
            </thead>
            <tbody>
              {a.onus.map((o) => (
                <tr key={o.serial} className="border-t border-border/60">
                  <td className="py-1 pr-3">
                    {o.cliente || '—'} <span className="font-data text-xs text-muted-foreground">{o.serial}</span>
                  </td>
                  <td className={cn('py-1 pr-3 text-right font-data', o.sinal < limiar && 'text-destructive')}>{o.sinal}</td>
                  <td className="py-1 pr-3 text-right font-data">{o.ont_rx ?? '—'}</td>
                  <td className="py-1 text-right font-data">{o.distancia !== null ? `${o.distancia} km` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {a.cto && (
            <Link to={`/ctos?cto=${a.cto.id}`} className="mt-2 inline-block text-xs text-primary hover:underline">
              Abrir CTO no mapa
            </Link>
          )}
        </div>
      )}
    </Card>
  )
}

export function CaixasRuins({ oltId }: { oltId: string }) {
  const [limiar, setLimiar] = useState('-26')
  const [nivel, setNivel] = useState('')
  const [severidade, setSeveridade] = useState('')
  const [visao, setVisao] = useState<'lista' | 'mapa'>(() => {
    try {
      return localStorage.getItem('sinal-caixas-visao') === 'mapa' ? 'mapa' : 'lista'
    } catch {
      return 'lista'
    }
  })
  function trocarVisao(v: 'lista' | 'mapa') {
    setVisao(v)
    try {
      localStorage.setItem('sinal-caixas-visao', v)
    } catch {
      /* sem storage: só não lembra */
    }
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['sinal-caixas', oltId, limiar],
    queryFn: async () =>
      (await api.get<SinalCaixas>('/sinal/caixas/', { params: { limiar, ...(oltId ? { olt: oltId } : {}) } })).data,
  })

  const achados = useMemo(
    () =>
      (data?.achados ?? []).filter((a) => (!nivel || a.nivel === nivel) && (!severidade || a.severidade === severidade)),
    [data, nivel, severidade],
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Sinal ruim abaixo de</span>
          <select
            value={limiar}
            onChange={(e) => setLimiar(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          >
            {['-25', '-26', '-27', '-28'].map((v) => (
              <option key={v} value={v}>
                {v} dBm
              </option>
            ))}
          </select>
        </label>
        <SelectFilter
          label="Onde"
          value={nivel}
          onChange={setNivel}
          options={(Object.keys(NIVEIS) as AchadoCaixa['nivel'][]).map((n) => ({
            label: `${NIVEIS[n].label} (${data?.contagem[n] ?? 0})`,
            value: n,
          }))}
        />
        <SelectFilter
          label="Prioridade"
          value={severidade}
          onChange={setSeveridade}
          options={(Object.keys(SEVERIDADE) as AchadoCaixa['severidade'][]).map((s) => ({
            label: SEVERIDADE[s].label,
            value: s,
          }))}
        />
        {isFetching && <span className="text-xs text-muted-foreground">atualizando…</span>}
        <div className="ml-auto inline-flex rounded-md border border-border p-0.5" role="tablist" aria-label="Visão">
          {(['lista', 'mapa'] as const).map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={visao === v}
              onClick={() => trocarVisao(v)}
              className={cn(
                'rounded px-3 py-1 text-sm',
                visao === v ? 'bg-primary/10 font-medium text-primary' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {v === 'lista' ? 'Lista' : 'Mapa'}
            </button>
          ))}
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Card className="gap-1 py-4">
            <CardHeader>
              <CardTitle>ONTs online analisadas</CardTitle>
              <CardValue>{data.onts_analisadas}</CardValue>
            </CardHeader>
          </Card>
          <Card className="gap-1 py-4">
            <CardHeader>
              <CardTitle>Abaixo de {data.limiar} dBm</CardTitle>
              <CardValue>{data.onts_ruins}</CardValue>
            </CardHeader>
          </Card>
          <Card className="gap-1 py-4">
            <CardHeader>
              <CardTitle>Backbone / PONs / CEOs suspeitos</CardTitle>
              <CardValue>
                {(data.contagem.backbone ?? 0) + (data.contagem.pon ?? 0) + (data.contagem.ceo ?? 0) + (data.contagem.ramal ?? 0)}
              </CardValue>
            </CardHeader>
          </Card>
          <Card className="gap-1 py-4">
            <CardHeader>
              <CardTitle>Caixas com provável defeito</CardTitle>
              <CardValue>{data.achados.filter((a) => a.nivel === 'cto' && a.severidade === 'alta').length}</CardValue>
            </CardHeader>
          </Card>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Rede padrão 1:2 → 1:8 (CEO) → 1:8 (CTO). Cada grupo é comparado com o resto da mesma PON: metade da PON ruim
        aponta o 1:8 da CEO; caixas de um cabo que nasce numa fusão apontam a fusão; uma caixa sozinha aponta a caixa,
        descontando o que o splitter do projeto e a distância já explicam (~0,35 dB/km). A tendência compara com 1-2
        semanas atrás. Usa o sinal medido na OLT e só ONTs online.
      </p>

      {visao === 'mapa' ? (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Carregando mapa…</p>}>
          <CaixasMapa oltId={oltId} limiar={limiar} severidade={severidade} nivel={nivel} />
        </Suspense>
      ) : isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : achados.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhuma caixa ou PON com sinal abaixo do limite.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {achados.map((a) => (
            <Achado key={`${a.nivel}-${a.olt_id}-${a.pon}-${a.referencia}`} a={a} limiar={Number(limiar)} />
          ))}
        </div>
      )}
    </div>
  )
}
