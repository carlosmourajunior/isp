import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { CircleMarker, MapContainer, Polygon, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression, LatLngTuple } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { statusStyles } from '@/lib/status'
import { Badge } from '@/components/ui/badge'
import type { CaixaNoMapa, SinalCaixasMapa } from '@/types/sinal'

type Achado = SinalCaixasMapa['achados'][number]

const COR_SEVERIDADE: Record<Achado['severidade'], string> = {
  alta: statusStyles.critical.dot,
  media: statusStyles.warning.dot,
  baixa: '#6b7280',
}

const NIVEL_CURTO: Record<Achado['nivel'], string> = {
  backbone: 'Backbone',
  pon: 'PON',
  ceo: 'CEO',
  ramal: 'Ramal',
  cabo: 'Cabo',
  cto: 'Caixa',
  clientes: 'Clientes',
  sem_caixa: 'Sem caixa',
}

function corCaixa(c: CaixaNoMapa, limiar: number) {
  if (c.ruins === 0) return statusStyles.good.dot
  if (c.ruins / c.clientes >= 0.6 || c.mediana < limiar) return statusStyles.critical.dot
  return statusStyles.warning.dot
}

/** Contorno convexo (monotone chain) para desenhar a área de um problema de grupo. */
function contorno(pontos: LatLngTuple[]): LatLngTuple[] {
  const p = [...pontos].sort((a, b) => a[1] - b[1] || a[0] - b[0])
  if (p.length < 3) return p
  const cruz = (o: LatLngTuple, a: LatLngTuple, b: LatLngTuple) =>
    (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])
  const baixo: LatLngTuple[] = []
  for (const x of p) {
    while (baixo.length >= 2 && cruz(baixo[baixo.length - 2], baixo[baixo.length - 1], x) <= 0) baixo.pop()
    baixo.push(x)
  }
  const cima: LatLngTuple[] = []
  for (const x of [...p].reverse()) {
    while (cima.length >= 2 && cruz(cima[cima.length - 2], cima[cima.length - 1], x) <= 0) cima.pop()
    cima.push(x)
  }
  return [...baixo.slice(0, -1), ...cima.slice(0, -1)]
}

function Enquadrar({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap()
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [32, 32], maxZoom: 17 })
  }, [map, bounds])
  return null
}

function limites(pontos: LatLngTuple[]): LatLngBoundsExpression | null {
  if (pontos.length === 0) return null
  const lats = pontos.map((p) => p[0])
  const lons = pontos.map((p) => p[1])
  return [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ]
}

