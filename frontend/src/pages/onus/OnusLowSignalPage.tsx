import { OnuListPage } from './OnuListPage'

export function OnusLowSignalPage() {
  return (
    <OnuListPage
      title="ONUs com Sinal Abaixo de -29 dBm"
      description="ONUs em estado crítico de sinal óptico — risco de perda de conexão."
      endpoint="/onus/"
      filters={{ olt_rx_sig__lt: '-29' }}
      emptyMessage="Nenhuma ONU com sinal abaixo de -29 dBm no momento."
    />
  )
}
