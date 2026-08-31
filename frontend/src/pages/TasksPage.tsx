import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Loader2, Play, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface Job {
  id: string
  func_name: string
  status: string
  created_at: string
  user: string
  menu_item: string
  started_at?: string
  current_step?: string
  error_message?: string
}

interface TaskListResponse {
  running_jobs: Job[]
  queued_jobs: Job[]
  finished_jobs: Job[]
  failed_jobs: Job[]
}

const triggers = [
  { endpoint: '/tasks/update-all/', label: 'Atualizar Tudo' },
  { endpoint: '/tasks/update-ports/', label: 'Ocupação OLT' },
  { endpoint: '/tasks/update-onus/', label: 'ONUs' },
  { endpoint: '/tasks/update-mac/', label: 'MAC Address' },
  { endpoint: '/tasks/sync-clientes/', label: 'Clientes Fibra' },
]

function JobList({ jobs, emptyMessage, showError }: { jobs: Job[]; emptyMessage: string; showError?: boolean }) {
  if (jobs.length === 0) {
    return <p className="px-5 py-6 text-center text-sm text-muted-foreground">{emptyMessage}</p>
  }

  return (
    <div className="flex flex-col divide-y divide-border">
      {jobs.map((job) => (
        <div key={job.id} className="flex flex-col gap-1 px-5 py-3">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-foreground">{job.menu_item || job.func_name}</span>
            <Badge variant={job.status === 'failed' ? 'destructive' : 'outline'}>{job.status}</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {job.user} · {job.started_at || job.created_at}
            {job.current_step ? ` · ${job.current_step}` : ''}
          </p>
          {showError && job.error_message && (
            <p className="mt-1 flex items-start gap-1.5 text-xs text-destructive">
              <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
              <span className="line-clamp-3">{job.error_message}</span>
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

export function TasksPage() {
  const queryClient = useQueryClient()
  const toast = useToast()

  const { data, isLoading } = useQuery({
    queryKey: ['/tasks/'],
    queryFn: async () => (await api.get<TaskListResponse>('/tasks/')).data,
    refetchInterval: 5000,
  })

  const trigger = useMutation({
    mutationFn: (endpoint: string) => api.post(endpoint),
    onSuccess: (_, endpoint) => {
      const label = triggers.find((t) => t.endpoint === endpoint)?.label ?? 'Tarefa'
      toast.success(`${label} iniciada`, 'Acompanhe o progresso abaixo.')
      queryClient.invalidateQueries({ queryKey: ['/tasks/'] })
    },
    onError: () => toast.error('Erro ao iniciar tarefa'),
  })

  return (
    <div>
      <PageHeader
        title="Tarefas"
        description="Status das tarefas em background (atualiza a cada 5s)."
        action={
          <div className="flex flex-wrap gap-2">
            {triggers.map((t) => (
              <Button
                key={t.endpoint}
                variant="outline"
                size="sm"
                disabled={trigger.isPending}
                onClick={() => trigger.mutate(t.endpoint)}
              >
                <Play className="size-3.5" />
                {t.label}
              </Button>
            ))}
          </div>
        }
      />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card className="gap-0 overflow-hidden py-0">
            <CardHeader className="flex-row items-center gap-2 space-y-0 border-b border-border py-3.5">
              <RefreshCw className="size-4 text-primary" />
              <CardTitle className="text-foreground">Em execução ({data?.running_jobs.length ?? 0})</CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <JobList jobs={data?.running_jobs ?? []} emptyMessage="Nenhuma tarefa em execução." />
            </CardContent>
          </Card>

          <Card className="gap-0 overflow-hidden py-0">
            <CardHeader className="flex-row items-center gap-2 space-y-0 border-b border-border py-3.5">
              <Loader2 className="size-4 text-muted-foreground" />
              <CardTitle className="text-foreground">Na fila ({data?.queued_jobs.length ?? 0})</CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <JobList jobs={data?.queued_jobs ?? []} emptyMessage="Nenhuma tarefa na fila." />
            </CardContent>
          </Card>

          <Card className="gap-0 overflow-hidden py-0">
            <CardHeader className="flex-row items-center gap-2 space-y-0 border-b border-border py-3.5">
              <AlertCircle className="size-4 text-destructive" />
              <CardTitle className="text-foreground">Falharam ({data?.failed_jobs.length ?? 0})</CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <JobList jobs={data?.failed_jobs ?? []} emptyMessage="Nenhuma falha recente." showError />
            </CardContent>
          </Card>

          <Card className="gap-0 overflow-hidden py-0">
            <CardHeader className="flex-row items-center gap-2 space-y-0 border-b border-border py-3.5">
              <CardTitle className="text-foreground">Concluídas ({data?.finished_jobs.length ?? 0})</CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <JobList jobs={data?.finished_jobs ?? []} emptyMessage="Nenhuma tarefa concluída recentemente." />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
