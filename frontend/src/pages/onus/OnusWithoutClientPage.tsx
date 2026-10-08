import { OnuListPage } from './OnuListPage'

export function OnusWithoutClientPage() {
  return (
    <OnuListPage
      title="ONUs sem Cliente Fibra"
      description="ONUs sem vínculo com um cliente fibra no IXC."
      endpoint="/onus/"
      filters={{ cliente_fibra: 'false' }}
      emptyMessage="Todas as ONUs têm cliente fibra vinculado."
    />
  )
}
