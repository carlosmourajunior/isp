import { OnuListPage } from './OnuListPage'

export function MacAddressesPage() {
  return (
    <OnuListPage
      title="MAC Addresses"
      description="Todos os endereços MAC cadastrados no sistema."
      endpoint="/onus/mac-addresses/"
    />
  )
}
