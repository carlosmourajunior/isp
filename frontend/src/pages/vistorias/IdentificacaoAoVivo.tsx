import { useEffect, useMemo, useRef, useState } from 'react'
import { CheckCircle2, Loader2, Radio, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { EventoAoVivo } from '@/types/vistoria'
import { ClienteLinha } from './ClienteLinha'

interface Props {
  vistoriaId: number
  porta: number
  /** Grava a porta com o cliente escolhido. */
  onIdentificado: (evento: EventoAoVivo) => Promise<void>
  /** OLT confirmou que o cliente voltou. */
  onReconectado: (evento: EventoAoVivo) => Promise<void>
  onSemOntAtiva: () => Promise<void>
  onClose: () => void
}

type Fase = 'iniciando' | 'aguardando_queda' | 'aguardando_volta'

const POLL_MS = 2000
// Depois disso sem nenhuma queda, a porta provavelmente não tem ONT ativa.
const SUGERIR_FANTASMA_S = 90

interface Resposta {
  agora: string
  eventos: EventoAoVivo[]
}

/**
 * "Desconecta e vê quem caiu", automático: escuta as desconexões (alarme
 * "ONT inativa" via syslog) a partir do momento em que a bancada começa, e
 * depois espera o mesmo cliente voltar - ninguém fica desconectado por esquecimento.
 */
export function IdentificacaoAoVivo({ vistoriaId, porta, onIdentificado, onReconectado, onSemOntAtiva, onClose }: Props) {
  const [fase, setFase] = useState<Fase>('iniciando')
  const [desde, setDesde] = useState<string | null>(null)
  const [eventos, setEventos] = useState<EventoAoVivo[]>([])
  const [escolhido, setEscolhido] = useState<EventoAoVivo | null>(null)
  const [segundos, setSegundos] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const inicio = useRef(0)
  const avisouVolta = useRef(false)

  // Relógio do servidor como ponto de partida (o do navegador pode estar adiantado).
  useEffect(() => {
    api
      .get<Resposta>(`/vistorias/${vistoriaId}/eventos/`)
      .then((r) => {
        setDesde(r.data.agora)
        setFase('aguardando_queda')
        inicio.current = Date.now()
      })
      .catch(() => setErro('Não foi possível falar com o servidor.'))
  }, [vistoriaId])

  // Esperando a volta: o mesmo pon/posição com alarme encerrado depois da queda escolhida.
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
      onReconectado(escolhido).catch(() => undefined)
    }
  }, [voltou, escolhido, onReconectado])

  useEffect(() => {
    if (!desde || voltou) return
    const id = setInterval(async () => {
      setSegundos(Math.round((Date.now() - inicio.current) / 1000))
      try {
        const r = await api.get<Resposta>(`/vistorias/${vistoriaId}/eventos/`, { params: { desde } })
        setEventos(r.data.eventos)
        setErro(null)
      } catch {
        setErro('Falha ao consultar a OLT - tentando de novo…')
      }
    }, POLL_MS)
    return () => clearInterval(id)
  }, [desde, voltou, vistoriaId])

  const quedas = useMemo(() => {
    const vistos = new Set<string>()
    return eventos
      .filter((e) => !e.voltou)
      .reverse()
      .filter((e) => {
        const chave = `${e.pon}/${e.position}`
        if (vistos.has(chave)) return false
        vistos.add(chave)
        return true
      })
      .sort((a, b) => Number(b.candidato_desta_cto) - Number(a.candidato_desta_cto))
  }, [eventos])

  async function escolher(evento: EventoAoVivo) {
    setSalvando(true)
    try {
      await onIdentificado(evento)
      setEscolhido(evento)
      setFase('aguardando_volta')
    } catch {
      // O erro já foi avisado por quem salvou; continua escutando.
    } finally {
      setSalvando(false)
    }
  }

  return (
    <Card className="gap-0 border-primary/50 py-0">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 font-semibold">
          <Radio className="size-4 text-primary" /> Identificar porta {porta} por desconexão
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
              <div className="font-medium">Peça para o técnico desconectar a porta {porta} agora.</div>
              <div className="text-xs text-muted-foreground">
                Escutando desconexões na OLT há {segundos}s. O alarme costuma chegar em alguns segundos.
              </div>
            </div>

            {quedas.length === 0 ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Nenhuma ONT caiu ainda…
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <div className="text-xs text-muted-foreground">
                  ONTs que caíram desde o início. Outras ONTs da OLT podem cair por acaso nesse intervalo - as marcadas como
                  candidatas são da lista desta caixa.
                </div>
                {quedas.map((e) => (
                  <div
                    key={e.id}
                    className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
                  >
                    <ClienteLinha
                      c={e}
                      extra={
                        <>
                          {e.candidato_desta_cto && <Badge variant="success">Candidato desta caixa</Badge>}
                          <span className="text-xs text-muted-foreground">
                            caiu às {new Date(e.ocorrido_em).toLocaleTimeString('pt-BR')}
                          </span>
                        </>
                      }
                    />
                    <Button size="sm" disabled={salvando} onClick={() => escolher(e)}>
                      É este
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {segundos >= SUGERIR_FANTASMA_S && quedas.length === 0 && (
              <div className="flex flex-col gap-2 rounded-md bg-amber-500/10 px-3 py-2 text-amber-700 dark:text-amber-400">
                <span>
                  Nada caiu em {SUGERIR_FANTASMA_S}s. Se o drop está ligado nessa porta, ele não tem ONT ativa do outro lado:
                  porta fantasma, candidata a liberar.
                </span>
                <Button size="sm" variant="outline" className="w-fit" onClick={onSemOntAtiva}>
                  Marcar porta {porta} como fantasma
                </Button>
              </div>
            )}
          </>
        )}

        {fase === 'aguardando_volta' && !voltou && escolhido && (
          <div className="flex flex-col gap-2">
            <div className="rounded-md bg-emerald-500/10 px-3 py-2">
              Porta {porta} = <strong>{escolhido.cliente_nome || escolhido.serial}</strong>. Registrado.
            </div>
            <div className="flex items-center gap-2 font-medium">
              <Loader2 className="size-4 animate-spin" /> Peça para reconectar - aguardando a ONT voltar…
            </div>
            <div className="text-xs text-muted-foreground">
              Não feche antes de confirmar: assim ninguém fica desconectado por engano.
            </div>
          </div>
        )}

        {voltou && escolhido && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 px-3 py-2 font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="size-4" /> {escolhido.cliente_nome || escolhido.serial} voltou. Porta {porta} conferida.
            </div>
            <Button size="sm" className="w-fit" onClick={onClose}>
              Próxima porta
            </Button>
          </div>
        )}

        {erro && <div className="text-xs text-destructive">{erro}</div>}
      </div>
    </Card>
  )
}