export function CaixasMapa({
  oltId,
  limiar,
  severidade,
  nivel,
}: {
  oltId: string
  limiar: string
  severidade: string
  nivel: string
}) {
  const [selecionado, setSelecionado] = useState<number | null>(null)
  const { data, isLoading } = useQuery({
    queryKey: ['sinal-caixas-mapa', oltId, limiar],
    queryFn: async () =>
      (await api.get<SinalCaixasMapa>('/sinal/caixas/mapa/', { params: { limiar, ...(oltId ? { olt: oltId } : {}) } }))
        .data,
  })

  const caixas = useMemo(() => new Map((data?.caixas ?? []).map((c) => [c.id, c])), [data])
  const achados = useMemo(
    () =>
      (data?.achados ?? []).filter(
        (a) => a.ctos.length > 0 && (!severidade || a.severidade === severidade) && (!nivel || a.nivel === nivel),
      ),
    [data, severidade, nivel],
  )
  const atual = achados.find((a) => a.indice === selecionado) ?? null
  const destacadas = useMemo(() => new Set(atual?.ctos ?? []), [atual])
  // Para cada caixa, o achado mais grave que a envolve (cor do contorno no mapa geral).
  const achadoDaCaixa = useMemo(() => {
    const m = new Map<number, Achado>()
    for (const a of achados) for (const id of a.ctos) if (!m.has(id)) m.set(id, a)
    return m
  }, [achados])

  const pontosAtual = (atual?.ctos ?? [])
    .map((id) => caixas.get(id))
    .filter((c): c is CaixaNoMapa => Boolean(c))
    .map((c) => [c.lat, c.lon] as LatLngTuple)
  const bounds = useMemo(
    () => limites(atual ? pontosAtual : (data?.caixas ?? []).map((c) => [c.lat, c.lon] as LatLngTuple)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [atual?.indice, data],
  )
  const grupos = achados.filter((a) => !['cto', 'clientes', 'sem_caixa'].includes(a.nivel))

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando mapa…</p>
  const lim = Number(limiar)

  return (
    <div className="grid gap-3 lg:grid-cols-[320px_1fr]">
      <div className="flex max-h-[70vh] flex-col gap-1.5 overflow-y-auto pr-1">
        {achados.length === 0 && <p className="text-sm text-muted-foreground">Nada para mostrar no mapa.</p>}
        {achados.map((a) => (
          <button
            key={a.indice}
            onClick={() => setSelecionado(a.indice === selecionado ? null : a.indice)}
            className={cn(
              'rounded-md border px-3 py-2 text-left text-sm transition-colors',
              a.indice === selecionado ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/50',
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 font-medium">
                <span className="inline-block size-2 rounded-full" style={{ background: COR_SEVERIDADE[a.severidade] }} />
                {a.referencia}
              </span>
              <Badge variant="outline">{NIVEL_CURTO[a.nivel]}</Badge>
            </div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {a.ruins}/{a.clientes} ruins · mediana {a.mediana} dBm · {a.ctos.length} caixa(s)
            </div>
            {a.indice === selecionado && <p className="mt-1.5 text-xs">{a.diagnostico}</p>}
          </button>
        ))}
      </div>

      <div className="relative isolate h-[70vh] min-h-[420px] overflow-hidden rounded-xl border border-border">
        <MapContainer center={[-22.27, -46.17]} zoom={14} className="h-full w-full" preferCanvas>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Enquadrar bounds={bounds} />

          {(atual ? [atual] : grupos).map((a) => {
            const pts = a.ctos
              .map((id) => caixas.get(id))
              .filter((c): c is CaixaNoMapa => Boolean(c))
              .map((c) => [c.lat, c.lon] as LatLngTuple)
            if (pts.length < 3) return null
            return (
              <Polygon
                key={`g-${a.indice}`}
                positions={contorno(pts)}
                pathOptions={{
                  color: COR_SEVERIDADE[a.severidade],
                  weight: atual ? 3 : 2,
                  dashArray: '6 4',
                  fillOpacity: atual ? 0.12 : 0.05,
                }}
                eventHandlers={{ click: () => setSelecionado(a.indice) }}
              >
                <Tooltip sticky>
                  <div className="text-xs font-semibold">{a.referencia}</div>
                </Tooltip>
              </Polygon>
            )
          })}

          {(data?.caixas ?? []).map((c) => {
            const emDestaque = destacadas.has(c.id)
            const apagada = atual !== null && !emDestaque
            const achado = achadoDaCaixa.get(c.id)
            return (
              <CircleMarker
                key={`${c.id}-${emDestaque}-${apagada}`}
                center={[c.lat, c.lon]}
                radius={emDestaque ? 9 : 6}
                pathOptions={{
                  color: emDestaque ? '#111827' : corCaixa(c, lim),
                  weight: emDestaque ? 3 : 1.5,
                  fillColor: corCaixa(c, lim),
                  fillOpacity: apagada ? 0.25 : 0.85,
                  opacity: apagada ? 0.4 : 1,
                }}
                eventHandlers={{ click: () => achado && setSelecionado(achado.indice) }}
              >
                <Tooltip direction="top" offset={[0, -6]}>
                  <div className="text-xs">
                    <div className="font-semibold">{c.descricao}</div>
                    <div>
                      {c.ruins}/{c.clientes} ruins · mediana {c.mediana} · pior {c.pior} dBm
                    </div>
                    <div>
                      PON {c.pon}
                      {c.ceo && ` · ${c.ceo}`}
                    </div>
                    {achado && <div className="mt-0.5 font-medium">{achado.referencia}</div>}
                  </div>
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>

        <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-md border border-border bg-background/95 px-3 py-2 text-xs shadow-sm">
          <div className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full" style={{ background: statusStyles.critical.dot }} />
            Caixa ruim (maioria abaixo de {limiar})
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full" style={{ background: statusStyles.warning.dot }} />
            Alguns clientes ruins
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full" style={{ background: statusStyles.good.dot }} />
            Boa (mesma PON, referência)
          </div>
          <div className="mt-1 text-muted-foreground">Tracejado: área de um problema de grupo (CEO, cabo, PON)</div>
        </div>
        {atual && (
          <div className="absolute right-3 top-3 z-[1000] flex gap-2">
            {atual.nivel === 'cto' && atual.ctos[0] && (
              <Link
                to={`/ctos?cto=${atual.ctos[0]}`}
                className="rounded-md border border-border bg-background/95 px-3 py-1.5 text-xs text-primary shadow-sm hover:underline"
              >
                Abrir CTO
              </Link>
            )}
            <button
              onClick={() => setSelecionado(null)}
              className="rounded-md border border-border bg-background/95 px-3 py-1.5 text-xs shadow-sm"
            >
              Ver todos
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
