import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Loader2, Radio, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { EventoAoVivo, EventosResposta } from '@/types/vistoria'
import { ClienteLinha } from './ClienteLinha'

interface Props {
  vistoriaId: number
  /** Portas ainda sem registro - o cliente identificado pode ir para uma delas (opcional). */
  portasLivres: number[]
  /** Grava o cliente na caixa (porta null = porta desconhecida). */
  onIdentificado: (evento: EventoAoVivo, porta: number | null) => Promise<void>
  /** OLT confirmou que o cliente voltou. */
  onReconectado: (evento: EventoAoVivo, porta: number | null) => Promise<void>
  onSemOntAtiva: (porta: number | null) => Promise<void>
  onNovaIdentificacao: () => void
  onClose: () => void
}

type Fase = 'iniciando' | 'aguardando_queda' | 'aguardando_volta'

const POLL_MS = 2000
// Depois disso sem nenhuma queda, o drop desconectado provavelmente não tem ONT ativa.
const SUGERIR_FANTASMA_S = 90

function SeletorPorta({ portas, value, onChange }: { portas: number[]; value: string; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-8 rounded-md border border-input bg-background px-2 text-xs"
      aria-label="Porta"
    >
      <option value="">Porta não informada</option>
      {portas.map((p) => (
        <option key={p} value={p}>
          Porta {p}
        </option>
      ))}
    </select>
  )
}

function avisos(e: EventoAoVivo, ponsDaCaixa: string[]) {
  const lista: string[] = []
  if (!e.mesma_pon_da_caixa) {
    lista.push(
      ponsDaCaixa.length
        ? `Queda na PON ${e.pon}, que não é a PON desta caixa (${ponsDaCaixa.join(', ')}) - provavelmente outro ponto da rede.`
        : `Queda na PON ${e.pon}. A PON desta caixa ainda não é conhecida - confira com o técnico.`,
    )
  }
  if (e.caiu_junto > 1) {
    lista.push(`${e.caiu_junto} ONTs da PON ${e.pon} caíram juntas - pode ser rompimento ou queda de energia, não a desconexão do técnico.`)
  }
  return lista
}

/**
 * "Desconecta e vê quem caiu", automático e sem depender da porta: escuta as
 * desconexões (alarme "ONT inativa" via syslog), destaca as quedas na PON da
 * caixa e avisa quando a queda parece ser em outro ponto da rede. Depois espera
 * o mesmo cliente voltar - ninguém fica desconectado por esquecimento.
 */
