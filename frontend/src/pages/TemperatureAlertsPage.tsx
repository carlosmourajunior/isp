import { useQuery } from '@tanstack/react-query'
import { Thermometer } from 'lucide-react'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface TemperatureAlert {
  id: number
  slot_name: string
  sensor_id: number
  actual_temp: number
  status: string
}

interface TemperatureAlertsResponse {
  critical_alerts: TemperatureAlert[]
  warning_alerts: TemperatureAlert[]
  critical_count: number
  warning_count: number
}

function AlertTable({ alerts, tone }: { alerts: TemperatureAlert[]; tone: 'destructive' | 'warning' }) {
  if (alerts.length === 0) {
    return <p className="px-5 py-8 text-center text-sm text-muted-foreground">Nenhum alerta neste nível.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="px-5 py-3 font-medium">Slot</th>
            <th className="px-5 py-3 font-medium">Sensor</th>
            <th className="px-5 py-3 font-medium">Temperatura</th>
            <th className="px-5 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id} className="border-b border-border last:border-0">
              <td className="px-5 py-2.5 text-foreground">{alert.slot_name}</td>
              <td className="px-5 py-2.5 text-muted-foreground">{alert.sensor_id}</td>
              <td className="px-5 py-2.5 text-foreground">{alert.actual_temp}°C</td>
              <td className="px-5 py-2.5">
                <Badge variant={tone}>{alert.status}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function TemperatureAlertsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['/olt/temperature-alerts/'],
    queryFn: async () => (await api.get<TemperatureAlertsResponse>('/olt/temperature-alerts/')).data,
  })

  return (
    <div>
      <PageHeader title="Alertas de Temperatura" description="Sensores da OLT em estado crítico ou de aviso." />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : (
        <div className="flex flex-col gap-6">
          <div>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Thermometer className="size-4 text-destructive" />
              Críticos ({data?.critical_count ?? 0})
            </h2>
            <Card className="gap-0 overflow-hidden py-0">
              <AlertTable alerts={data?.critical_alerts ?? []} tone="destructive" />
            </Card>
          </div>

          <div>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Thermometer className="size-4 text-amber-500" />
              Aviso ({data?.warning_count ?? 0})
            </h2>
            <Card className="gap-0 overflow-hidden py-0">
              <AlertTable alerts={data?.warning_alerts ?? []} tone="warning" />
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
