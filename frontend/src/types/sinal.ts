export interface SinalResumo {
  total: number
  bom: number
  alerta: number
  critico: number
  sem_leitura: number
  ultima_coleta: string | null
}

export type TipoVariacao = 'piorou' | 'oscilando' | 'melhorou'
export type FaixaSinal = 'bom' | 'alerta' | 'critico' | 'sem_leitura'

export interface VariacaoItem {
  serial: string
  olt_id: number
  olt_nome: string | null
  pon: string
  position: number
  cliente_nome: string
  login: string
  cto: { id: number; descricao: string; ramal: string } | null
  alarmes: Partial<Record<'sinal_baixo' | 'sinal_degradado' | 'tx_alto' | 'sinal_alto' | 'quedas' | 'falta_energia', number>>
  tipo: TipoVariacao
  referencia: number
  referencia_periodo_anterior: boolean
  atual: number
  minimo: number
  maximo: number
  delta: number
  amplitude: number
  leituras: number
  faixa_atual: FaixaSinal
  diagnostico: string
}

export interface VariacaoGrupo {
  nivel: 'cto' | 'pon'
  referencia: string
  cto_id: number | null
  ramal: string
  pon: string
  afetados: number
  total: number
  delta_medio: number
  diagnostico: string
  serials: string[]
}

export interface SinalVariacao {
  periodo: '24h' | '7d'
  limiar_db: number
  inicio: string
  gerado_em: string
  onts_com_leitura: number
  leituras_no_periodo: number
  contagem: Partial<Record<TipoVariacao, number>>
  grupos: VariacaoGrupo[]
  itens: VariacaoItem[]
}
