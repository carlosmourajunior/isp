import { OnuListPage } from './OnuListPage'

export function DuplicatedOnusPage() {
  return (
    <OnuListPage
      title="ONUs Duplicadas"
      description="ONUs com número serial duplicado — normalmente indica reconexão ou erro de provisionamento."
      endpoint="/onus/duplicated/"
      emptyMessage="Nenhuma ONU duplicada encontrada."
    />
  )
}
