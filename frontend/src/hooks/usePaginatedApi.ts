import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'

interface UsePaginatedApiOptions {
  endpoint: string
  page: number
  search?: string
  ordering?: string
  filters?: Record<string, string | undefined>
  enabled?: boolean
}

/** Data fetching padrão para as listagens paginadas (formato DRF PageNumberPagination). */
export function usePaginatedApi<T>({
  endpoint,
  page,
  search,
  ordering,
  filters,
  enabled = true,
}: UsePaginatedApiOptions) {
  const params: Record<string, string | number> = { page }
  if (search) params.search = search
  if (ordering) params.ordering = ordering
  if (filters) {
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') params[key] = value
    }
  }

  return useQuery({
    queryKey: [endpoint, params],
    queryFn: async () => (await api.get<Paginated<T>>(endpoint, { params })).data,
    placeholderData: keepPreviousData,
    enabled,
  })
}
