import { OnuListPage } from './OnuListPage'

export function OnusOfflinePage() {
  return (
    <OnuListPage
      title="ONUs com Oper. State Down"
      description="ONUs administrativamente ligadas mas operacionalmente offline."
      endpoint="/onus/"
      filters={{ oper_state: 'down' }}
      emptyMessage="Nenhuma ONU offline no momento."
    />
  )
}
