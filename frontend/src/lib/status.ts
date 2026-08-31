/**
 * Cores de status centralizadas - escala fixa (good/warning/critical) da
 * skill dataviz, validada (validate_palette.js) contra o acento violeta do
 * app. Nunca reaproveitada como cor categórica; sempre usada com ícone +
 * texto (badges), nunca cor sozinha - ver plano em
 * ~/.claude/plans/wiggly-sparking-scone.md.
 */

export type StatusLevel = 'good' | 'warning' | 'critical'

interface StatusStyle {
  label: string
  /** Variant do componente Badge (frontend/src/components/ui/badge.tsx). */
  badgeVariant: 'success' | 'warning' | 'destructive'
  /** Hex exato validado - usado em pontos/chips pequenos onde a identidade da cor importa
   * mais que legibilidade de texto (ex: dot de status "vivo", ícone de StatCard). */
  dot: string
}

export const statusStyles: Record<StatusLevel, StatusStyle> = {
  good: { label: 'Bom', badgeVariant: 'success', dot: '#0ca30c' },
  warning: { label: 'Aviso', badgeVariant: 'warning', dot: '#fab219' },
  critical: { label: 'Crítico', badgeVariant: 'destructive', dot: '#d03b3b' },
}

/** Estado operacional (up/down) de uma ONU/porta. */
export function operStateStatus(state: string | null | undefined): StatusLevel {
  return state?.toLowerCase() === 'up' ? 'good' : 'critical'
}

/**
 * Faixa de sinal óptico (dBm). Mesmos limiares já usados no dashboard e no
 * backend (olt/api_views.py::onu_health_summary): bom acima de -27, aviso
 * entre -27 e -29, crítico abaixo de -29.
 */
export function signalStatus(dbm: number | null | undefined): StatusLevel {
  if (dbm === null || dbm === undefined) return 'warning'
  if (dbm >= -27) return 'good'
  if (dbm >= -29) return 'warning'
  return 'critical'
}
