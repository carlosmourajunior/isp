import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardValue } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useOlts } from '@/hooks/useOlts'
import type { Causa, ItemOffline, ItemRecorrente, OfflineAtivos, Recorrentes } from '@/types/desconexoes'

type Aba = 'recorrentes' | 'offline'

const CAUSAS: Record<Causa, { label: string; variant: 'warning' | 'destructive' | 'secondary' | 'outline' }> = {
  energia: { label: 'Energia / equipamento', variant: 'warning' },
  fibra: { label: 'Fibra / sinal', variant: 'destructive' },
  misto: { label: 'Misto', variant: 'secondary' },
  sem_evento: { label: 'Sem evento nos logs', variant: 'outline' },
}

const SITUACAO_VARIANT: Record<string, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  ativo: 'success',
  bloqueado: 'warning',
  inativo: 'destructive',
  sem_contrato: 'secondary',
  sem_cliente: 'secondary',
}

function dataHora(iso: string | null | undefined) {
  return iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}

function Abas({ valor, onChange }: { valor: Aba; onChange: (v: Aba) => void }) {
  const opcoes: { id: Aba; label: string }[] = [
    { id: 'recorrentes', label: 'Caem todo dia' },
    { id: 'offline', label: 'Ativos no IXC, offline' },
  ]
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

function NumeroSelect({
  label,
  value,
  onChange,
  opcoes,
  sufixo,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  opcoes: number[]
  sufixo: string
}) {
  return (
    <label className="flex items-center gap-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {opcoes.map((v) => (
          <option key={v} value={v}>
            {v} {sufixo}
          </option>
        ))}
      </select>
    </label>
  )
}

