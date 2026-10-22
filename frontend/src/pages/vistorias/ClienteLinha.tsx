import { Badge } from '@/components/ui/badge'
import { statusStyles } from '@/lib/status'
import { contratoStyles } from '@/lib/vistoriaStatus'
import type { ClienteInfo } from '@/types/vistoria'

/** Nome + online/offline + contrato + fantasma: o que a bancada precisa bater o olho. */
export function ClienteLinha({ c, extra }: { c: ClienteInfo; extra?: React.ReactNode }) {
  const dot = c.online ? statusStyles.good.dot : statusStyles.critical.dot
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="inline-block size-2 shrink-0 rounded-full" style={{ backgroundColor: dot }} />
        <span className="font-medium text-foreground">{c.cliente_nome || '(sem cliente no IXC)'}</span>
        {c.login && c.login !== c.cliente_nome && (
          <span className="rounded bg-secondary px-1.5 py-0.5 font-mono text-xs text-foreground">{c.login}</span>
        )}
        {c.outros_logins.length > 0 && (
          <Badge variant="warning" title={`Outros logins: ${c.outros_logins.map((o) => o.login || o.serial).join(', ')}`}>
            +{c.outros_logins.length} login{c.outros_logins.length > 1 ? 's' : ''}
          </Badge>
        )}
        {c.fantasma_provavel && <Badge variant="destructive">Fantasma provável</Badge>}
        {extra}
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        <span>{c.serial}</span>
        {c.pon && (
          <span>
            {c.pon}/{c.position}
          </span>
        )}
        <span>
          {c.online ? 'online' : c.oper_state ? 'offline' : 'ONT não encontrada'}
          {!c.online && c.offline_ha_dias !== null && ` há ${c.offline_ha_dias} dia(s)`}
        </span>
        <Badge variant={contratoStyles[c.contrato].badge}>{c.contrato_rotulo}</Badge>
      </div>
    </div>
  )
}
