import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, MapPin, Waypoints } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { statusStyles, type StatusLevel } from '@/lib/status'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardValue } from '@/components/ui/card'
import { useOlts } from '@/hooks/useOlts'
import { OnuListPage } from '@/pages/onus/OnuListPage'
import type { SinalResumo, SinalVariacao, TipoVariacao, VariacaoItem } from '@/types/sinal'

type Faixa = 'critico' | 'alerta' | 'bom'

const FAIXAS: { id: Faixa; label: string; detalhe: string; nivel: StatusLevel; filtro: Record<string, string> }[] = [
  { id: 'critico', label: 'Crítico', detalhe: 'abaixo de -29 dBm', nivel: 'critical', filtro: { olt_rx_sig__lt: '-29' } },
  {
    id: 'alerta',
    label: 'Alerta',
    detalhe: 'entre -27 e -29 dBm',
    nivel: 'warning',
    filtro: { olt_rx_sig__gte: '-29', olt_rx_sig__lte: '-27' },
  },
  { id: 'bom', label: 'Bom', detalhe: 'acima de -27 dBm', nivel: 'good', filtro: { olt_rx_sig__gt: '-27' } },
]

const TIPOS: Record<TipoVariacao, { label: string; variant: 'destructive' | 'warning' | 'success' }> = {
  piorou: { label: 'Piorou', variant: 'destructive' },
  oscilando: { label: 'Oscilando', variant: 'warning' },
  melhorou: { label: 'Melhorou', variant: 'success' },
}

const ALARMES: Record<string, string> = {
  sinal_baixo: 'sinal baixo',
  sinal_degradado: 'sinal degradado',
  tx_alto: 'Tx alto',
  sinal_alto: 'sinal alto',
  quedas: 'quedas',
  falta_energia: 'falta de energia',
}

function dataHora(iso: string | null | undefined) {
  return iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}

