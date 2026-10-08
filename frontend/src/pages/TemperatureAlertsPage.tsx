import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, ArrowUpDown, Thermometer } from 'lucide-react'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { SelectFilter } from '@/components/SelectFilter'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface TemperatureAlert {
  id: number
  olt: number | null
  olt_name: string | null
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

type SortKey = 'olt_name' | 'slot_name' | 'sensor_id' | 'actual_temp' | 'status'

function SortableTh({
  label,
  sortKey,
  active,
  onSort,
}: {
  label: string
  sortKey: SortKey
  active: { key: SortKey; dir: 'asc' | 'desc' } | null
  onSort: (key: SortKey) => void
}) {
  const isAsc = active?.key === sortKey && active.dir === 'asc'
  const isDesc = active?.key === sortKey && active.dir === 'desc'
  return (
    <th className="px-5 py-3 font-medium">
      <button type="button" onClick={() => onSort(sortKey)} className="inline-flex items-center gap-1 hover:text-foreground">
        {label}
        {isAsc ? (
          <ArrowUp className="size-3" />
        ) : isDesc ? (
          <ArrowDown className="size-3" />
        ) : (
          <ArrowUpDown className="size-3 opacity-40" />
        )}
      </button>
    </th>
  )
}

/** Tabela já carrega tudo de uma vez (sem paginação de backend) - ordenação é só no cliente. */
function AlertTable({
  alerts,
  tone,
  showOlt,
}: {
  alerts: TemperatureAlert[]
  tone: 'destructive' | 'warning'
  showOlt: boolean
}) {
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' } | null>(null)

  const sorted = useMemo(() => {
    if (!sort) return alerts
    const copy = [...alerts]
    copy.sort((a, b) => {
      const va = a[sort.key] ?? ''
      const vb = b[sort.key] ?? ''
      const cmp = typeof va === 'number' && typeof vb === 'number' ? va - vb : String(va).localeCompare(String(vb))
      return sort.dir === 'asc' ? cmp : -cmp
    })
    return copy
  }, [alerts, sort])

  function toggleSort(key: SortKey) {
    setSort((current) =>
      current?.key === key ? { key, dir: current.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' },
    )
  }

  if (alerts.length === 0) {
    return <p className="px-5 py-8 text-center text-sm text-muted-foreground">Nenhum alerta neste nível.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            {showOlt && <SortableTh label="OLT" sortKey="olt_name" active={sort} onSort={toggleSort} />}
            <SortableTh label="Slot" sortKey="slot_name" active={sort} onSort={toggleSort} />
            <SortableTh label="Sensor" sortKey="sensor_id" active={sort} onSort={toggleSort} />
            <SortableTh label="Temperatura" sortKey="actual_temp" active={sort} onSort={toggleSort} />
            <SortableTh label="Status" sortKey="status" active={sort} onSort={toggleSort} />
          </tr>
        </thead>
        <tbody>
          {sorted.map((alert) => (
            <tr key={alert.id} className="border-b border-border last:border-0">
              {showOlt && <td className="px-5 py-2.5 text-muted-foreground">{alert.olt_name || '—'}</td>}
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
  const [olt, setOlt] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['/olt/temperature-alerts/'],
    queryFn: async () => (await api.get<TemperatureAlertsResponse>('/olt/temperature-alerts/')).data,
  })

  const oltOptions = useMemo(() => {
    const byId = new Map<number, string>()
    for (const alert of [...(data?.critical_alerts ?? []), ...(data?.warning_alerts ?? [])]) {
      if (alert.olt && alert.olt_name) byId.set(alert.olt, alert.olt_name)
    }
    return Array.from(byId, ([value, label]) => ({ label, value: String(value) }))
  }, [data])
  const showOltFilter = oltOptions.length > 1

  const criticalAlerts = (data?.critical_alerts ?? []).filter((a) => !olt || String(a.olt) === olt)
  const warningAlerts = (data?.warning_alerts ?? []).filter((a) => !olt || String(a.olt) === olt)

  return (
    <div>
      <PageHeader
        title="Alertas de Temperatura"
        description="Sensores da OLT em estado crítico ou de aviso."
        action={
          showOltFilter && <SelectFilter label="OLT" value={olt} onChange={setOlt} options={oltOptions} />
        }
      />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : (
        <div className="flex flex-col gap-6">
          <div>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Thermometer className="size-4 text-destructive" />
              Críticos ({criticalAlerts.length})
            </h2>
            <Card className="gap-0 overflow-hidden py-0">
              <AlertTable alerts={criticalAlerts} tone="destructive" showOlt={showOltFilter} />
            </Card>
          </div>

          <div>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Thermometer className="size-4 text-amber-500" />
              Aviso ({warningAlerts.length})
            </h2>
            <Card className="gap-0 overflow-hidden py-0">
              <AlertTable alerts={warningAlerts} tone="warning" showOlt={showOltFilter} />
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
