/**
 * Cores e rótulos da tela CTOs. Reaproveita a escala fixa de status do app
 * (lib/status.ts: good/warning/critical) - nunca cor sozinha: sempre com
 * rótulo/badge, e no mapa com legenda.
 */
import { statusStyles } from '@/lib/status'
import type { CtoPapel, CtoSituacao, InferenciaStatus } from '@/types/ctos'

type BadgeVariant = 'success' | 'warning' | 'destructive' | 'outline' | 'secondary'

const NEUTRO = '#8a8f98'

export const situacaoStyles: Record<CtoSituacao, { label: string; color: string; badge: BadgeVariant }> = {
  livre: { label: 'Com portas livres', color: statusStyles.good.dot, badge: 'success' },
  quase_cheia: { label: 'Quase cheia (75%+)', color: statusStyles.warning.dot, badge: 'warning' },
  cheia: { label: 'Cheia', color: statusStyles.critical.dot, badge: 'destructive' },
  acima: { label: 'Acima da capacidade', color: statusStyles.critical.dot, badge: 'destructive' },
  sem_capacidade: { label: 'Sem nº de portas', color: NEUTRO, badge: 'outline' },
}

export const statusInferenciaStyles: Record<InferenciaStatus, { label: string; badge: BadgeVariant }> = {
  confirmado: { label: 'Confirmado', badge: 'success' },
  provavel: { label: 'Provável', badge: 'warning' },
  divergente: { label: 'Divergente', badge: 'destructive' },
  incerto: { label: 'Incerto', badge: 'outline' },
  sem_candidata: { label: 'Sem candidata', badge: 'secondary' },
}

export const papelStyles: Record<CtoPapel, { label: string; badge: BadgeVariant; descricao: string }> = {
  confirmado: { label: 'Confirmado', badge: 'success', descricao: 'Cadastrado aqui e a rede confirma' },
  provavel: { label: 'Provável', badge: 'warning', descricao: 'Sem cadastro de CTO; a rede aponta esta' },
  veio_de_outra: {
    label: 'Cadastro em outra',
    badge: 'warning',
    descricao: 'Cadastrado em outra CTO, mas a rede aponta esta',
  },
  possivel: { label: 'Possível', badge: 'outline', descricao: 'Melhor candidata, mas sem certeza - não entra na ocupação' },
  suspeito: {
    label: 'Provavelmente não está aqui',
    badge: 'destructive',
    descricao: 'Cadastrado aqui, mas a rede aponta outra CTO',
  },
}
