import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Loader2, RefreshCw, ScanLine } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { OnuHealthSummary, OnuStats } from '@/types/api'
import { OnuListPage } from './OnuListPage'

interface Situacao {
  id: string
  label: string
  description: string
  endpoint: string
  filters?: Record<string, string>
  quick?: boolean
  emptyMessage?: string
}

const SITUACOES: Situacao[] = [
  {
    id: '',
    label: 'Todas',
    description: 'Lista completa de ONUs cadastradas.',
    endpoint: '/onus/',
    quick: true,
  },
  {
    id: 'offline',
    label: 'Oper. state down',
    description: 'ONUs fora do ar no momento (estado operacional down).',
    endpoint: '/onus/',
    filters: { oper_state: 'down' },
    quick: true,
    emptyMessage: 'Nenhuma ONU offline no momento.',
  },
  {
    id: 'sem-cliente',
    label: 'Sem cliente fibra',
    description: 'ONUs sem cliente fibra vinculado no IXC.',
    endpoint: '/onus/',
    filters: { cliente_fibra: 'false' },
    quick: true,
    emptyMessage: 'Todas as ONUs têm cliente fibra vinculado.',
  },
  {
    id: 'sem-mac',
    label: 'Sem MAC',
    description: 'ONUs sem MAC registrado.',
    endpoint: '/onus/sem-mac/',
    emptyMessage: 'Nenhuma ONU sem MAC.',
  },
  {
    id: 'duplicadas',
    label: 'Duplicadas',
    description: 'ONUs com número serial duplicado: normalmente reconexão ou erro de provisionamento.',
    endpoint: '/onus/duplicated/',
    emptyMessage: 'Nenhuma ONU duplicada encontrada.',
  },
]

const TAREFAS = [
  {
    endpoint: '/tasks/update-onus/',
    label: 'Atualizar ONUs',
    icon: RefreshCw,
    title: 'Relê status e sinal de todas as ONUs na OLT',
  },
  { endpoint: '/tasks/update-mac/', label: 'Atualizar MAC', icon: ScanLine, title: 'Relê a tabela de MACs da OLT' },
  {
    endpoint: '/tasks/sync-clientes/',
    label: 'Atualizar clientes (IXC)',
    icon: Database,
    title: 'Sincroniza os clientes fibra do IXC e remarca as ONUs',
  },
]

/** Página única de ONUs: a "situação" (aba) troca o endpoint/filtro e fica na URL (?situacao=). */
export function OnusPage() {
  const [params, setParams] = useSearchParams()
  const situacao = SITUACOES.find((s) => s.id === (params.get('situacao') ?? '')) ?? SITUACOES[0]

  const { data: stats } = useQuery({
    queryKey: ['onu-stats'],
    queryFn: async () => (await api.get<OnuStats>('/onus/stats/')).data,
  })
  const { data: health } = useQuery({
    queryKey: ['onu-health-summary'],
    queryFn: async () => (await api.get<OnuHealthSummary>('/onus/health-summary/')).data,
  })
  const toast = useToast()
  const queryClient = useQueryClient()
  const disparar = useMutation({
    mutationFn: async (t: (typeof TAREFAS)[number]) => (await api.post(t.endpoint)).data,
    onSuccess: (_, t) => {
      toast.success(`${t.label} iniciada`, 'Roda em segundo plano para todas as OLTs; acompanhe em Tarefas.')
      queryClient.invalidateQueries({ queryKey: ['/tasks/'] })
    },
    onError: () => toast.error('Não foi possível iniciar a tarefa'),
  })

  const contagem: Record<string, number | undefined> = {
    '': stats?.total_onus,
    offline: stats?.onus_offline,
    'sem-cliente': health?.onus_sem_cliente_fibra,
    'sem-mac': health?.onus_sem_mac,
  }

  return (
    <OnuListPage
      key={situacao.id}
      title="ONUs"
      description={situacao.description}
      endpoint={situacao.endpoint}
      filters={situacao.filters}
      showQuickFilters={situacao.quick}
      emptyMessage={situacao.emptyMessage}
      headerAction={
        <div className="flex flex-wrap items-center gap-2">
          {TAREFAS.map((t) => (
            <Button
              key={t.endpoint}
              size="sm"
              variant="outline"
              title={t.title}
              disabled={disparar.isPending}
              onClick={() => disparar.mutate(t)}
            >
              {disparar.isPending && disparar.variables?.endpoint === t.endpoint ? (
                <Loader2 className="animate-spin" />
              ) : (
                <t.icon />
              )}
              {t.label}
            </Button>
          ))}
          <Link to="/tasks" className="text-xs text-primary hover:underline">
            Ver tarefas
          </Link>
        </div>
      }
    >
      <div className="mb-4 flex flex-wrap gap-1.5" role="tablist" aria-label="Situação">
        {SITUACOES.map((s) => {
          const ativa = s.id === situacao.id
          const n = contagem[s.id]
          return (
            <button
              key={s.id || 'todas'}
              role="tab"
              aria-selected={ativa}
              onClick={() => setParams(s.id ? { situacao: s.id } : {})}
              className={cn(
                'flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors',
                ativa
                  ? 'border-primary bg-primary/10 font-medium text-primary'
                  : 'border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              {s.label}
              {n !== undefined && <span className="font-data text-xs opacity-80">{n}</span>}
            </button>
          )
        })}
      </div>
    </OnuListPage>
  )
}
