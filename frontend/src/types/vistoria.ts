/** Tipos da vistoria de CTO - espelham olt/vistoria_views.py. */
import type { CtoRef } from './ctos'

export type PortaResultado = 'cliente' | 'vazia' | 'sem_ont_ativa' | 'nao_identificado'
export type PortaMetodo = 'etiqueta' | 'desconexao' | 'manual'
export type Contrato = 'ativo' | 'bloqueado' | 'inativo' | 'sem_contrato'
export type PapelVistoria = 'confirmado' | 'provavel' | 'veio_de_outra' | 'possivel' | 'suspeito' | 'sem_ont'

export interface ClienteInfo {
  serial: string
  cliente_nome: string
  endereco: string
  pon: string
  position: number | null
  oper_state: string | null
  online: boolean
  olt_rx_sig: number | null
  ultimo_online: string | null
  offline_ha_dias: number | null
  contrato: Contrato
  contrato_rotulo: string
  fantasma_provavel: boolean
  cto_provavel: CtoRef | null
  inferencia_status: string | null
}

export interface Candidato extends ClienteInfo {
  papel: PapelVistoria
  cadastrado_aqui: boolean
  /** Já identificado nesta vistoria (com ou sem porta). */
  registrado: boolean
  porta_registrada: number | null
}

export interface PortaRegistro {
  id: number
  /** null = identificado na caixa sem saber a porta. */
  porta: number | null
  resultado: PortaResultado
  metodo: PortaMetodo
  serial: string
  pon: string
  position: number | null
  cliente_nome: string
  reconexao_confirmada: boolean
  observacao: string
  registrado_em: string
}

export interface VistoriaBasica {
  id: number
  cto: { id: number; descricao: string; portas: number | null; ramal: string }
  olt_id: number | null
  olt_nome: string | null
  usuario: string
  tecnico: string
  observacao: string
  iniciada_em: string
  finalizada_em: string | null
  resumo?: Partial<Record<PortaResultado, number>>
}

export interface VistoriaDetalhe extends VistoriaBasica {
  portas: PortaRegistro[]
  candidatos: Candidato[]
  pons: string[]
}

export interface EventoAoVivo extends ClienteInfo {
  id: number
  ocorrido_em: string
  tipo: string
  alarme: string
  voltou: boolean
  candidato_desta_cto: boolean
  /** Queda numa PON onde a caixa tem clientes. */
  mesma_pon_da_caixa: boolean
  /** Quantas ONTs da mesma PON caíram junto (1 = só esta). */
  caiu_junto: number
}

export interface EventosResposta {
  agora: string
  pons_da_caixa: string[]
  eventos: EventoAoVivo[]
}

export interface Correcoes {
  clientes: {
    serial: string
    cliente_nome: string
    cto_cadastro: string | null
    cto_campo: { id: number; descricao: string; ixc_id: string | null }
    porta: number | null
    vistoria_id: number
    vistoriado_em: string
  }[]
  portas_fantasma: {
    cto: CtoRef
    porta: number | null
    observacao: string
    vistoria_id: number
    vistoriado_em: string
  }[]
  escrita_ixc_permitida: boolean
  pode_corrigir: boolean
}

export interface CorrecaoIxc {
  id: number
  serial: string
  cliente_nome: string
  caixa_antes: string
  cto: CtoRef | null
  usuario: string
  status: 'ok' | 'alerta' | 'erro'
  mensagem: string
  outros_campos_alterados: string[]
  criado_em: string
}
