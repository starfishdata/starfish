import { Suspense } from 'react'
import { getProjectById } from '@/src/_actions/actions'
import DatasetPageClient from '@/src/app/project/[...id]/DatasetPageClient'
import { Loader2 } from 'lucide-react'

export default async function DatasetPage({ params }: { params: { id: string } }) {
  const id = params.id[0]

  const project = await getProjectById(id)

  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    }>
      <DatasetPageClient
        projectId={id}
        initialProject={project}
      />
    </Suspense>
  )
}
