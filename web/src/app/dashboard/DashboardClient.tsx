'use client'

import { useState } from 'react'
//import CreateProjectForm from './CreateProjectForm'
import ProjectList from './ProjectList'

export default function DashboardClient({ initialProjects }: any) {
  const [projects, setProjects] = useState(initialProjects)

  // const handleProjectCreated = (newProject: any) => {
  //   setProjects((prevProjects: any) => [newProject, ...prevProjects]);
  // }

  const handleProjectsChange = async () => {
    try {
      const response = await fetch('/api/projects/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      })
      
      if (response.ok) {
        const updatedProjects = await response.json()
        setProjects(updatedProjects)
      } else {
        console.error('Failed to fetch updated projects')
      }
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* <CreateProjectForm onProjectCreated={handleProjectCreated} /> */}
      <ProjectList 
        projects={projects} 
        onProjectsChange={handleProjectsChange}
      />
    </div>
  )
}