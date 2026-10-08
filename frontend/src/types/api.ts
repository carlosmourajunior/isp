export interface Onu {
  id: number
  olt: number | null
  olt_name: string | null
  pon: string
  slot: number | null
  port: number | null
  position: number
  mac: string
  serial: string
  oper_state: string
  admin_state: string
  olt_rx_sig: number | null
  ont_rx_sig: number | null
  ont_tx_sig: number | null
  ont_olt: string
  desc1: string
  desc2: string
  cliente_fibra: boolean
}

export type OltVendor = 'nokia_alcatel'

export interface Olt {
  id: number
  name: string
  vendor: OltVendor
  device_type: string
  host: string
  username: string
  ssh_port: number
  slot_count: number
  global_delay_factor: number
  verbose: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OltFormValues {
  name: string
  vendor: OltVendor
  device_type: string
  host: string
  username: string
  password: string
  ssh_port: number
  slot_count: number
  is_active: boolean
}

export const OLT_VENDOR_LABELS: Record<OltVendor, string> = {
  nokia_alcatel: 'Nokia / Alcatel (AOS)',
}

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
  olt: number | null
  olt_name: string | null
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

export interface OltSystemSummaryItem {
  id: number
  name: string
  system_info: OltSystemInfo | null
  slots_total: number
  slots_operational: number
  temperature_avg: number | null
  temperature_max: number | null
  temperature_critical: number
  temperature_warning: number
}

export interface OltSystemSummaryResponse {
  olts: OltSystemSummaryItem[]
}

export interface OltUser {
  id: number
  olt: number | null
  olt_name: string | null
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
