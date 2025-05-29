'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import CreateProjectForm from './CreateProjectForm'
import ExploreTemplates from './ExploreTemplates'
import { Suspense } from 'react'
import DashboardClient from './DashboardClient'
import { getAllProjectsOfUser } from '@/src/_actions/actions'
import { Loader2 } from 'lucide-react'

async function DashboardWrapper() {
  const initialProjects = await getAllProjectsOfUser()
  return <DashboardClient initialProjects={initialProjects} />
}

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0)

  const handleProjectCreated = (newProject: any) => {
    // Refresh the project list or handle the new project
    setRefreshKey(prev => prev + 1)
    console.log('New project created:', newProject)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
      
      <Tabs defaultValue="create" className="mb-8">
        <TabsList className="bg-pink-100 h-12">
          {/* <TabsTrigger value="create" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-8">
            Create Project
          </TabsTrigger> */}
          <TabsTrigger value="explore" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-8">
            Explore Templates
          </TabsTrigger>
        </TabsList>

        {/* <TabsContent value="create">
          <CreateProjectForm onProjectCreated={handleProjectCreated} />
        </TabsContent> */}

        <TabsContent value="explore">
          <ExploreTemplates onProjectCreated={handleProjectCreated} />
        </TabsContent>
      </Tabs>

      {/* Your existing project list component would go here */}
      <div key={refreshKey}>
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
    </div>
  )
}