import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface OnuStats {
  total_onus: number
  onus_online: number
  onus_offline: number
  clientes_fibra: number
  onus_sinal_baixo: number
  percentual_online: number
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
    </div>
  )
}

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['onu-stats'],
    queryFn: async () => {
      const response = await api.get<OnuStats>('/onus/stats/')
      return response.data
    },
  })

  if (isLoading) {
    return <p className="text-muted-foreground">Carregando estatísticas…</p>
  }

  if (isError || !data) {
    return <p className="text-destructive">Não foi possível carregar as estatísticas.</p>
  }

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-foreground">Dashboard</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Total de ONUs" value={data.total_onus} />
        <StatCard label="Online" value={data.onus_online} />
        <StatCard label="Offline" value={data.onus_offline} />
        <StatCard label="Clientes Fibra" value={data.clientes_fibra} />
        <StatCard label="Sinal Baixo" value={data.onus_sinal_baixo} />
      </div>
      <p className="mt-4 text-sm text-muted-foreground">
        {data.percentual_online}% das ONUs estão online.
      </p>
    </div>
  )
}
