import { useParams } from 'react-router-dom'

import { MaterialsScreen } from './MaterialsScreen'

// Thin route adapter: feed "Apply" lands here with a job id, then the
// unified MaterialsScreen runs the generation pipeline.
export function GeneratePage() {
  const { jobId } = useParams<{ jobId: string }>()
  return <MaterialsScreen mode="generate" jobId={jobId ? Number(jobId) : undefined} />
}
