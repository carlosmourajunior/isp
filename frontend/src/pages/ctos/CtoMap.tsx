import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { situacaoStyles } from '@/lib/ctoStatus'
import type { Cto, CtoSituacao } from '@/types/ctos'

interface CtoMapProps {
  ctos: Cto[]
  selectedId: number | null
  onSelect: (id: number) => void
}

/** Reenquadra o mapa quando o conjunto de CTOs muda (troca de OLT/filtro). */
function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap()
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [24, 24] })
  }, [map, bounds])
  return null
}

export function CtoMap({ ctos, selectedId, onSelect }: CtoMapProps) {
  const comCoordenadas = useMemo(
    () => ctos.filter((c) => c.latitude !== null && c.longitude !== null),
    [ctos],
  )

  const bounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (comCoordenadas.length === 0) return null
    const lats = comCoordenadas.map((c) => c.latitude as number)
    const lons = comCoordenadas.map((c) => c.longitude as number)
    return [
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)],
    ]
    // Só reenquadra quando muda o conjunto, não a cada refetch com os mesmos ids.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comCoordenadas.map((c) => c.id).join(',')])

  return (
    <div className="relative isolate h-[65vh] min-h-[420px] overflow-hidden rounded-xl border border-border">
      <MapContainer center={[-22.27, -46.17]} zoom={14} className="h-full w-full" preferCanvas>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds bounds={bounds} />
        {comCoordenadas.map((cto) => {
          const estilo = situacaoStyles[cto.situacao]
          const selecionada = cto.id === selectedId
          return (
            <CircleMarker
              key={`${cto.id}-${selecionada}`}
              center={[cto.latitude as number, cto.longitude as number]}
              radius={selecionada ? 10 : cto.tipo === 'CD' ? 4 : 7}
              pathOptions={{
                color: selecionada ? '#111827' : cto.situacao === 'acima' ? '#7f1d1d' : estilo.color,
                weight: selecionada ? 3 : cto.situacao === 'acima' ? 3 : 1.5,
                fillColor: estilo.color,
                fillOpacity: cto.origem === 'kmz' ? 0.35 : 0.8,
                dashArray: cto.origem === 'kmz' ? '3 3' : undefined,
              }}
              eventHandlers={{ click: () => onSelect(cto.id) }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <div className="text-xs">
                  <div className="font-semibold">{cto.descricao}</div>
                  <div>
                    {cto.ocupadas}/{cto.portas ?? '?'} ocupadas
                    {cto.possiveis > 0 && ` (+${cto.possiveis} possíveis)`}
                  </div>
                  <div>{estilo.label}</div>
                  {cto.ramal && <div>{cto.ramal}</div>}
                  {cto.origem === 'kmz' && <div>Só no projeto (fora do IXC)</div>}
                </div>
              </Tooltip>
            </CircleMarker>
          )
        })}
      </MapContainer>

      <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-md border border-border bg-background/95 px-3 py-2 text-xs shadow-sm">
        {(Object.keys(situacaoStyles) as CtoSituacao[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <span className="inline-block size-2.5 rounded-full" style={{ backgroundColor: situacaoStyles[s].color }} />
            {situacaoStyles[s].label}
          </div>
        ))}
        <div className="mt-1 flex items-center gap-2 text-muted-foreground">
          <span className="inline-block size-2.5 rounded-full border border-dashed border-muted-foreground" />
          Tracejada: só no projeto (KMZ)
        </div>
      </div>

      {comCoordenadas.length < ctos.length && (
        <div className="pointer-events-none absolute right-3 top-3 z-[1000] rounded-md border border-border bg-background/95 px-3 py-1.5 text-xs text-muted-foreground shadow-sm">
          {ctos.length - comCoordenadas.length} CTO(s) sem coordenadas não aparecem no mapa
        </div>
      )}
    </div>
  )
}
