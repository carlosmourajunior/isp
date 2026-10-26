/** Tipos da tela CTOs - espelham olt/cto_views.py. */

export type CtoSituacao = 'livre' | 'quase_cheia' | 'cheia' | 'acima' | 'sem_capacidade'

export type InferenciaStatus = 'vistoriado' | 'confirmado' | 'provavel' | 'divergente' | 'incerto' | 'sem_candidata'

/** Papel de um cliente em relação à CTO consultada. */
export type CtoPapel = 'confirmado' | 'provavel' | 'veio_de_outra' | 'possivel' | 'suspeito'

export interface CtoRef {
  id: number
  descricao: string
}

export interface Cto {
  id: number
  descricao: string
  tipo: string
  origem: 'ixc' | 'kmz'
  ixc_id: string | null
  olt_id: number | null
  olt_nome: string | null
  ramal: string
  latitude: number | null
  longitude: number | null
  /** Portas físicas: projeto + splitters adicionados em campo. */
  portas: number | null
  portas_base: number | null
  /** Portas definidas à mão no painel (vale sobre projeto e IXC). */
  portas_manual: number | null
  /** Portas do projeto (KMZ) ou, sem projeto, do cadastro do IXC. */
  portas_projeto: number | null
  /** Portas que podem receber cliente (físicas - inutilizadas). */
  portas_uteis: number | null
  splitters_extras: number[]
  portas_inutilizadas: number[]
  splitter: string
  confirmados: number
  provaveis: number
  vindos_de_outra: number
  possiveis: number
  suspeitos: number
  offline: number
  ocupadas: number
  livres: number | null
  situacao: CtoSituacao
  cadastro_ixc: number
}

export interface Motivos {
  provavel?: string[]
  alternativa?: string[]
  cadastro?: string[]
}

export interface CtoCliente {
  id: number
  serial: string
  olt_nome: string
  pon: string
  position: number
  cliente_nome: string
  distance_km: number | null
  oper_state: string | null
  olt_rx_sig: number | null
  status: InferenciaStatus
  papel: CtoPapel
  cto_cadastro: CtoRef | null
  cto_provavel: CtoRef | null
  cto_alternativa: CtoRef | null
  score: number | null
  motivos: Motivos
}

export interface CtoDetail extends Cto {
  pons: string[]
  clientes: CtoCliente[]
  calculado_em: string | null
}

export interface CtoInferencia {
  id: number
  olt: number
  olt_nome: string
  pon: string
  position: number
  serial: string
  cliente_nome: string
  distance_km: number | null
  cto_cadastro: CtoRef | null
  cto_provavel: CtoRef | null
  cto_alternativa: CtoRef | null
  score: number | null
  score_alternativa: number | null
  status: InferenciaStatus
  motivos: Motivos
  calculado_em: string
}

export interface CtoResumo {
  onts: number
  ancoras: number
  por_status: Record<InferenciaStatus, number>
  calculado_em: string | null
}
