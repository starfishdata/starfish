import { Suspense } from 'react'
import { fetchAllSeedDataPoints, fetchSeedDataUploadJobStatus, getAllExportJobForProject, getAllFineTuningJobForProject, fetchLatestGenerationJobByProjectId, getProjectById, getDataPointsByProjectIdAndVersion, getAllEvaluationJobForProject, getJobDataForProjectAndVersion } from '@/src/_actions/actions'
import DatasetPageClient from '@/src/app/project/[...id]/DatasetPageClient'
import { Loader2 } from 'lucide-react'

export default async function DatasetPage({ params }: { params: { id: string } }) {
  const id = params.id[0]

  const [
    project,
    fineTuneJobs,
    exportJobs,
    evaluationJobs,
    seedData,
    seedDataJobStatus,
    latestGenerationJobStatus,
  ] = await Promise.all([
    getProjectById(id),
    getAllFineTuningJobForProject(id),
    getAllExportJobForProject(id),
    getAllEvaluationJobForProject(id),
    fetchAllSeedDataPoints(id),
    fetchSeedDataUploadJobStatus(id),
    fetchLatestGenerationJobByProjectId(id)
  ])

  const [
    inputDataset,
    inputGenerationAndEvaluationJobMetadata
  ] = await Promise.all([
    getDataPointsByProjectIdAndVersion(id, project?.latestDatasetVersion),
    getJobDataForProjectAndVersion(id, project?.latestDatasetVersion)
  ]);

  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="text-pink-600 h-12 w-12 animate-spin mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    }>
      <DatasetPageClient 
        projectId={id}
        initialProject={project as any} 
        inputFinetuneJobs={fineTuneJobs || []} 
        inputExportJobs={exportJobs as any || []} 
        inputEvaluationJobs={evaluationJobs as any || []}
        inputSeedData={seedData as any || []} 
        inputDataset={inputDataset as any || []}
        inputSeedDataJobStatus={seedDataJobStatus as any}
        inputLatestGenerationJobStatus={latestGenerationJobStatus as any}
        inputGenerationAndEvaluationJobMetadata={inputGenerationAndEvaluationJobMetadata as any}
      />
    </Suspense>
  )
}
