'use client'

import { useEffect, useState } from 'react'
import DatasetPageClient from '@/src/app/project/[...id]/DatasetPageClient'
import { Loader2 } from 'lucide-react'

export default function DatasetPage({ params }: { params: { id: string } }) {
  const id = params.id[0]
  const [project, setProject] = useState({
    name: '',
    description: '',
    template_name: ''
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchProject = async () => {
      try {
        setLoading(true)
        const response = await fetch(`/api/projects/get?id=${id}`)
        
        if (!response.ok) {
          throw new Error('Failed to fetch project')
        }
        
        const projectData = await response.json()
        setProject(projectData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred')
      } finally {
        setLoading(false)
      }
    }

    fetchProject()
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  return (
    <DatasetPageClient
      projectId={id}
      initialProject={project}
    />
  )
}
