'use client'

import { useState } from 'react'
//import CreateProjectForm from './CreateProjectForm'
import ProjectList from './ProjectList'

export default function DashboardClient({ initialProjects }: any) {
  const [projects, setProjects] = useState(initialProjects)

  // const handleProjectCreated = (newProject: any) => {
  //   setProjects((prevProjects: any) => [newProject, ...prevProjects]);
  // }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* <CreateProjectForm onProjectCreated={handleProjectCreated} /> */}
      <ProjectList projects={projects} />
    </div>
  )
}