import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Olt, Paginated } from '@/types/api'

/** OLTs ativas cadastradas - usado pra popular os dropdowns de filtro por OLT nas telas. */
export function useOlts() {
  return useQuery({
    queryKey: ['/olts/', { is_active: 'true' }],
    queryFn: async () =>
      (await api.get<Paginated<Olt>>('/olts/', { params: { is_active: true } })).data.results,
    staleTime: 60_000,
  })
}
