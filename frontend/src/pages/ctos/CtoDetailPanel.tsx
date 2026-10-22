import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ClipboardCheck, Loader2, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { papelStyles, situacaoStyles } from '@/lib/ctoStatus'
import { operStateStatus, statusStyles } from '@/lib/status'
import type { CtoCliente, CtoDetail, CtoPapel } from '@/types/ctos'

interface CtoDetailPanelProps {
  ctoId: number
  onClose: () => void
  onSelect: (id: number) => void
}

function Numero({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div title={hint}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold text-foreground">{value}</div>
    </div>
  )
}

function CtoLink({ cto, onSelect }: { cto: CtoCliente['cto_provavel']; onSelect: (id: number) => void }) {
  if (!cto) return <span className="text-muted-foreground">—</span>
  return (
    <button type="button" className="text-primary hover:underline" onClick={() => onSelect(cto.id)}>
      {cto.descricao}
    </button>
  )
}

function motivoPrincipal(cliente: CtoCliente): string {
  const lista = cliente.papel === 'suspeito' ? cliente.motivos.cadastro : cliente.motivos.provavel
  return (lista ?? []).join('; ')
}

const ordemPapeis: CtoPapel[] = ['confirmado', 'provavel', 'veio_de_outra', 'possivel', 'suspeito']

export function CtoDetailPanel({ ctoId, onClose, onSelect }: CtoDetailPanelProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['/ctos/', ctoId],
    queryFn: async () => (await api.get<CtoDetail>(`/ctos/${ctoId}/`)).data,
  })
  const navigate = useNavigate()
  const iniciarVistoria = useMutation({
    mutationFn: async () => (await api.post<{ id: number }>('/vistorias/', { cto: ctoId })).data,
    onSuccess: (v) => navigate(`/vistorias/${v.id}`),
  })

  return (
    <Card className="gap-0 py-0">
      <div className="flex items-start justify-between border-b border-border px-4 py-3">
        <div>
          <div className="text-base font-semibold text-foreground">{data?.descricao ?? '…'}</div>
          {data && (
            <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
              <Badge variant={situacaoStyles[data.situacao].badge}>{situacaoStyles[data.situacao].label}</Badge>
              {data.ramal && <span>{data.ramal}</span>}
              {data.splitter && <span>· splitter {data.splitter}</span>}
              {data.pons.length > 0 && <span>· PON {data.pons.join(', ')}</span>}
              {data.origem === 'kmz' && <Badge variant="outline">Só no projeto (fora do IXC)</Badge>}
            </div>
          )}
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-muted-foreground hover:bg-accent" aria-label="Fechar">
          <X className="size-4" />
        </button>
      </div>

      {isLoading || !data ? (
        <div className="px-4 py-10 text-center text-muted-foreground">
          <Loader2 className="mx-auto size-5 animate-spin" />
        </div>
      ) : (
        <div className="flex flex-col gap-4 px-4 py-4">
          <div className="grid grid-cols-3 gap-3">
            <Numero
              label="Ocupadas (estimado)"
              value={`${data.ocupadas}/${data.portas_uteis ?? '?'}`}
              hint="Confirmados + prováveis + cadastrados em outra CTO que a rede aponta para esta, sobre as portas úteis"
            />
            <Numero label="Livres (estimado)" value={data.livres ?? '?'} />
            <Numero label="No cadastro IXC" value={data.ixc_id ? data.cadastro_ixc : '—'} />
            <Numero label="Possíveis" value={data.possiveis} hint="Melhor candidata é esta, mas sem certeza" />
            <Numero
              label="Offline"
              value={data.offline}
              hint="ONTs atribuídas a esta CTO que estão offline - podem ser portas a liberar"
            />
            <Numero label="Provavelmente em outra" value={data.suspeitos} hint="Cadastrados aqui, rede aponta outra CTO" />
          </div>

          {(data.splitters_extras.length > 0 || data.portas_inutilizadas.length > 0) && (
            <p className="text-xs text-muted-foreground">
              {data.portas_base ?? '?'} portas no projeto
              {data.splitters_extras.map((n, i) => (
                <span key={i}> + splitter de {n}</span>
              ))}
              {data.portas_inutilizadas.length > 0 && ` · porta(s) inutilizada(s): ${data.portas_inutilizadas.join(', ')}`}
            </p>
          )}

          <Button
            size="sm"
            variant="outline"
            className="w-fit"
            disabled={iniciarVistoria.isPending}
            onClick={() => iniciarVistoria.mutate()}
          >
            <ClipboardCheck /> Iniciar vistoria desta caixa
          </Button>

          {data.offline > 0 && (
            <p className="rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
              {data.offline} ONT(s) desta caixa estão offline. Se o contrato estiver cancelado, a porta pode ser liberada.
            </p>
          )}

          {ordemPapeis.map((papel) => {
            const lista = data.clientes.filter((c) => c.papel === papel)
            if (lista.length === 0) return null
            return (
              <div key={papel}>
                <div className="mb-1.5 flex items-center gap-2">
                  <Badge variant={papelStyles[papel].badge}>{papelStyles[papel].label}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {lista.length} · {papelStyles[papel].descricao}
                  </span>
                </div>
                <div className="overflow-x-auto rounded-md border border-border">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="px-2 py-1.5 font-medium">Cliente</th>
                        <th className="px-2 py-1.5 font-medium">PON/pos</th>
                        <th className="px-2 py-1.5 font-medium">Dist.</th>
                        <th className="px-2 py-1.5 font-medium">Estado</th>
                        <th className="px-2 py-1.5 font-medium">{papel === 'suspeito' ? 'Rede aponta' : 'Cadastro IXC'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lista.map((c) => {
                        const estado = operStateStatus(c.oper_state)
                        return (
                          <tr key={c.id} className="border-b border-border last:border-0" title={motivoPrincipal(c)}>
                            <td className="px-2 py-1.5">
                              <div className="font-medium text-foreground">{c.cliente_nome || '(sem cliente no IXC)'}</div>
                              <div className="text-muted-foreground">{c.serial}</div>
                            </td>
                            <td className="whitespace-nowrap px-2 py-1.5">
                              {c.pon}/{c.position}
                            </td>
                            <td className="whitespace-nowrap px-2 py-1.5">
                              {c.distance_km !== null ? `${c.distance_km.toFixed(1)} km` : '—'}
                            </td>
                            <td className="px-2 py-1.5">
                              <span className="inline-flex items-center gap-1">
                                <span
                                  className="inline-block size-2 rounded-full"
                                  style={{ backgroundColor: statusStyles[estado].dot }}
                                />
                                {c.oper_state ?? '—'}
                              </span>
                            </td>
                            <td className="px-2 py-1.5">
                              <CtoLink cto={papel === 'suspeito' ? c.cto_provavel : c.cto_cadastro} onSelect={onSelect} />
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })}

          {data.clientes.length === 0 && (
            <p className="text-sm text-muted-foreground">Nenhum cliente associado a esta CTO pela inferência.</p>
          )}
          <p className="text-xs text-muted-foreground">
            Passe o mouse sobre um cliente para ver por que ele foi associado.
            {data.calculado_em && ` Calculado em ${new Date(data.calculado_em).toLocaleString('pt-BR')}.`}
          </p>
        </div>
      )}
    </Card>
  )
}
