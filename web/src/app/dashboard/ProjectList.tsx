'use client'

import Link from 'next/link'
import { ChevronRightIcon } from 'lucide-react'

export default function ProjectList({ projects }: { projects: any[] }) {
  const handleProjectClick = (projectId: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    window.location.href = `/project/${projectId}`
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="bg-white shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-lg p-4 sm:p-6 mb-6 sm:mb-8 border border-gray-200">
        <h2 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4 text-gray-900">Your Projects</h2>
        {projects && projects.length > 0 ? (
          <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project: any) => (
              <Link
                href={`/project/${project.id}`}
                key={project.id}
                className="group"
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
            ))}
          </div>
        ) : (
          <p className="text-sm sm:text-base text-gray-500 text-center py-4">No projects found. Create a new project to get started!</p>
        )}
      </div>
    </div>
  )
}