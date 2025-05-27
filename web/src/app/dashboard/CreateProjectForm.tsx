'use client'

import { useState } from 'react'
import { PlusIcon, Loader2 } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from '@/hooks/use-toast'
import { createProject } from '@/src/_actions/actions'

export default function CreateProjectForm({ onProjectCreated }: any) {
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const formData = new FormData()
      formData.append('project_name', newProjectName)
      formData.append('project_description', newProjectDescription)

      const newProject: any = await createProject(formData)

      toast({
        title: "Project created",
        description: "Your new project has been successfully created.",
        duration: 5000,
      })

      // Reset form
      setNewProjectName('')
      setNewProjectDescription('')

      // Notify parent component about the new project
      onProjectCreated(newProject)
    } catch (error) {
      toast({
        title: "Error",
        description: "There was an error creating your project. Please try again.",
        variant: "destructive",
        duration: 5000,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="bg-white shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-lg p-4 sm:p-6 mb-6 sm:mb-8 border border-gray-200">
        <h2 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4 text-gray-900">Create New Project</h2>
        <form onSubmit={handleCreateProject} className="space-y-3 sm:space-y-4">
          <div>
            <label htmlFor="projectName" className="block text-sm font-medium text-gray-700 mb-1 sm:mb-2">
              Project Name
            </label>
            <Input
              type="text"
              id="projectName"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              required
              className="w-full text-sm sm:text-base"
              placeholder="Enter project name"
            />
          </div>
          <div>
            <label htmlFor="projectDescription" className="block text-sm font-medium text-gray-700 mb-1 sm:mb-2">
              Description
            </label>
            <Textarea
              id="projectDescription"
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
              required
              className="w-full text-sm sm:text-base"
              rows={3}
              placeholder="Enter project description"
            />
          </div>
          <Button 
            type="submit" 
            disabled={isLoading}
            className="w-full sm:w-auto bg-pink-600 hover:bg-pink-700 focus:ring-pink-500 text-sm sm:text-base"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <PlusIcon className="mr-2 h-4 w-4" />
                Create Project
              </>
            )}
          </Button>
        </form>
      </div>
    </div>
  )
}