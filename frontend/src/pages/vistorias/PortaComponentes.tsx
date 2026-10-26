import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, History, Loader2, Search, Tag } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { resultadoStyles } from '@/lib/vistoriaStatus'
import type { ClienteInfo, PortaRegistro, PortaResultado } from '@/types/vistoria'
import { ClienteLinha } from './ClienteLinha'

/** Peças de porta usadas na vistoria e no painel de edição da CTO. */

export interface SalvarPorta {
  porta: number | null
  resultado: PortaResultado
  serial?: string
  metodo?: 'etiqueta' | 'desconexao' | 'manual'
  reconexao_confirmada?: boolean
  observacao?: string
}

/** Escolher o cliente da etiqueta: primeiro entre os candidatos, depois busca no cadastro todo. */
export function EscolherCliente({
  candidatos,
  porta,
  onEscolher,
  onClose,
}: {
  candidatos: ClienteInfo[]
  /** null = cliente da caixa sem saber a porta. */
  porta: number | null
  onEscolher: (serial: string) => void
  onClose: () => void
}) {
  const [termo, setTermo] = useState('')
  const filtrados = useMemo(() => {
    const t = termo.trim().toLowerCase()
    return t
      ? candidatos.filter(
          (c) =>
            c.cliente_nome.toLowerCase().includes(t) ||
            c.login.toLowerCase().includes(t) ||
            c.serial.toLowerCase().includes(t),
        )
      : candidatos
  }, [candidatos, termo])

  const buscaAtiva = termo.trim().length >= 3
  const { data: foraBruto, isFetching } = useQuery({
    queryKey: ['/vistorias/clientes/', termo],
    queryFn: async () => (await api.get<ClienteInfo[]>('/vistorias/clientes/', { params: { q: termo } })).data,
    enabled: buscaAtiva,
  })
  // Fora da lista = resultados do cadastro todo que não são candidatos desta caixa.
  const fora = useMemo(() => {
    const daCaixa = new Set(candidatos.map((c) => c.serial))
    return (foraBruto ?? []).filter((c) => !daCaixa.has(c.serial))
  }, [foraBruto, candidatos])

  const opcao = (c: ClienteInfo, extra?: React.ReactNode) => (
    <button
      key={c.serial}
      type="button"
      onClick={() => onEscolher(c.serial)}
      className="rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-accent"
    >
      <ClienteLinha c={c} extra={extra} />
      {c.outros_logins.length > 0 && (
        <div className="mt-1 text-xs text-amber-700 dark:text-amber-400">
          Este titular tem outro(s) login(s): {c.outros_logins.map((o) => o.login || o.serial).join(', ')}. Confira qual é o
          desta caixa pela etiqueta - na dúvida, identifique por desconexão.
        </div>
      )}
    </button>
  )

  return (
    <Card className="gap-0 border-primary/50 py-0">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 font-semibold">
          <Tag className="size-4 text-primary" /> {porta !== null ? `Cliente da porta ${porta} (etiqueta)` : 'Cliente da caixa (porta não informada)'}
        </div>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
      </div>
      <div className="flex max-h-[28rem] flex-col gap-2 overflow-y-auto px-4 py-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Nome, login da etiqueta ou serial…"
            className="pl-8"
          />
        </div>

        <div className="text-xs font-medium text-muted-foreground">Candidatos desta caixa</div>
        {filtrados.length > 0 ? (
          filtrados.map((c) => opcao(c))
        ) : (
          <div className="text-sm text-muted-foreground">Nenhum candidato com esse nome.</div>
        )}

        {buscaAtiva && (
          <>
            <div className="mt-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
              No cadastro todo (cliente que o IXC coloca em outra caixa)
              {isFetching && <Loader2 className="size-3 animate-spin" />}
            </div>
            {fora.map((c) =>
              opcao(
                c,
                c.cto_provavel && (
                  <span className="text-xs text-muted-foreground">rede aponta {c.cto_provavel.descricao}</span>
                ),
              ),
            )}
            {!isFetching && fora.length === 0 && (
              <div className="text-sm text-muted-foreground">Nenhum outro cliente com esse nome. Tente por desconexão.</div>
            )}
          </>
        )}
        {!buscaAtiva && (
          <div className="text-xs text-muted-foreground">
            Digite 3 letras ou mais para procurar também no cadastro todo.
          </div>
        )}
      </div>
    </Card>
  )
}