export function IdentificacaoAoVivo({
  vistoriaId,
  portasLivres,
  onIdentificado,
  onReconectado,
  onSemOntAtiva,
  onNovaIdentificacao,
  onClose,
}: Props) {
  const [fase, setFase] = useState<Fase>('iniciando')
  const [desde, setDesde] = useState<string | null>(null)
  const [ponsDaCaixa, setPonsDaCaixa] = useState<string[]>([])
  const [eventos, setEventos] = useState<EventoAoVivo[]>([])
  const [escolhido, setEscolhido] = useState<EventoAoVivo | null>(null)
  const [portaEscolhida, setPortaEscolhida] = useState<number | null>(null)
  const [portaPorEvento, setPortaPorEvento] = useState<Record<number, string>>({})
  const [portaFantasma, setPortaFantasma] = useState('')
  const [segundos, setSegundos] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const inicio = useRef(0)
  const avisouVolta = useRef(false)

  // Relógio do servidor como ponto de partida (o do navegador pode estar adiantado).
  useEffect(() => {
    api
      .get<EventosResposta>(`/vistorias/${vistoriaId}/eventos/`)
      .then((r) => {
        setDesde(r.data.agora)
        setPonsDaCaixa(r.data.pons_da_caixa)
        setFase('aguardando_queda')
        inicio.current = Date.now()
      })
      .catch(() => setErro('Não foi possível falar com o servidor.'))
  }, [vistoriaId])

  const voltou = useMemo(
    () =>
      fase === 'aguardando_volta' &&
      escolhido !== null &&
      eventos.some(
        (e) =>
          e.voltou && e.pon === escolhido.pon && e.position === escolhido.position && e.ocorrido_em >= escolhido.ocorrido_em,
      ),
    [eventos, fase, escolhido],
  )

  useEffect(() => {
    if (voltou && escolhido && !avisouVolta.current) {
      avisouVolta.current = true
      onReconectado(escolhido, portaEscolhida).catch(() => undefined)
    }
  }, [voltou, escolhido, portaEscolhida, onReconectado])

  useEffect(() => {
    if (!desde || voltou) return
    const id = setInterval(async () => {
      setSegundos(Math.round((Date.now() - inicio.current) / 1000))
      try {
        const r = await api.get<EventosResposta>(`/vistorias/${vistoriaId}/eventos/`, { params: { desde } })
        setEventos(r.data.eventos)
        setPonsDaCaixa(r.data.pons_da_caixa)
        setErro(null)
      } catch {
        setErro('Falha ao consultar a OLT - tentando de novo…')
      }
    }, POLL_MS)
    return () => clearInterval(id)
  }, [desde, voltou, vistoriaId])

  // Uma linha por ONT (a queda mais recente). Ordem: candidatos da caixa na PON
  // da caixa > outros na PON da caixa > o resto.
  const quedas = useMemo(() => {
    const vistos = new Set<string>()
    const unicas = [...eventos]
      .reverse()
      .filter((e) => !e.voltou)
      .filter((e) => {
        const chave = `${e.pon}/${e.position}`
        if (vistos.has(chave)) return false
        vistos.add(chave)
        return true
      })
    const peso = (e: EventoAoVivo) =>
      (e.mesma_pon_da_caixa ? 4 : 0) + (e.candidato_desta_cto ? 2 : 0) + (e.caiu_junto === 1 ? 1 : 0)
    return unicas.sort((a, b) => peso(b) - peso(a))
  }, [eventos])
  const naPonDaCaixa = quedas.filter((e) => e.mesma_pon_da_caixa)
  const foraDaPon = quedas.filter((e) => !e.mesma_pon_da_caixa)

  async function escolher(evento: EventoAoVivo) {
    const bruto = portaPorEvento[evento.id] ?? ''
    const porta = bruto ? Number(bruto) : null
    setSalvando(true)
    try {
      await onIdentificado(evento, porta)
      setEscolhido(evento)
      setPortaEscolhida(porta)
      setFase('aguardando_volta')
    } catch {
      // O erro já foi avisado por quem salvou; continua escutando.
    } finally {
      setSalvando(false)
    }
  }

  const linha = (e: EventoAoVivo) => {
    const alertas = avisos(e, ponsDaCaixa)
    return (
      <div
        key={e.id}
        className={
          alertas.length
            ? 'flex flex-col gap-2 rounded-md border border-amber-500/50 bg-amber-500/5 px-3 py-2'
            : 'flex flex-col gap-2 rounded-md border border-border px-3 py-2'
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <ClienteLinha
            c={e}
            extra={
              <>
                <Badge variant={e.mesma_pon_da_caixa ? 'success' : 'warning'}>PON {e.pon}</Badge>
                {e.candidato_desta_cto && <Badge variant="success">Cliente desta caixa</Badge>}
                <span className="text-xs text-muted-foreground">caiu às {new Date(e.ocorrido_em).toLocaleTimeString('pt-BR')}</span>
              </>
            }
          />
          <div className="flex items-center gap-2">
            <SeletorPorta
              portas={portasLivres}
              value={portaPorEvento[e.id] ?? ''}
              onChange={(v) => setPortaPorEvento((m) => ({ ...m, [e.id]: v }))}
            />
            <Button size="sm" disabled={salvando} onClick={() => escolher(e)}>
              É este
            </Button>
          </div>
        </div>
        {alertas.map((a) => (
          <div key={a} className="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-400">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {a}
          </div>
        ))}
      </div>
    )
  }

  return (
    <Card className="gap-0 border-primary/50 py-0">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 font-semibold">
          <Radio className="size-4 text-primary" /> Identificar por desconexão
          {ponsDaCaixa.length > 0 && (
            <span className="text-xs font-normal text-muted-foreground">PON da caixa: {ponsDaCaixa.join(', ')}</span>
          )}
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-muted-foreground hover:bg-accent" aria-label="Fechar">
          <X className="size-4" />
        </button>
      </div>

      <div className="flex flex-col gap-3 px-4 py-4 text-sm">
        {fase === 'iniciando' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Preparando…
          </div>
        )}

        {fase === 'aguardando_queda' && (
          <>
            <div className="rounded-md bg-primary/10 px-3 py-2">
              <div className="font-medium">Peça para o técnico desconectar o drop que quer identificar.</div>
              <div className="text-xs text-muted-foreground">
                Escutando desconexões na OLT há {segundos}s. O alarme costuma chegar em alguns segundos. Se souber a porta,
                escolha ao lado do cliente - é opcional.
              </div>
            </div>

            {quedas.length === 0 && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Nenhuma ONT caiu ainda…
              </div>
            )}

            {naPonDaCaixa.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="text-xs font-medium text-muted-foreground">Na PON desta caixa</div>
                {naPonDaCaixa.map(linha)}
              </div>
            )}

            {foraDaPon.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="text-xs font-medium text-amber-700 dark:text-amber-400">
                  Em outras PONs - provavelmente não é a desconexão do técnico
                </div>
                {foraDaPon.map(linha)}
              </div>
            )}

            {segundos >= SUGERIR_FANTASMA_S && naPonDaCaixa.length === 0 && (
              <div className="flex flex-col gap-2 rounded-md bg-amber-500/10 px-3 py-2 text-amber-700 dark:text-amber-400">
                <span>
                  Nada caiu na PON desta caixa em {SUGERIR_FANTASMA_S}s. Se o drop desconectado está ligado, não tem ONT ativa do
                  outro lado: drop fantasma, porta a liberar.
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  <SeletorPorta portas={portasLivres} value={portaFantasma} onChange={setPortaFantasma} />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onSemOntAtiva(portaFantasma ? Number(portaFantasma) : null)}
                  >
                    Registrar drop fantasma
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {fase === 'aguardando_volta' && !voltou && escolhido && (
          <div className="flex flex-col gap-2">
            <div className="rounded-md bg-emerald-500/10 px-3 py-2">
              <strong>{escolhido.cliente_nome || escolhido.serial}</strong> registrado nesta caixa
              {portaEscolhida ? ` (porta ${portaEscolhida})` : ''}.
            </div>
            <div className="flex items-center gap-2 font-medium">
              <Loader2 className="size-4 animate-spin" /> Peça para reconectar - aguardando a ONT voltar…
            </div>
            <div className="text-xs text-muted-foreground">Não feche antes de confirmar: assim ninguém fica desconectado por engano.</div>
          </div>
        )}

        {voltou && escolhido && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 px-3 py-2 font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="size-4" /> {escolhido.cliente_nome || escolhido.serial} voltou. Conferido.
            </div>
            <Button size="sm" className="w-fit" onClick={onNovaIdentificacao}>
              Identificar outro cliente
            </Button>
          </div>
        )}

        {erro && <div className="text-xs text-destructive">{erro}</div>}
      </div>
    </Card>
  )
}
