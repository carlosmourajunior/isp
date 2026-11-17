export type Causa = 'energia' | 'fibra' | 'misto' | 'sem_evento'

interface ItemBase {
  olt_id: number | null
  olt_nome: string
  serial: string
  pon: string
  position: number | null
  estado_atual: string | null
  cliente_nome: string
  login: string
  id_contrato: string
  situacao: string
  situacao_rotulo: string
  status_contrato: string
  status_internet: string
  endereco: string
  causa: Causa
  causa_rotulo: string
  ultima_queda: string | null
}

export interface ItemRecorrente extends ItemBase {
  dias_com_queda: number
  quedas: number
  quedas_por_dia: number
  tipos: Record<string, number>
  noturno: boolean
  hora_tipica: number | null
  duracao_mediana_min: number | null
}

export interface ItemOffline extends ItemBase {
  admin_state: string | null
  dias_offline: number
  dias_minimo: boolean
  ultimo_online: string | null
  ultima_queda_tipo: string | null
}

export interface Recorrentes {
  gerado_em: string
  janela: number
  min_dias: number
  historico_dias: number
  historico_curto: boolean
  total: number
  contagem: Record<string, number>
  itens: ItemRecorrente[]
}

export interface OfflineAtivos {
  gerado_em: string
  dias_offline: number
  incluir_sem_contrato: boolean
  historico_desde: string | null
  onus_offline_total: number
  total: number
  contagem: Record<string, number>
  itens: ItemOffline[]
}
