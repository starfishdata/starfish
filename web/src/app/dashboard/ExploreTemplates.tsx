'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Loader2, Plus, ArrowLeft, Check } from "lucide-react"
import { useToast } from '@/hooks/use-toast'
import type { TemplateRegister } from '../project/[...id]/types'

interface ExploreTemplatesProps {
  onProjectCreated?: (project: any) => void
}

type Step = 'select-template' | 'enter-details' | 'creating'

export default function ExploreTemplates({ onProjectCreated }: ExploreTemplatesProps) {
  const [templateData, setTemplateData] = useState<TemplateRegister[]>([])
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [templatesLoaded, setTemplatesLoaded] = useState(false)
  const [currentStep, setCurrentStep] = useState<Step>('select-template')
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateRegister | null>(null)
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const { toast } = useToast()

  // Fetch template data
  useEffect(() => {
    if (templatesLoaded) return
    
    const fetchTemplateData = async () => {
      setIsLoadingTemplates(true)
      try {
        const response = await fetch('/api/template/list')
        if (response.ok) {
          const data = await response.json()
          setTemplateData(data)
          setTemplatesLoaded(true)
        } else {
          console.error('Failed to fetch template data:', response.statusText)
        }
      } catch (error) {
        console.error('Error fetching template data:', error)
      } finally {
        setIsLoadingTemplates(false)
      }
    }

    fetchTemplateData()
  }, [templatesLoaded])

  const handleTemplateSelect = (template: TemplateRegister) => {
    setSelectedTemplate(template)
    // Pre-fill with template-based suggestions
    setProjectName(`${template.name} Project`)
    setProjectDescription(template.description)
    setCurrentStep('enter-details')
  }

  const handleBackToTemplates = () => {
    setCurrentStep('select-template')
    setSelectedTemplate(null)
    setProjectName('')
    setProjectDescription('')
  }

  const handleCreateProject = async () => {
    if (!selectedTemplate || !projectName.trim() || !projectDescription.trim()) {
      toast({
        title: "Error",
        description: "Please fill in both project name and description.",
        variant: "destructive",
        duration: 3000,
      })
      return
    }

    setIsCreatingProject(true)
    setCurrentStep('creating')
    
    try {
      const projectData = {
        project_name: projectName.trim(),
        project_description: projectDescription.trim(),
        template_name: selectedTemplate.name,
        template_description: selectedTemplate.description
      }

      const response = await fetch('/api/projects/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(projectData)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to create project')
      }

      const newProject = await response.json()

      toast({
        title: "Project created successfully!",
        description: `Project "${newProject.name}" has been created using the ${selectedTemplate.name} template.`,
        duration: 5000,
      })

      // Reset to initial state
      setCurrentStep('select-template')
      setSelectedTemplate(null)
      setProjectName('')
      setProjectDescription('')

      // Notify parent component about the new project
      if (onProjectCreated) {
        onProjectCreated(newProject)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error occurred'
      toast({
        title: "Error",
        description: `There was an error creating your project: ${message}`,
        variant: "destructive",
        duration: 5000,
      })
      // Go back to details step on error
      setCurrentStep('enter-details')
    } finally {
      setIsCreatingProject(false)
    }
  }

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-6">
      <div className="flex items-center space-x-4">
        {/* Step 1: Select Template */}
        <div className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
            currentStep === 'select-template' 
              ? 'bg-pink-600 text-white' 
              : selectedTemplate 
                ? 'bg-green-600 text-white' 
                : 'bg-gray-200 text-gray-600'
          }`}>
            {selectedTemplate && currentStep !== 'select-template' ? <Check className="w-4 h-4" /> : '1'}
          </div>
          <span className="ml-2 text-sm font-medium text-gray-700">Select Template</span>
        </div>

        {/* Arrow */}
        <div className="w-8 h-px bg-gray-300"></div>

        {/* Step 2: Enter Details */}
        <div className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
            currentStep === 'enter-details' 
              ? 'bg-pink-600 text-white' 
              : currentStep === 'creating' && projectName && projectDescription
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-600'
          }`}>
            {currentStep === 'creating' && projectName && projectDescription ? <Check className="w-4 h-4" /> : '2'}
          </div>
          <span className="ml-2 text-sm font-medium text-gray-700">Enter Details</span>
        </div>

        {/* Arrow */}
        <div className="w-8 h-px bg-gray-300"></div>

        {/* Step 3: Create Project */}
        <div className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
            currentStep === 'creating' 
              ? 'bg-pink-600 text-white' 
              : 'bg-gray-200 text-gray-600'
          }`}>
            3
          </div>
          <span className="ml-2 text-sm font-medium text-gray-700">Create Project</span>
        </div>
      </div>
    </div>
  )

  const renderTemplateSelection = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-gray-900">Choose a Template</h2>
          <p className="text-sm text-gray-600 mt-1">Select a template to get started with your project</p>
        </div>
        {isLoadingTemplates && (
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-gray-600">Loading templates...</span>
          </div>
        )}
      </div>

      {!isLoadingTemplates && templateData.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No templates available</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {templateData.map((template, index) => (
            <Card 
              key={index} 
              className="cursor-pointer transition-all hover:shadow-lg border-gray-200 hover:border-pink-300"
              onClick={() => handleTemplateSelect(template)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base sm:text-lg">{template.name}</CardTitle>
                  <Badge variant="secondary" className="text-xs">
                    v{template.starfish_version}
                  </Badge>
                </div>
                <CardDescription className="text-sm text-gray-600">
                  by {template.author}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-gray-700 line-clamp-3">
                  {template.description}
                </p>
                
                {template.dependencies.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1">Dependencies:</p>
                    <div className="flex flex-wrap gap-1">
                      {template.dependencies.slice(0, 3).map((dep, depIndex) => (
                        <Badge key={depIndex} variant="outline" className="text-xs">
                          {dep}
                        </Badge>
                      ))}
                      {template.dependencies.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{template.dependencies.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {template.input_example && (
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1">Example Input:</p>
                    <code className="text-xs bg-gray-100 p-2 rounded block overflow-hidden text-ellipsis whitespace-nowrap">
                      {typeof template.input_example === 'object' 
                        ? JSON.stringify(template.input_example) 
                        : template.input_example}
                    </code>
                  </div>
                )}

                <Button className="w-full bg-pink-600 hover:bg-pink-700 focus:ring-pink-500 text-sm">
                  Select Template
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )

  const renderProjectDetails = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button 
          variant="outline" 
          onClick={handleBackToTemplates}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Templates
        </Button>
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-gray-900">Project Details</h2>
          <p className="text-sm text-gray-600 mt-1">Configure your project name and description</p>
        </div>
      </div>

      {/* Selected Template Info */}
      {selectedTemplate && (
        <Card className="border-pink-200 bg-pink-50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-pink-600" />
              <CardTitle className="text-pink-800">Selected Template: {selectedTemplate.name}</CardTitle>
            </div>
            <CardDescription className="text-pink-700">
              {selectedTemplate.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 text-sm text-pink-600">
              <span>by {selectedTemplate.author}</span>
              <span>•</span>
              <span>v{selectedTemplate.starfish_version}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Project Details Form */}
      <Card>
        <CardHeader>
          <CardTitle>Project Information</CardTitle>
          <CardDescription>
            Enter the name and description for your new project
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="project-name">Project Name *</Label>
            <Input
              id="project-name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Enter your project name"
              className="w-full"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-description">Project Description *</Label>
            <Textarea
              id="project-description"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              placeholder="Describe what your project will do"
              className="min-h-[100px] w-full"
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button 
          onClick={handleCreateProject}
          disabled={!projectName.trim() || !projectDescription.trim()}
          className="bg-pink-600 hover:bg-pink-700 text-white flex items-center gap-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          <Plus className="h-4 w-4" />
          Create Project
        </Button>
      </div>
    </div>
  )

  const renderCreatingProject = () => (
    <div className="space-y-6">
      <div className="text-center py-12">
        <div className="flex justify-center mb-4">
          <Loader2 className="h-12 w-12 animate-spin text-pink-600" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Creating Your Project</h2>
        <p className="text-gray-600 mb-4">
          Setting up "{projectName}" with the {selectedTemplate?.name} template...
        </p>
        <div className="bg-gray-50 rounded-lg p-4 max-w-md mx-auto">
          <div className="text-sm text-gray-600 space-y-1">
            <div>✓ Template selected: {selectedTemplate?.name}</div>
            <div>✓ Project details configured</div>
            <div className="flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              Creating project...
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="px-4 sm:px-0">
      <div className="bg-white shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-lg p-4 sm:p-6 mb-6 sm:mb-8 border border-gray-200">
        {renderStepIndicator()}
        
        {currentStep === 'select-template' && renderTemplateSelection()}
        {currentStep === 'enter-details' && renderProjectDetails()}
        {currentStep === 'creating' && renderCreatingProject()}
      </div>
    </div>
  )
} 