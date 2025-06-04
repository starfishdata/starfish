'use client'

import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import ExploreTemplates from './ExploreTemplates'
import { Suspense } from 'react'
import DashboardClient from './DashboardClient'
import { Loader2 } from 'lucide-react'

export default function DashboardPage() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("explore")

  const fetchProjects = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch('/api/projects/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          
        }),
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.status}`)
      }
      
      const data = await response.json()

      setProjects(data)
    } catch (error) {
      console.error('Error fetching projects:', error)
      setError(error instanceof Error ? error.message : 'Failed to fetch projects')
      setProjects([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleProjectCreated = (newProject: any) => {
    // Add the new project to the list without refetching
    setProjects(prev => [...prev, newProject])
    // Switch to projects tab to show the updated list
    setActiveTab("projects")
  }

  const handleRefresh = () => {
    fetchProjects()
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-500">Loading projects...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button 
          onClick={handleRefresh}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-8">
        <TabsList className="bg-pink-100 h-12">
          <TabsTrigger value="explore" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-8">
            Create Project
          </TabsTrigger>
          <TabsTrigger value="projects" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-8">
            My Projects
          </TabsTrigger>
        </TabsList>

        <TabsContent value="explore">
          <ExploreTemplates onProjectCreated={handleProjectCreated} />
        </TabsContent>

        <TabsContent value="projects">
          <DashboardClient 
            initialProjects={projects} 
            onProjectCreated={handleProjectCreated}
            onRefresh={handleRefresh}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}