import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, Loader2, Router } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import type { Onu } from '@/types/api'

interface Resultado {
  onu: Onu | null
  mensagens: string[]
}

type Fonte = 'olt' | 'ixc'

/** Atualiza UMA ONU na hora: relê a PON dela na OLT (+ MAC) ou busca o cliente fibra no IXC. */
export function AtualizarOnuDialog({ onu, onClose }: { onu: Onu | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [resultado, setResultado] = useState<{ fonte: Fonte; mensagens: string[]; erro?: boolean } | null>(null)

  const atualizar = useMutation({
    mutationFn: async (fonte: Fonte) =>
      (await api.post<Resultado>(`/onus/${onu?.id}/atualizar/`, { fonte })).data,
    onSuccess: (r, fonte) => {
      setResultado({ fonte, mensagens: r.mensagens })
      // Recarrega qualquer listagem/contagem de ONUs aberta.
      queryClient.invalidateQueries({
        predicate: (q) => typeof q.queryKey[0] === 'string' && (q.queryKey[0] as string).startsWith('/onus/'),
      })
      queryClient.invalidateQueries({ queryKey: ['onu-stats'] })
      queryClient.invalidateQueries({ queryKey: ['onu-health-summary'] })
    },
    onError: (e: unknown, fonte) => {
      const msg = (e as { response?: { data?: { error?: string } } }).response?.data?.error
      setResultado({ fonte, mensagens: [msg || 'Erro ao atualizar.'], erro: true })
    },
  })

  if (!onu) return null
  const fechar = () => {
    setResultado(null)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={fechar} />
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-lg">
        <h2 className="text-base font-semibold text-foreground">Atualizar esta ONU</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          <span className="font-data">{onu.serial}</span> · {onu.pon}/{onu.position}
          {onu.olt_name ? ` · ${onu.olt_name}` : ''}
        </p>

        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <Button variant="outline" disabled={atualizar.isPending} onClick={() => atualizar.mutate('olt')}>
            {atualizar.isPending && atualizar.variables === 'olt' ? <Loader2 className="animate-spin" /> : <Router />}
            Da OLT
          </Button>
          <Button variant="outline" disabled={atualizar.isPending} onClick={() => atualizar.mutate('ixc')}>
            {atualizar.isPending && atualizar.variables === 'ixc' ? <Loader2 className="animate-spin" /> : <Database />}
            Do IXC
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          OLT: relê a PON da ONU (status, sinal, descrição) e o MAC dela. IXC: busca o cliente fibra com esse serial.
        </p>

        {resultado && (
          <div
            className={
              resultado.erro
                ? 'mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive'
                : 'mt-4 rounded-md bg-secondary px-3 py-2 text-sm'
            }
          >
            <div className="mb-1 text-xs font-medium uppercase text-muted-foreground">
              {resultado.fonte === 'olt' ? 'OLT' : 'IXC'}
            </div>
            <ul className="flex flex-col gap-1">
              {resultado.mensagens.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-5 flex justify-end">
          <Button variant="outline" size="sm" onClick={fechar}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  )
}