function Abas<T extends string>({
  valor,
  opcoes,
  onChange,
}: {
  valor: T
  opcoes: { id: T; label: string }[]
  onChange: (v: T) => void
}) {
  return (
    <div className="inline-flex rounded-md border border-border p-0.5" role="tablist">
      {opcoes.map((o) => (
        <button
          key={o.id}
          role="tab"
          aria-selected={o.id === valor}
          onClick={() => onChange(o.id)}
          className={cn(
            'rounded px-3 py-1 text-sm transition-colors',
            o.id === valor ? 'bg-primary/10 font-medium text-primary' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function SinalPage() {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') === 'variacao' ? 'variacao' : 'faixas'
  const faixa = (FAIXAS.find((f) => f.id === params.get('faixa'))?.id ?? 'critico') as Faixa
  const oltId = params.get('olt') ?? ''

  function atualizar(mudancas: Record<string, string>) {
    const novo = new URLSearchParams(params)
    for (const [k, v] of Object.entries(mudancas)) {
      if (v) novo.set(k, v)
      else novo.delete(k)
    }
    setParams(novo, { replace: true })
  }

  const { data: olts } = useOlts()
  const { data: resumo } = useQuery({
    queryKey: ['sinal-resumo', oltId],
    queryFn: async () =>
      (await api.get<SinalResumo>('/sinal/resumo/', { params: oltId ? { olt: oltId } : {} })).data,
  })

  const faixaAtual = FAIXAS.find((f) => f.id === faixa)!

  return (
    <div>
      <PageHeader
        title="Sinal óptico"
        description={`Sinal recebido na OLT por ONU. Última coleta: ${dataHora(resumo?.ultima_coleta)}.`}
        action={
          (olts?.length ?? 0) > 1 && (
            <SelectFilter
              label="OLT"
              value={oltId}
              onChange={(v) => atualizar({ olt: v })}
              options={(olts ?? []).map((o) => ({ label: o.name, value: String(o.id) }))}
            />
          )
        }
      />

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {FAIXAS.map((f) => {
          const ativa = aba === 'faixas' && faixa === f.id
          return (
            <button key={f.id} className="text-left" onClick={() => atualizar({ aba: '', faixa: f.id })}>
              <Card className={cn('gap-1 py-4 transition-colors hover:bg-accent/50', ativa && 'border-primary')}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-1.5">
                    <span className="inline-block size-2 rounded-full" style={{ background: statusStyles[f.nivel].dot }} />
                    {f.label} <span className="text-xs font-normal">({f.detalhe})</span>
                  </CardTitle>
                  <CardValue>{resumo ? resumo[f.id] : '—'}</CardValue>
                </CardHeader>
              </Card>
            </button>
          )
        })}
        <Card className="gap-1 py-4">
          <CardHeader>
            <CardTitle>Sem leitura</CardTitle>
            <CardValue>{resumo?.sem_leitura ?? '—'}</CardValue>
          </CardHeader>
        </Card>
      </div>

      <div className="mb-4">
        <Abas
          valor={aba}
          opcoes={[
            { id: 'faixas', label: `Lista: ${faixaAtual.label.toLowerCase()}` },
            { id: 'variacao', label: 'Variação (logs)' },
          ]}
          onChange={(v) => atualizar({ aba: v === 'variacao' ? 'variacao' : '' })}
        />
      </div>

      {aba === 'faixas' ? (
        <OnuListPage
          key={`${faixa}-${oltId}`}
          hideHeader
          title=""
          description=""
          endpoint="/onus/"
          filters={{ ...faixaAtual.filtro, ...(oltId ? { olt: oltId } : {}) }}
          showQuickFilters
          emptyMessage={`Nenhuma ONU na faixa ${faixaAtual.label.toLowerCase()}.`}
        />
      ) : (
        <Variacao oltId={oltId} />
      )}
    </div>
  )
}

function Variacao({ oltId }: { oltId: string }) {
  const [periodo, setPeriodo] = useState<'24h' | '7d'>('24h')
  const [limiar, setLimiar] = useState('2')
  const [tipo, setTipo] = useState('')
  const [cto, setCto] = useState<string | null>(null)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['sinal-variacao', oltId, periodo, limiar],
    queryFn: async () =>
      (
        await api.get<SinalVariacao>('/sinal/variacao/', {
          params: { periodo, limiar, ...(oltId ? { olt: oltId } : {}) },
        })
      ).data,
  })

  const itens = useMemo(() => {
    let lista: VariacaoItem[] = data?.itens ?? []
    if (tipo) lista = lista.filter((i) => i.tipo === tipo)
    if (cto) {
      const grupo = data?.grupos.find((g) => `${g.nivel}:${g.referencia}` === cto)
      if (grupo) lista = lista.filter((i) => grupo.serials.includes(i.serial))
    }
    return lista
  }, [data, tipo, cto])

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <Abas
          valor={periodo}
          opcoes={[
            { id: '24h', label: 'Último dia' },
            { id: '7d', label: 'Última semana' },
          ]}
          onChange={(v) => {
            setPeriodo(v)
            setCto(null)
          }}
        />
        <label className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Variação mínima</span>
          <select
            value={limiar}
            onChange={(e) => setLimiar(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          >
            {['1', '2', '3', '5'].map((v) => (
              <option key={v} value={v}>
                {v} dB
              </option>
            ))}
          </select>
        </label>
        <SelectFilter
          label="Tipo"
          value={tipo}
          onChange={setTipo}
          options={(Object.keys(TIPOS) as TipoVariacao[]).map((t) => ({
            label: `${TIPOS[t].label} (${data?.contagem[t] ?? 0})`,
            value: t,
          }))}
        />
        {isFetching && <span className="text-xs text-muted-foreground">atualizando…</span>}
      </div>

      {data && (
        <p className="text-xs text-muted-foreground">
          Compara o sinal atual com a mediana do período anterior de mesmo tamanho ({data.onts_com_leitura} ONTs,{' '}
          {data.leituras_no_periodo} leituras desde {dataHora(data.inicio)}). Alarmes de sinal e quedas vêm do syslog
          da OLT.
        </p>
      )}

      <div>
        <h2 className="mb-2 text-sm font-semibold text-foreground">Possíveis problemas em comum</h2>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Carregando…</p>
        ) : data && data.grupos.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhum grupo de clientes variando junto na mesma caixa ou PON. As variações abaixo parecem individuais.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {data?.grupos.map((g) => {
              const chave = `${g.nivel}:${g.referencia}`
              const ativo = cto === chave
              const Icone = g.nivel === 'pon' ? Waypoints : MapPin
              return (
                <Card key={chave} className={cn('gap-2 py-4', ativo && 'border-primary')}>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5 text-foreground">
                        <Icone className="size-4" />
                        {g.nivel === 'pon' ? g.referencia : `Caixa ${g.referencia}`}
                        {g.nivel === 'cto' && g.ramal && (
                          <span className="font-normal text-muted-foreground">· {g.ramal}</span>
                        )}
                      </span>
                      <Badge variant={g.nivel === 'pon' ? 'destructive' : 'warning'}>
                        {g.afetados}/{g.total} · {g.delta_medio > 0 ? '+' : ''}
                        {g.delta_medio} dB
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2 text-sm">
                    <p className="flex gap-1.5">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />
                      {g.diagnostico}
                    </p>
                    <div className="flex gap-3 text-xs">
                      <button className="text-primary hover:underline" onClick={() => setCto(ativo ? null : chave)}>
                        {ativo ? 'Mostrar todos' : 'Ver clientes'}
                      </button>
                      {g.cto_id && (
                        <Link className="text-primary hover:underline" to={`/ctos?cto=${g.cto_id}`}>
                          Abrir CTO
                        </Link>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-foreground">
          Clientes com variação {cto && <span className="font-normal text-muted-foreground">(filtrado pelo grupo)</span>}
        </h2>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2">PON / pos.</th>
                <th className="px-3 py-2">CTO provável</th>
                <th className="px-3 py-2">Variação</th>
                <th className="px-3 py-2 text-right">Antes → agora (dBm)</th>
                <th className="px-3 py-2 text-right">Mín / máx</th>
                <th className="px-3 py-2">Alarmes</th>
                <th className="px-3 py-2">Diagnóstico</th>
              </tr>
            </thead>
            <tbody>
              {itens.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-center text-muted-foreground">
                    {isLoading ? 'Carregando…' : 'Nenhuma ONU variou além do limite no período.'}
                  </td>
                </tr>
              )}
              {itens.map((i) => (
                <tr key={`${i.olt_id}-${i.serial}`} className="border-t border-border align-top">
                  <td className="px-3 py-2">
                    <div className="font-medium text-foreground">{i.cliente_nome || '—'}</div>
                    <div className="font-data text-xs text-muted-foreground">
                      {i.serial}
                      {i.login && ` · ${i.login}`}
                    </div>
                  </td>
                  <td className="px-3 py-2 font-data">
                    {i.pon}/{i.position}
                    {i.olt_nome && <div className="text-xs text-muted-foreground">{i.olt_nome}</div>}
                  </td>
                  <td className="px-3 py-2">
                    {i.cto ? (
                      <Link className="text-primary hover:underline" to={`/ctos?cto=${i.cto.id}`}>
                        {i.cto.descricao}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={TIPOS[i.tipo].variant}>{TIPOS[i.tipo].label}</Badge>
                  </td>
                  <td className="px-3 py-2 text-right font-data whitespace-nowrap">
                    {i.referencia} → <strong>{i.atual}</strong>
                    <div className={cn('text-xs', i.delta < 0 ? 'text-destructive' : 'text-emerald-600')}>
                      {i.delta > 0 ? '+' : ''}
                      {i.delta} dB
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right font-data whitespace-nowrap">
                    {i.minimo} / {i.maximo}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {Object.entries(i.alarmes).length === 0
                      ? '—'
                      : Object.entries(i.alarmes)
                          .map(([k, n]) => `${n}× ${ALARMES[k] ?? k}`)
                          .join(', ')}
                  </td>
                  <td className="max-w-xs px-3 py-2 text-xs text-muted-foreground">{i.diagnostico}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
