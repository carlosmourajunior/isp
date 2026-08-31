import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Cpu,
  RefreshCw,
  ScanLine,
  Signal,
  Thermometer,
  UserX,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { OltSystemStats, OltUser, OnuHealthSummary, OnuStats, Paginated } from '@/types/api'
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardValue } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

function StatCard({
  label,
  value,
  icon: Icon,
  to,
  tone = 'default',
}: {
  label: string
  value: React.ReactNode
  icon: React.ComponentType<{ className?: string }>
  to?: string
  tone?: 'default' | 'warning' | 'destructive'
}) {
  const toneClasses = {
    default: 'text-muted-foreground',
    warning: 'text-amber-600 dark:text-amber-400',
    destructive: 'text-destructive',
  }[tone]

  return (
    <Card className="gap-3">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{label}</CardTitle>
        <Icon className={`size-4 ${toneClasses}`} />
      </CardHeader>
      <CardContent>
        <CardValue>{value}</CardValue>
      </CardContent>
      {to && (
        <CardFooter>
          <Link
            to={to}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            Ver detalhes <ArrowRight className="size-3" />
          </Link>
        </CardFooter>
      )}
    </Card>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-3 text-sm font-semibold text-foreground">{children}</h2>
}

export function DashboardPage() {
  const onuStats = useQuery({
    queryKey: ['onu-stats'],
    queryFn: async () => (await api.get<OnuStats>('/onus/stats/')).data,
  })

  const healthSummary = useQuery({
    queryKey: ['onu-health-summary'],
    queryFn: async () => (await api.get<OnuHealthSummary>('/onus/health-summary/')).data,
  })

  const systemStats = useQuery({
    queryKey: ['olt-system-stats'],
    queryFn: async () => (await api.get<OltSystemStats>('/olt/system-stats/')).data,
  })

  const topPorts = useQuery({
    queryKey: ['olt-users-top'],
    queryFn: async () => {
      const response = await api.get<Paginated<OltUser>>('/olt-users/', {
        params: { ordering: '-users_connected' },
      })
      return response.data.results.slice(0, 5)
    },
  })

  const isLoading =
    onuStats.isLoading || healthSummary.isLoading || systemStats.isLoading || topPorts.isLoading

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando painel…</p>
  }

  const stats = onuStats.data
  const health = healthSummary.data
  const system = systemStats.data

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Visão geral da rede em tempo real.</p>
      </div>

      {stats && (
        <div>
          <SectionTitle>ONUs</SectionTitle>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Total" value={stats.total_onus} icon={Activity} to="/onus" />
            <StatCard
              label="Online"
              value={
                <span className="flex items-center gap-2">
                  {stats.onus_online}
                  <Badge variant="success">{stats.percentual_online}%</Badge>
                </span>
              }
              icon={Signal}
              to="/onus"
            />
            <StatCard
              label="Offline"
              value={stats.onus_offline}
              icon={AlertTriangle}
              to="/onus/offline"
              tone={stats.onus_offline > 0 ? 'destructive' : 'default'}
            />
            <StatCard label="Clientes Fibra" value={stats.clientes_fibra} icon={Activity} to="/clientes-fibra" />
            <StatCard
              label="Sinal Baixo"
              value={stats.onus_sinal_baixo}
              icon={Signal}
              tone={stats.onus_sinal_baixo > 0 ? 'warning' : 'default'}
            />
          </div>
        </div>
      )}

      {health && (
        <div>
          <SectionTitle>Pendências</SectionTitle>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard
              label="ONUs sem MAC"
              value={health.onus_sem_mac}
              icon={ScanLine}
              to="/onus/sem-mac"
              tone={health.onus_sem_mac > 0 ? 'warning' : 'default'}
            />
            <StatCard
              label="Sem Cliente Fibra"
              value={health.onus_sem_cliente_fibra}
              icon={UserX}
              to="/onus/sem-cliente"
              tone={health.onus_sem_cliente_fibra > 0 ? 'warning' : 'default'}
            />
            <StatCard
              label="Sinal entre -27 e -29"
              value={health.sinal_entre_27_e_29}
              icon={Signal}
              tone={health.sinal_entre_27_e_29 > 0 ? 'warning' : 'default'}
            />
            <StatCard
              label="Sinal abaixo de -29"
              value={health.sinal_abaixo_29}
              icon={Signal}
              tone={health.sinal_abaixo_29 > 0 ? 'destructive' : 'default'}
            />
          </div>
        </div>
      )}

      {system && (
        <div>
          <SectionTitle>Sistema OLT</SectionTitle>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="gap-2">
              <CardHeader>
                <CardTitle>Sistema</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p className="text-foreground">{system.system_info?.isam_release ?? '—'}</p>
                <p className="text-muted-foreground">
                  {system.system_info ? `${system.system_info.uptime_days} dias de uptime` : 'Sem dados'}
                </p>
              </CardContent>
            </Card>

            <Card className="gap-2">
              <CardHeader>
                <CardTitle>Slots</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p className="text-foreground">{system.slots_stats.total_slots} no total</p>
                <p>
                  <span className="text-emerald-600 dark:text-emerald-400">
                    {system.slots_stats.operational_slots} operacionais
                  </span>
                  {system.slots_stats.offline_slots > 0 && (
                    <span className="text-destructive"> · {system.slots_stats.offline_slots} offline</span>
                  )}
                </p>
              </CardContent>
            </Card>

            <Card className="gap-2">
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <CardTitle>Temperatura</CardTitle>
                <Thermometer className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p className="text-foreground">
                  Média {system.temperature_stats.average_temperature}°C · Máx {system.temperature_stats.max_temperature}°C
                </p>
                <Link to="/temperature-alerts" className="inline-flex items-center gap-1.5 hover:underline">
                  <span className="text-destructive">{system.temperature_stats.critical_temperatures} críticas</span>
                  <span className="text-muted-foreground">/</span>
                  <span className="text-amber-600 dark:text-amber-400">
                    {system.temperature_stats.warning_temperatures} aviso
                  </span>
                </Link>
              </CardContent>
            </Card>

            <Card className="justify-center gap-2">
              <CardContent className="flex items-center justify-center">
                <Button variant="outline" size="sm" className="w-full" disabled>
                  <RefreshCw className="size-3.5" />
                  Atualizar OLT
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {topPorts.data && topPorts.data.length > 0 && (
        <div>
          <SectionTitle>Top 5 Portas por Ocupação</SectionTitle>
          <Card className="py-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Porta</th>
                    <th className="px-5 py-3 font-medium">Usuários</th>
                    <th className="px-5 py-3 font-medium">Atualizado</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {topPorts.data.map((port) => (
                    <tr key={port.id} className="border-b border-border last:border-0">
                      <td className="px-5 py-3 text-foreground">
                        1/1/{port.slot}/{port.port}
                      </td>
                      <td className="px-5 py-3 flex items-center gap-1.5">
                        <Cpu className="size-3.5 text-muted-foreground" />
                        {port.users_connected}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {new Date(port.last_updated).toLocaleString('pt-BR')}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link
                          to={`/onus/porta/${port.slot}/${port.port}`}
                          className="text-xs font-medium text-primary hover:underline"
                        >
                          Detalhes
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
