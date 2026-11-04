import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'

interface OnuTarget {
  slot: number
  port: number
  position: number
}

/** Mostra o motivo devolvido pela API (ex.: permissão, falha na OLT) em vez de uma mensagem genérica. */
function motivoDoErro(err: unknown): string {
  const data = (err as { response?: { data?: { message?: string; error?: string } } })?.response?.data
  return data?.message ?? data?.error ?? 'Verifique se você tem permissão para operar a OLT.'
}

/** Ações que mexem na OLT de verdade (remover/reiniciar ONU) - usadas nas listagens e no detalhe de porta. */
export function useOnuActions() {
  const queryClient = useQueryClient()
  const toast = useToast()

  function invalidateOnuLists() {
    queryClient.invalidateQueries({
      predicate: (query) => typeof query.queryKey[0] === 'string' && query.queryKey[0].startsWith('/onus'),
    })
  }

  const removeOnu = useMutation({
    mutationFn: ({ slot, port, position }: OnuTarget) => api.delete(`/olt/onus/${slot}/${port}/${position}/`),
    onSuccess: () => {
      toast.success('ONU removida com sucesso')
      invalidateOnuLists()
    },
    onError: (err) => toast.error('Erro ao remover ONU', motivoDoErro(err)),
  })

  const resetOnu = useMutation({
    mutationFn: ({ slot, port, position }: OnuTarget) => api.post(`/olt/onus/${slot}/${port}/${position}/reset/`),
    onSuccess: () => toast.success('ONU reiniciada com sucesso'),
    onError: (err) => toast.error('Erro ao reiniciar ONU', motivoDoErro(err)),
  })

  return { removeOnu, resetOnu }
}
