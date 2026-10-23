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

export interface AchadoOnu {
  serial: string
  cliente: string
  sinal: number
  ont_rx: number | null
  distancia: number | null
}

export interface AchadoCaixa {
  nivel: 'backbone' | 'pon' | 'ceo' | 'ramal' | 'cabo' | 'cto' | 'clientes' | 'sem_caixa'
  severidade: 'alta' | 'media' | 'baixa'
  referencia: string
  olt_id: number
  olt_nome: string
  pon: string
  ramal: string
  /** Splitter de distribuição (CEO/CD) do projeto. */
  ceo?: string
  /** Fibra de alimentação da CEO (backbone), ex.: "F.O.02 do CFOA_02". */
  alimentacao?: string
  cto: { id: number; descricao: string; splitter: string; portas: number | null } | null
  clientes: number
  ruins: number
  mediana: number
  pior: number
  melhor: number
  mediana_referencia: number | null
  delta: number | null
  delta_ajustado: number | null
  esperado_splitter?: number
  ajuste_distancia?: number
  dispersao?: number
  tendencia: { mediana_antes: number; variacao: number; texto: string } | null
  diagnostico: string
  onus: AchadoOnu[]
}

export interface SinalCaixas {
  limiar: number
  gerado_em: string
  onts_analisadas: number
  onts_ruins: number
  contagem: Record<AchadoCaixa['nivel'], number>
  achados: AchadoCaixa[]
}

export interface CaixaNoMapa {
  id: number
  descricao: string
  lat: number
  lon: number
  ceo: string
  ramal: string
  pon: string
  olt_id: number
  clientes: number
  ruins: number
  mediana: number
  pior: number
}

export interface SinalCaixasMapa {
  limiar: number
  gerado_em: string
  caixas: CaixaNoMapa[]
  achados: {
    indice: number
    nivel: AchadoCaixa['nivel']
    severidade: AchadoCaixa['severidade']
    referencia: string
    pon: string
    diagnostico: string
    ruins: number
    clientes: number
    mediana: number
    ctos: number[]
  }[]
}
