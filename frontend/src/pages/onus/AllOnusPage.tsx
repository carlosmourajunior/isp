import { OnuListPage } from './OnuListPage'

export function AllOnusPage() {
  return (
    <OnuListPage
      title="Todas as ONUs"
      description="Lista completa de ONUs cadastradas."
      endpoint="/onus/"
      showQuickFilters
    />
  )
}
