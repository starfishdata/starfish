import { Suspense } from 'react'
import DashboardClient from './DashboardClient'
import { getAllProjectsOfUser } from '@/src/_actions/actions'
import { Loader2 } from 'lucide-react'

async function DashboardWrapper() {
  const initialProjects = await getAllProjectsOfUser()
  return <DashboardClient initialProjects={initialProjects} />
}

export default function DashboardPage() {
  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <Suspense fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
              <div className="flex justify-center mb-4">
              <Loader2 className="text-pink-600 h-12 w-12 animate-spin" />
              </div>
              <p className="text-gray-600">Loading Projects...</p>
          </div>
        </div>
        }
      >
      <DashboardWrapper />
      </Suspense>
    </div>
  )
}