function baixarCsv(nome: string, cabecalho: string[], linhas: (string | number | null)[][]) {
  const celula = (v: string | number | null) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const texto = [cabecalho, ...linhas].map((l) => l.map(celula).join(';')).join('\r\n')
  // BOM para o Excel abrir os acentos corretamente.
  const blob = new Blob(['﻿' + texto], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nome
  a.click()
  URL.revokeObjectURL(url)
}

function textoBusca(i: { cliente_nome: string; login: string; serial: string; endereco: string }) {
  return `${i.cliente_nome} ${i.login} ${i.serial} ${i.endereco}`.toLowerCase()
}

function Resumo({ itens }: { itens: { rotulo: string; valor: number | string }[] }) {
  return (
    <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {itens.map((i) => (
        <Card key={i.rotulo} className="gap-1 py-4">
          <CardHeader>
            <CardTitle>{i.rotulo}</CardTitle>
            <CardValue>{i.valor}</CardValue>
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}

function ClienteCelula({ i }: { i: ItemRecorrente | ItemOffline }) {
  return (
    <td className="px-3 py-2">
      <div className="font-medium text-foreground">{i.cliente_nome || '—'}</div>
      <div className="font-data text-xs text-muted-foreground">
        {i.serial}
        {i.login && ` · ${i.login}`}
      </div>
    </td>
  )
}

function IxcCelula({ i }: { i: ItemRecorrente | ItemOffline }) {
  return (
    <td className="px-3 py-2">
      <Badge variant={SITUACAO_VARIANT[i.situacao] ?? 'secondary'}>{i.situacao_rotulo}</Badge>
      {i.status_internet && <div className="mt-0.5 text-xs text-muted-foreground">Internet: {i.status_internet}</div>}
    </td>
  )
}

function PonCelula({ i }: { i: ItemRecorrente | ItemOffline }) {
  return (
    <td className="px-3 py-2 font-data">
      {i.pon ? `${i.pon}/${i.position}` : '—'}
      {i.olt_nome && <div className="text-xs text-muted-foreground">{i.olt_nome}</div>}
    </td>
  )
}

export function DesconexoesPage() {
  const [params, setParams] = useSearchParams()
  const aba: Aba = params.get('aba') === 'offline' ? 'offline' : 'recorrentes'
  const oltId = params.get('olt') ?? ''
  const { data: olts } = useOlts()

  function atualizar(mudancas: Record<string, string>) {
    const novo = new URLSearchParams(params)
    for (const [k, v] of Object.entries(mudancas)) {
      if (v) novo.set(k, v)
      else novo.delete(k)
    }
    setParams(novo, { replace: true })
  }

  return (
    <div>
      <PageHeader
        title="Desconexões"
        description="Cruza o cadastro do IXC com o log da OLT (syslog e coletas de ONUs) para achar clientes que caem sempre e clientes ativos sem conexão."
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
      <div className="mb-4">
        <Abas valor={aba} onChange={(v) => atualizar({ aba: v === 'recorrentes' ? '' : v })} />
      </div>
      {aba === 'recorrentes' ? <AbaRecorrentes oltId={oltId} /> : <AbaOffline oltId={oltId} />}
    </div>
  )
}

function AbaRecorrentes({ oltId }: { oltId: string }) {
  const [janela, setJanela] = useState('14')
  const [minDias, setMinDias] = useState('10')
  const [perfil, setPerfil] = useState('')
  const [busca, setBusca] = useState('')

  const minDiasValido = String(Math.min(Number(minDias), Number(janela)))
  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: ['desconexoes-recorrentes', oltId, janela, minDiasValido],
    queryFn: async () =>
      (
        await api.get<Recorrentes>('/desconexoes/recorrentes/', {
          params: { janela, min_dias: minDiasValido, ...(oltId ? { olt: oltId } : {}) },
        })
      ).data,
  })

  const itens = useMemo(() => {
    const q = busca.trim().toLowerCase()
    return (data?.itens ?? []).filter((i) => {
      if (perfil === 'noturno' ? !i.noturno : perfil && i.causa !== perfil) return false
      return !q || textoBusca(i).includes(q)
    })
  }, [data, perfil, busca])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <NumeroSelect label="Janela" value={janela} onChange={setJanela} opcoes={[7, 14, 21, 30]} sufixo="dias" />
        <NumeroSelect
          label="Caiu em pelo menos"
          value={minDiasValido}
          onChange={setMinDias}
          opcoes={[3, 5, 7, 10, 12, 14].filter((n) => n <= Number(janela))}
          sufixo="dias"
        />
        <SelectFilter
          label="Perfil"
          value={perfil}
          onChange={setPerfil}
          options={[
            { label: `Energia / equipamento (${data?.contagem.energia ?? 0})`, value: 'energia' },
            { label: `Fibra / sinal (${data?.contagem.fibra ?? 0})`, value: 'fibra' },
            { label: `Misto (${data?.contagem.misto ?? 0})`, value: 'misto' },
            { label: `Desliga à noite (${data?.contagem.noturno ?? 0})`, value: 'noturno' },
          ]}
        />
        <Input
          className="w-56"
          placeholder="Buscar cliente, login ou serial"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
        <Button
          variant="outline"
          size="sm"
          disabled={itens.length === 0}
          onClick={() =>
            baixarCsv(
              'desconexoes-recorrentes.csv',
              ['Cliente', 'Login', 'Serial', 'OLT', 'PON', 'IXC', 'Dias com queda', 'Quedas', 'Perfil', 'Desliga à noite', 'Hora típica', 'Duração mediana (min)', 'Última queda'],
              itens.map((i) => [
                i.cliente_nome, i.login, i.serial, i.olt_nome, i.pon ? `${i.pon}/${i.position}` : '',
                i.situacao_rotulo, i.dias_com_queda, i.quedas, i.causa_rotulo, i.noturno ? 'sim' : 'não',
                i.hora_tipica, i.duracao_mediana_min, dataHora(i.ultima_queda),
              ]),
            )
          }
        >
          <Download className="size-4" /> CSV
        </Button>
        {isFetching && <span className="text-xs text-muted-foreground">atualizando…</span>}
      </div>

      <Resumo
        itens={[
          { rotulo: 'Clientes com padrão diário', valor: data?.total ?? '—' },
          { rotulo: 'Energia / equipamento', valor: data?.contagem.energia ?? 0 },
          { rotulo: 'Fibra / sinal', valor: data?.contagem.fibra ?? 0 },
          { rotulo: 'Desligam à noite', valor: data?.contagem.noturno ?? 0 },
        ]}
      />

      {data && (
        <p className="text-xs text-muted-foreground">
          Conta os dias distintos (horário de Brasília) com ao menos uma queda de ONT nos últimos {data.janela} dias.
          Energia = dying gasp; fibra = ONT inativa ou perda de sinal. Histórico disponível: {data.historico_dias} dias
          {data.historico_curto && ' (menor que a janela escolhida: o resultado pode estar subestimado)'}.
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Cliente</th>
              <th className="px-3 py-2">PON / pos.</th>
              <th className="px-3 py-2">IXC</th>
              <th className="px-3 py-2 text-right">Dias com queda</th>
              <th className="px-3 py-2 text-right">Quedas</th>
              <th className="px-3 py-2">Perfil</th>
              <th className="px-3 py-2">Horário típico</th>
              <th className="px-3 py-2 text-right">Duração mediana</th>
              <th className="px-3 py-2">Última queda</th>
            </tr>
          </thead>
          <tbody>
            {itens.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-6 text-center text-muted-foreground">
                  {isLoading ? 'Carregando…' : isError ? 'Erro ao carregar a análise.' : 'Nenhum cliente com esse padrão.'}
                </td>
              </tr>
            )}
            {itens.map((i) => (
              <tr key={`${i.olt_id}-${i.serial}`} className="border-t border-border align-top">
                <ClienteCelula i={i} />
                <PonCelula i={i} />
                <IxcCelula i={i} />
                <td className="px-3 py-2 text-right font-data">
                  <strong>{i.dias_com_queda}</strong>/{data?.janela}
                </td>
                <td className="px-3 py-2 text-right font-data">
                  {i.quedas}
                  <div className="text-xs text-muted-foreground">{i.quedas_por_dia}/dia</div>
                </td>
                <td className="px-3 py-2">
                  <Badge variant={CAUSAS[i.causa].variant}>{CAUSAS[i.causa].label}</Badge>
                  {i.noturno && <div className="mt-0.5 text-xs text-muted-foreground">desliga à noite</div>}
                </td>
                <td className="px-3 py-2 font-data">{i.hora_tipica == null ? '—' : `${String(i.hora_tipica).padStart(2, '0')}h`}</td>
                <td className="px-3 py-2 text-right font-data">
                  {i.duracao_mediana_min == null ? '—' : i.duracao_mediana_min >= 60 ? `${(i.duracao_mediana_min / 60).toFixed(1)} h` : `${i.duracao_mediana_min} min`}
                </td>
                <td className="px-3 py-2 text-xs whitespace-nowrap">{dataHora(i.ultima_queda)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function AbaOffline({ oltId }: { oltId: string }) {
  const [dias, setDias] = useState('5')
  const [semContrato, setSemContrato] = useState(false)
  const [causa, setCausa] = useState('')
  const [busca, setBusca] = useState('')

  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: ['desconexoes-offline', oltId, dias, semContrato],
    queryFn: async () =>
      (
        await api.get<OfflineAtivos>('/desconexoes/offline-ativos/', {
          params: {
            dias_offline: dias,
            ...(semContrato ? { incluir_sem_contrato: '1' } : {}),
            ...(oltId ? { olt: oltId } : {}),
          },
        })
      ).data,
  })

  const itens = useMemo(() => {
    const q = busca.trim().toLowerCase()
    return (data?.itens ?? []).filter((i) => (!causa || i.causa === causa) && (!q || textoBusca(i).includes(q)))
  }, [data, causa, busca])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <NumeroSelect label="Offline há mais de" value={dias} onChange={setDias} opcoes={[1, 3, 5, 7, 10, 15, 30]} sufixo="dias" />
        <SelectFilter
          label="Causa provável"
          value={causa}
          onChange={setCausa}
          options={[
            { label: `Energia / equipamento (${data?.contagem.energia ?? 0})`, value: 'energia' },
            { label: `Fibra / sinal (${data?.contagem.fibra ?? 0})`, value: 'fibra' },
            { label: `Sem evento nos logs (${data?.contagem.sem_evento ?? 0})`, value: 'sem_evento' },
          ]}
        />
        <label className="flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={semContrato} onChange={(e) => setSemContrato(e.target.checked)} />
          <span className="text-muted-foreground">Incluir sem contrato vinculado</span>
        </label>
        <Input
          className="w-56"
          placeholder="Buscar cliente, login ou serial"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
        <Button
          variant="outline"
          size="sm"
          disabled={itens.length === 0}
          onClick={() =>
            baixarCsv(
              'desconexoes-offline-ativos.csv',
              ['Cliente', 'Login', 'Serial', 'OLT', 'PON', 'Contrato IXC', 'Internet IXC', 'Dias offline', 'Dias é mínimo', 'Último online', 'Última queda', 'Causa provável', 'Admin OLT', 'Endereço', 'Posições com o mesmo serial'],
              itens.map((i) => [
                i.cliente_nome, i.login, i.serial, i.olt_nome, i.pon ? `${i.pon}/${i.position}` : '',
                i.status_contrato, i.status_internet, i.dias_offline, i.dias_minimo ? 'sim' : 'não',
                dataHora(i.ultimo_online), dataHora(i.ultima_queda), i.causa_rotulo, i.admin_state, i.endereco,
                i.posicoes_duplicadas || '',
              ]),
            )
          }
        >
          <Download className="size-4" /> CSV
        </Button>
        {isFetching && <span className="text-xs text-muted-foreground">atualizando…</span>}
      </div>

      <Resumo
        itens={[
          { rotulo: 'Ativos no IXC e offline', valor: data?.total ?? '—' },
          { rotulo: 'ONUs offline (todas)', valor: data?.onus_offline_total ?? '—' },
          { rotulo: 'Energia / equipamento', valor: data?.contagem.energia ?? 0 },
          { rotulo: 'Fibra / sinal', valor: data?.contagem.fibra ?? 0 },
        ]}
      />

      {data && (
        <p className="text-xs text-muted-foreground">
          Só entram clientes com contrato e internet ativos no IXC cuja ONU está offline agora. Os dias contam desde
          o último momento em que a ONU esteve online: uma coleta com a ONU online ou um evento "ONT voltou" no log
          da OLT (o que for mais recente). "≥" indica que ela não aparece online em nada desde{' '}
          {dataHora(data.historico_desde)} (início do histórico). Serial cadastrado em mais de uma posição da OLT
          aparece uma vez só, e some da lista se alguma das posições estiver online.
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Cliente</th>
              <th className="px-3 py-2">PON / pos.</th>
              <th className="px-3 py-2">IXC</th>
              <th className="px-3 py-2 text-right">Dias offline</th>
              <th className="px-3 py-2">Último online</th>
              <th className="px-3 py-2">Última queda</th>
              <th className="px-3 py-2">Causa provável</th>
              <th className="px-3 py-2">Endereço</th>
            </tr>
          </thead>
          <tbody>
            {itens.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-muted-foreground">
                  {isLoading ? 'Carregando…' : isError ? 'Erro ao carregar a análise.' : 'Nenhum cliente nessa situação.'}
                </td>
              </tr>
            )}
            {itens.map((i) => (
              <tr key={`${i.olt_id}-${i.serial}`} className="border-t border-border align-top">
                <ClienteCelula i={i} />
                <PonCelula i={i} />
                <IxcCelula i={i} />
                <td className="px-3 py-2 text-right font-data whitespace-nowrap">
                  <strong>
                    {i.dias_minimo ? '≥ ' : ''}
                    {Math.floor(i.dias_offline)}
                  </strong>{' '}
                  d
                  {i.admin_state && i.admin_state !== 'up' && (
                    <div className="text-xs text-amber-600">admin: {i.admin_state}</div>
                  )}
                </td>
                <td className="px-3 py-2 text-xs whitespace-nowrap">
                  {dataHora(i.ultimo_online)}
                  {i.ultimo_online_origem === 'log' && <div className="text-muted-foreground">pelo log da OLT</div>}
                </td>
                <td className="px-3 py-2 text-xs whitespace-nowrap">{dataHora(i.ultima_queda)}</td>
                <td className="px-3 py-2">
                  <Badge variant={CAUSAS[i.causa].variant}>{CAUSAS[i.causa].label}</Badge>
                  {i.posicoes_duplicadas > 0 && (
                    <div className="mt-0.5 text-xs text-amber-600">serial em {i.posicoes_duplicadas} posições</div>
                  )}
                </td>
                <td className="max-w-xs px-3 py-2 text-xs text-muted-foreground">{i.endereco || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
