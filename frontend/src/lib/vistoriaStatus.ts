import type { Contrato, PapelVistoria, PortaResultado } from '@/types/vistoria'

type BadgeVariant = 'success' | 'warning' | 'destructive' | 'outline' | 'secondary'

export const contratoStyles: Record<Contrato, { badge: BadgeVariant }> = {
  ativo: { badge: 'success' },
  bloqueado: { badge: 'warning' },
  inativo: { badge: 'destructive' },
  sem_contrato: { badge: 'destructive' },
}

export const resultadoStyles: Record<PortaResultado, { label: string; badge: BadgeVariant }> = {
  cliente: { label: 'Cliente', badge: 'success' },
  vazia: { label: 'Vazia', badge: 'secondary' },
  sem_ont_ativa: { label: 'Fantasma (sem ONT ativa)', badge: 'destructive' },
  nao_identificado: { label: 'Não identificado', badge: 'warning' },
}

export const papelVistoriaLabel: Record<PapelVistoria, string> = {
  confirmado: 'Confirmado',
  provavel: 'Provável',
  veio_de_outra: 'Cadastro em outra CTO',
  possivel: 'Possível',
  suspeito: 'Cadastrado aqui, rede aponta outra',
  sem_ont: 'Cadastrado aqui, ONT não existe na OLT',
}
