import { OnuListPage } from './OnuListPage'

export function OnusSignalWarningPage() {
  return (
    <OnuListPage
      title="ONUs com Sinal entre -27 e -29 dBm"
      description="ONUs em estado de aviso de sinal óptico — vale acompanhar antes que piore."
      endpoint="/onus/"
      filters={{ olt_rx_sig__gte: '-29', olt_rx_sig__lte: '-27' }}
      emptyMessage="Nenhuma ONU com sinal nessa faixa no momento."
    />
  )
}
