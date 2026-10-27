import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Link2, Loader2, MapPin, Upload } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import type { CadastroCaixaLog, CaixaForaDoIxc, ForaDoIxcResposta } from '@/types/ctos'

const statusLog: Record<CadastroCaixaLog['status'], 'success' | 'warning' | 'destructive'> = {
  ok: 'success',
  alerta: 'warning',
  erro: 'destructive',
}

function erroDaApi(e: unknown) {
  return (e as { response?: { data?: { error?: string } } }).response?.data?.error
}

/** Caixas do projeto (KMZ) que ainda não existem no IXC: cadastrar ou vincular. */
export function ForaDoIxcTab({ oltId, onSelectCto }: { oltId: string; onSelectCto: (id: number) => void }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [nomes, setNomes] = useState<Record<number, string>>({})
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set())
  const [confirmar, setConfirmar] = useState<CaixaForaDoIxc[] | null>(null)
  const [incluirCd, setIncluirCd] = useState(false)

  const params: Record<string, string> = {}
  if (oltId) params.olt = oltId
  if (incluirCd) params.incluir_cd = '1'
  const { data, isLoading } = useQuery({
    queryKey: ['/ctos/fora-do-ixc/', params],
    queryFn: async () => (await api.get<ForaDoIxcResposta>('/ctos/fora-do-ixc/', { params })).data,
  })

  const nome = (c: CaixaForaDoIxc) => (nomes[c.id] ?? c.nome_sugerido).trim()
  const podeSelecionar = (c: CaixaForaDoIxc) => Boolean(c.modelo && !c.duplicada && nome(c))
  const caixas = useMemo(() => data?.caixas ?? [], [data])
  const escolhidas = caixas.filter((c) => selecionadas.has(c.id) && podeSelecionar(c))
  const selecionaveis = caixas.filter(podeSelecionar)

  const atualizar = () => {
    queryClient.invalidateQueries({ queryKey: ['/ctos/fora-do-ixc/'] })
    queryClient.invalidateQueries({ queryKey: ['/ctos/'] })
  }

  const cadastrar = useMutation({
    mutationFn: async (lista: CaixaForaDoIxc[]) =>
      (
        await api.post<{ resultados: CadastroCaixaLog[]; ok?: number; alerta?: number; erro?: number }>(
          '/ctos/fora-do-ixc/cadastrar/',
          { itens: lista.map((c) => ({ cto: c.id, descricao: nome(c) })) },
        )
      ).data,
    onSuccess: (r) => {
      const resumo = `${r.ok ?? 0} cadastrada(s)${r.alerta ? `, ${r.alerta} para conferir` : ''}${r.erro ? `, ${r.erro} com erro` : ''}.`
      if (r.erro || r.alerta) toast.error('Cadastro no IXC com pendências', `${resumo} Veja a coluna Resultado.`)
      else toast.success('Caixas cadastradas no IXC', resumo)
    },
    onError: (e: unknown) => toast.error('O IXC não foi alterado', erroDaApi(e)),
    onSettled: () => {
      setConfirmar(null)
      setSelecionadas(new Set())
      atualizar()
    },
  })

  const vincular = useMutation({
    mutationFn: async (c: CaixaForaDoIxc) =>
      (await api.post<CadastroCaixaLog>('/ctos/fora-do-ixc/vincular/', { cto: c.id, ixc_cto: c.duplicada?.id })).data,
    onSuccess: (r) => toast.success('Caixas juntadas', r.mensagem),
    onError: (e: unknown) => toast.error('Não foi possível vincular', erroDaApi(e)),
    onSettled: atualizar,
  })

  if (isLoading || !data) return <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />

  const todas = selecionaveis.length > 0 && escolhidas.length === selecionaveis.length

  return (
    <div className="flex flex-col gap-3">
      {!data.pode_cadastrar && (
        <div className="rounded-md bg-secondary px-3 py-2 text-xs text-muted-foreground">{data.motivo}</div>
      )}
      <Card className="gap-0 overflow-hidden py-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <div className="font-semibold">Caixas do projeto que não existem no IXC ({caixas.length})</div>
            <div className="text-xs text-muted-foreground">
              Sem cadastro no IXC a caixa não recebe clientes lá. Projeto, cidade e transmissor são copiados da caixa do
              IXC mais próxima (coluna Modelo).
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <input type="checkbox" className="accent-primary" checked={incluirCd} onChange={(e) => setIncluirCd(e.target.checked)} />
              Incluir CDs/CEOs
            </label>
            {data.pode_cadastrar && (
              <Button size="sm" disabled={escolhidas.length === 0} onClick={() => setConfirmar(escolhidas)}>
                <Upload /> Cadastrar selecionadas no IXC ({escolhidas.length})
              </Button>
            )}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="w-8 px-3 py-2">
                  <input
                    type="checkbox"
                    aria-label="Selecionar todas"
                    className="size-4 accent-primary"
                    checked={todas}
                    disabled={!data.pode_cadastrar || selecionaveis.length === 0}
                    onChange={() => setSelecionadas(todas ? new Set() : new Set(selecionaveis.map((c) => c.id)))}
                  />
                </th>
                <th className="px-3 py-2 font-medium">Nome no IXC</th>
                <th className="px-3 py-2 font-medium">Projeto</th>
                <th className="px-3 py-2 font-medium">Portas</th>
                <th className="px-3 py-2 font-medium">Modelo (IXC)</th>
                <th className="px-3 py-2 font-medium">Resultado</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {caixas.map((c) => (
                <tr key={c.id} className={cn('border-b border-border align-top last:border-0', selecionadas.has(c.id) && 'bg-primary/5')}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      aria-label={`Selecionar ${c.descricao}`}
                      className="size-4 accent-primary"
                      checked={selecionadas.has(c.id)}
                      disabled={!data.pode_cadastrar || !podeSelecionar(c)}
                      onChange={() =>
                        setSelecionadas((s) => {
                          const n = new Set(s)
                          if (n.has(c.id)) n.delete(c.id)
                          else n.add(c.id)
                          return n
                        })
                      }
                    />
                  </td>
                  <td className="px-3 py-2">
                    <Input
                      value={nomes[c.id] ?? c.nome_sugerido}
                      placeholder="Dê um nome (ex.: CA_301)"
                      onChange={(e) => setNomes((n) => ({ ...n, [c.id]: e.target.value }))}
                      className="h-8 w-44"
                    />
                    {!c.nome_sugerido && <div className="mt-0.5 text-xs text-muted-foreground">Sem nome no projeto</div>}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {c.tipo && <Badge variant="outline" className="mr-1">{c.tipo}</Badge>}
                    {c.ramal || '—'}
                    {c.ceo && <div className="text-muted-foreground">{c.ceo}</div>}
                    {c.clientes_na_vistoria > 0 && (
                      <div className="text-muted-foreground">{c.clientes_na_vistoria} cliente(s) na vistoria</div>
                    )}
                  </td>
                  <td className="px-3 py-2">{c.portas ?? '?'}</td>
                  <td className="px-3 py-2 text-xs">
                    {c.duplicada ? (
                      <span className="flex items-start gap-1 text-amber-700 dark:text-amber-400">
                        <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
                        Parece já existir no IXC: {c.duplicada.descricao} (id {c.duplicada.ixc_id})
                      </span>
                    ) : c.modelo ? (
                      <>
                        {c.modelo.descricao} · projeto {c.modelo.id_projeto || '?'}
                        <div className="text-muted-foreground">a {c.modelo.distancia_m} m</div>
                      </>
                    ) : (
                      <span className="text-destructive">Nenhuma caixa do IXC por perto</span>
                    )}
                  </td>
                  <td className="max-w-xs px-3 py-2 text-xs">
                    {c.ultimo_cadastro && (
                      <>
                        <Badge variant={statusLog[c.ultimo_cadastro.status]}>{c.ultimo_cadastro.status}</Badge>
                        <div className="mt-0.5 text-muted-foreground">{c.ultimo_cadastro.mensagem}</div>
                      </>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    {c.duplicada && data.pode_cadastrar && (
                      <Button size="sm" variant="outline" disabled={vincular.isPending} onClick={() => vincular.mutate(c)}>
                        <Link2 /> Vincular
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" title="Ver no mapa" onClick={() => onSelectCto(c.id)}>
                      <MapPin />
                    </Button>
                  </td>
                </tr>
              ))}
              {caixas.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
                    Todas as caixas do projeto já estão no IXC.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <ConfirmDialog
        open={confirmar !== null}
        title={`Cadastrar ${confirmar?.length ?? 0} caixa(s) no IXC?`}
        description={
          confirmar && (
            <>
              <ul className="mb-2 max-h-48 overflow-y-auto">
                {confirmar.map((c) => (
                  <li key={c.id}>
                    <strong>{nome(c)}</strong>: {c.portas ?? '?'} portas, como {c.modelo?.descricao} (projeto{' '}
                    {c.modelo?.id_projeto || '?'})
                  </li>
                ))}
              </ul>
              Cada caixa é criada e conferida no IXC; a vistoria e os ajustes continuam ligados a ela.
            </>
          )
        }
        confirmLabel="Cadastrar no IXC"
        isLoading={cadastrar.isPending}
        onConfirm={() => confirmar && cadastrar.mutate(confirmar)}
        onCancel={() => setConfirmar(null)}
      />
    </div>
  )
}
