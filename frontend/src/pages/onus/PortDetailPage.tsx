import { useParams } from 'react-router-dom'
import { OnuListPage } from './OnuListPage'

export function PortDetailPage() {
  const { slot, port } = useParams<{ slot: string; port: string }>()
  const pon = `1/1/${slot}/${port}`

  return (
    <OnuListPage
      title={`Detalhes da Porta ${pon}`}
      description="ONUs conectadas nesta porta."
      endpoint="/onus/"
      filters={{ pon }}
      emptyMessage="Nenhuma ONU encontrada nesta porta."
    />
  )
}
