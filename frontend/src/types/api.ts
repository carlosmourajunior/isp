export interface OnuStats {
  total_onus: number
  onus_online: number
  onus_offline: number
  clientes_fibra: number
  onus_sinal_baixo: number
  percentual_online: number
}

export interface OnuHealthSummary {
  onus_sem_mac: number
  onus_sem_cliente_fibra: number
  sinal_abaixo_29: number
  sinal_entre_27_e_29: number
}

export interface OltSystemInfo {
  id: number
  isam_release: string
  uptime_days: number
  uptime_hours: number
  uptime_minutes: number
  uptime_seconds: number
  uptime_raw: string
  total_uptime_hours: number
  last_updated: string
}

export interface OltSystemStats {
  system_info: OltSystemInfo | null
  slots_stats: {
    total_slots: number
    operational_slots: number
    offline_slots: number
    operational_percentage: number
  }
  temperature_stats: {
    critical_temperatures: number
    warning_temperatures: number
    normal_temperatures: number
    average_temperature: number
    max_temperature: number
    min_temperature: number
  }
  last_updated: string | null
}

export interface OltUser {
  id: number
  slot: number
  port: number
  users_connected: number
  last_updated: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
