import { OnuListPage } from './OnuListPage'

export function OnusWithoutMacPage() {
  return (
    <OnuListPage
      title="ONUs sem MAC"
      description="ONUs sem endereço MAC cadastrado no sistema."
      endpoint="/onus/sem-mac/"
      emptyMessage="Todas as ONUs têm MAC cadastrado."
    />
  )
}
