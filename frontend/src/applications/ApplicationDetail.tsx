import { useParams } from 'react-router-dom'

import { MaterialsScreen } from './MaterialsScreen'

// Thin route adapter: opening an application from the dashboard/kanban
// lands here with an application id; the unified MaterialsScreen shows
// the materials, status switcher, and interview prep.
export function ApplicationDetailScreen() {
  const { applicationId } = useParams<{ applicationId: string }>()
  return (
    <MaterialsScreen
      mode="detail"
      applicationId={applicationId ? Number(applicationId) : undefined}
    />
  )
}
