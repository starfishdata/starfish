'use client'

import Link from 'next/link'
import { ChevronRightIcon, TrashIcon } from 'lucide-react'

export default function ProjectList({ 
  projects, 
  onProjectsChange 
}: { 
  projects: any[]
  onProjectsChange?: () => void 
}) {
  const handleProjectClick = (projectId: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    window.location.href = `/project/${projectId}`
  }

  const handleDeleteProject = (projectId: string, projectName: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (window.confirm(`Are you sure you want to delete "${projectName}"? This action cannot be undone.`)) {
      deleteProject(projectId, projectName)
    }
  }

  const deleteProject = async (projectId: string, projectName: string) => {
    try {
      const response = await fetch(`/api/projects/delete?id=${projectId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to delete project: ${response.statusText}`)
      }

      // Show success message
      alert(`Project "${projectName}" has been deleted successfully.`)
      
      // Trigger refresh of projects list without full page reload
      if (onProjectsChange) {
        onProjectsChange()
      }
      
    } catch (error) {
      console.error('Error deleting project:', error)
      alert(`Failed to delete project "${projectName}". Please try again.`)
    }
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="bg-white shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-lg p-4 sm:p-6 mb-6 sm:mb-8 border border-gray-200">
        <h2 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4 text-gray-900">Your Projects</h2>
        {projects && projects.length > 0 ? (
          <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project: any) => (
              <div key={project.id} className="group relative">
                <Link
                  href={`/project/${project.id}`}
                  className="block"
                  onClick={handleProjectClick(project.id)}
                >
                  <div className="border border-gray-200 rounded-lg p-3 sm:p-4 transition-all duration-200 ease-in-out hover:shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:border-pink-200 bg-white">
                    <h3 className="text-base sm:text-lg font-semibold mb-1 sm:mb-2 text-gray-900 group-hover:text-pink-600">{project.name}</h3>
                    <p className="text-sm sm:text-base text-gray-600 mb-2 sm:mb-4 line-clamp-2">{project.description}</p>
                    <div className="flex items-center text-xs sm:text-sm text-pink-600 font-medium">
                      <span>View Details</span>
                      <ChevronRightIcon className="h-3 w-3 sm:h-4 sm:w-4 ml-1 group-hover:translate-x-1 transition-transform duration-200" />
                    </div>
                  </div>
                </Link>
                <button
                  onClick={handleDeleteProject(project.id, project.name)}
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-white border border-gray-200 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:bg-red-50 hover:border-red-200 hover:text-red-600"
                  title={`Delete ${project.name}`}
                >
                  <TrashIcon className="h-3 w-3 sm:h-4 sm:w-4" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm sm:text-base text-gray-500 text-center py-4">No projects found. Create a new project to get started!</p>
        )}
      </div>
    </div>
  )
}