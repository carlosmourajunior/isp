import { useQuery } from '@tanstack/react-query'
import { Clock } from 'lucide-react'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle, CardValue } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface SchedulerJob {
  id: string
  name: string
  next_run: string | null
  trigger: string
}

interface SchedulerStatusResponse {
  scheduler: {
    status: 'running' | 'not_running' | 'stopped'
    jobs: SchedulerJob[]
  }
  queue: {
    pending_jobs: number
    failed_jobs: number
    finished_jobs: number
  }
}

const statusLabel: Record<SchedulerStatusResponse['scheduler']['status'], { text: string; variant: 'success' | 'destructive' | 'outline' }> = {
  running: { text: 'Rodando', variant: 'success' },
  not_running: { text: 'Parado', variant: 'destructive' },
  stopped: { text: 'Desligado', variant: 'outline' },
}

export function SchedulerPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['/scheduler/status/'],
    queryFn: async () => (await api.get<SchedulerStatusResponse>('/scheduler/status/')).data,
  })

  return (
    <div>
      <PageHeader title="Scheduler" description="Status das atualizações automáticas e da fila de tarefas." />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
            <Card className="gap-2">
              <CardHeader>
                <CardTitle>Status do Scheduler</CardTitle>
              </CardHeader>
              <CardContent>
                {data && <Badge variant={statusLabel[data.scheduler.status].variant}>{statusLabel[data.scheduler.status].text}</Badge>}
              </CardContent>
            </Card>
            <Card className="gap-2">
              <CardHeader>
                <CardTitle>Jobs Agendados</CardTitle>
              </CardHeader>
              <CardContent>
                <CardValue>{data?.scheduler.jobs.length ?? 0}</CardValue>
              </CardContent>
            </Card>
            <Card className="gap-2">
              <CardHeader>
                <CardTitle>Fila Pendente</CardTitle>
              </CardHeader>
              <CardContent>
                <CardValue>{data?.queue.pending_jobs ?? 0}</CardValue>
              </CardContent>
            </Card>
            <Card className="gap-2">
              <CardHeader>
                <CardTitle>Falhas na Fila</CardTitle>
              </CardHeader>
              <CardContent>
                <CardValue>{data?.queue.failed_jobs ?? 0}</CardValue>
              </CardContent>
            </Card>
          </div>

          <div>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Clock className="size-4 text-muted-foreground" />
              Jobs agendados
            </h2>
            <Card className="gap-0 overflow-hidden py-0">
              {data && data.scheduler.jobs.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs text-muted-foreground">
                        <th className="px-5 py-3 font-medium">Nome</th>
                        <th className="px-5 py-3 font-medium">Próxima execução</th>
                        <th className="px-5 py-3 font-medium">Trigger</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.scheduler.jobs.map((job) => (
                        <tr key={job.id} className="border-b border-border last:border-0">
                          <td className="px-5 py-2.5 text-foreground">{job.name}</td>
                          <td className="px-5 py-2.5 text-muted-foreground">{job.next_run ?? '—'}</td>
                          <td className="px-5 py-2.5 text-muted-foreground">{job.trigger}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="px-5 py-8 text-center text-sm text-muted-foreground">
                  Nenhum job agendado no momento (atualizações automáticas desabilitadas por segurança).
                </p>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
