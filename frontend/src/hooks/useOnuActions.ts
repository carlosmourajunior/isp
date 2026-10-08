import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'

interface OnuTarget {
  slot: number
  port: number
  position: number
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
    onError: () => toast.error('Erro ao remover ONU', 'Verifique se você tem permissão de administrador.'),
  })

  const resetOnu = useMutation({
    mutationFn: ({ slot, port, position }: OnuTarget) => api.post(`/olt/onus/${slot}/${port}/${position}/reset/`),
    onSuccess: () => toast.success('ONU reiniciada com sucesso'),
    onError: () => toast.error('Erro ao reiniciar ONU', 'Verifique se você tem permissão de administrador.'),
  })

  return { removeOnu, resetOnu }
}