export function PortaCard({
  numero,
  registro,
  ativa,
  inutilizada,
  finalizada,
  onEtiqueta,
  onMarcar,
  onLimpar,
  onInutilizar,
  anterior,
  onConfirmar,
}: {
  numero: number
  registro?: PortaRegistro
  ativa: boolean
  inutilizada: boolean
  finalizada: boolean
  /** Registro de uma sessão anterior da ficha, ainda não conferido nesta. */
  anterior?: boolean
  onConfirmar?: () => void
  onEtiqueta: () => void
  onMarcar: (resultado: PortaResultado) => void
  onLimpar: () => void
  onInutilizar: (inutilizar: boolean) => void
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-2 rounded-lg border border-border p-3',
        anterior && 'border-dashed bg-muted/30',
        ativa && 'border-primary ring-1 ring-primary',
        inutilizada && 'border-dashed bg-muted/40',
      )}
    >
      <div className="flex items-center justify-between">
        <span className={cn('text-sm font-semibold', inutilizada && 'text-muted-foreground line-through')}>Porta {numero}</span>
        {inutilizada ? (
          <Badge variant="secondary">Inutilizada</Badge>
        ) : registro ? (
          <Badge variant={resultadoStyles[registro.resultado].badge}>{resultadoStyles[registro.resultado].label}</Badge>
        ) : (
          <Badge variant="outline">Pendente</Badge>
        )}
      </div>

      {registro?.resultado === 'cliente' && <RegistroCliente registro={registro} />}
      {registro && registro.resultado !== 'cliente' && registro.observacao && (
        <div className="text-xs text-muted-foreground">{registro.observacao}</div>
      )}
      {registro && <QuandoRegistrado registro={registro} anterior={anterior} />}
      {!finalizada && anterior && registro && onConfirmar && (
        <Button size="sm" variant="outline" className="w-fit" onClick={onConfirmar}>
          <CheckCircle2 /> Continua assim
        </Button>
      )}

      {!finalizada && inutilizada && (
        <Button size="sm" variant="ghost" className="w-fit" onClick={() => onInutilizar(false)}>
          Reativar porta
        </Button>
      )}

      {!finalizada && !inutilizada && (
        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="outline" onClick={onEtiqueta}>
            <Tag /> Etiqueta
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onMarcar('vazia')}>
            Vazia
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onMarcar('sem_ont_ativa')}>
            Fantasma
          </Button>
          {registro && (
            <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={onLimpar}>
              Limpar
            </Button>
          )}
          <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => onInutilizar(true)}>
            Inutilizar
          </Button>
        </div>
      )}
    </div>
  )
}

export function RegistroCliente({ registro }: { registro: PortaRegistro }) {
  return (
    <div className="text-sm">
      <div className="font-medium">{registro.cliente_nome || registro.serial}</div>
      <div className="text-xs text-muted-foreground">
        {registro.serial}
        {registro.pon && ` · PON ${registro.pon}`} · {registro.metodo === 'desconexao' ? 'por desconexão' : 'por etiqueta'}
        {registro.reconexao_confirmada && (
          <span className="ml-1 inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="size-3" /> voltou
          </span>
        )}
      </div>
    </div>
  )
}


export function QuandoRegistrado({ registro, anterior }: { registro: PortaRegistro; anterior?: boolean }) {
  return (
    <div className={cn('flex items-center gap-1 text-[11px] text-muted-foreground', anterior && 'text-amber-700 dark:text-amber-400')}>
      {anterior && <History className="size-3" />}
      {anterior ? 'De vistoria anterior: ' : ''}
      {new Date(registro.registrado_em).toLocaleDateString('pt-BR')}
      {registro.registrado_por && ` por ${registro.registrado_por}`}
    </div>
  )
}
