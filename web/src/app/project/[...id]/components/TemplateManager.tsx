'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Loader2, Play, ArrowLeft } from "lucide-react"
import type { TemplateRegister } from '../types'

interface TemplateManagerProps {
  projectId: string
}

export default function TemplateManager({ projectId }: TemplateManagerProps) {
  // Template data state
  const [templateData, setTemplateData] = useState<TemplateRegister[]>([])
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateRegister | null>(null)
  const [templatesLoaded, setTemplatesLoaded] = useState(false)

  // Template execution state
  const [templateInputs, setTemplateInputs] = useState<Record<string, string>>({})
  const [isRunningTemplate, setIsRunningTemplate] = useState(false)
  const [showTemplateForm, setShowTemplateForm] = useState(false)

  // Fetch template data
  useEffect(() => {
    if (templatesLoaded) return // Prevent multiple calls
    
    const fetchTemplateData = async () => {
      setIsLoadingTemplates(true)
      try {
        const response = await fetch('/api/template/list')
        if (response.ok) {
          const data = await response.json()
          setTemplateData(data)
          setTemplatesLoaded(true) // Mark as loaded
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

  const parseTemplateExample = (inputExample: any) => {
    try {
      // If it's already an object, return it directly
      if (typeof inputExample === 'object' && inputExample !== null) {
        return inputExample
      }
      
      // If it's still a string, try to parse it
      if (typeof inputExample === 'string') {
        // Clean up Python syntax to make it valid JSON
        const cleanedExample = inputExample
          .trim()
          .replace(/True/g, 'true')
          .replace(/False/g, 'false')
          .replace(/None/g, 'null')
          .replace(/,(\s*[}\]])/g, '$1')
          .replace(/'/g, '"')
          .replace(/^\s*#.*$/gm, '')
        
        return JSON.parse(cleanedExample)
      }
      
      return null
    } catch (error) {
      console.error('Error parsing template example:', error)
      return null
    }
  }

  const getInputType = (value: any): string => {
    if (typeof value === 'number') return 'number'
    if (typeof value === 'boolean') return 'checkbox'
    if (typeof value === 'object' && value !== null) return 'textarea'
    return 'text'
  }

  const getDefaultValue = (value: any): string => {
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }

  const handleTemplateSelect = (template: TemplateRegister) => {
    setSelectedTemplate(template)
    setShowTemplateForm(true)
    
    // Parse example and initialize form inputs - start with empty inputs
    if (template.input_example) {
      const exampleData = parseTemplateExample(template.input_example)
      if (exampleData) {
        // Initialize with empty values so users can see placeholders
        const initialInputs: Record<string, string> = {}
        Object.keys(exampleData).forEach(key => {
          initialInputs[key] = ''
        })
        setTemplateInputs(initialInputs)
      } else {
        setTemplateInputs({})
      }
    } else {
      setTemplateInputs({})
    }
  }

  const handleInputChange = (key: string, value: string) => {
    setTemplateInputs(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleRunTemplate = async () => {
    if (!selectedTemplate) return
    
    setIsRunningTemplate(true)
    try {
      // Build the final inputs - use user input if provided, otherwise use default values
      const exampleData = parseTemplateExample(selectedTemplate.input_example)
      const finalInputs: Record<string, any> = {}
      
      if (exampleData) {
        Object.keys(exampleData).forEach(key => {
          const userValue = templateInputs[key]
          if (userValue && userValue.trim()) {
            // User provided a value, use it
            const inputType = getInputType(exampleData[key])
            if (inputType === 'number') {
              finalInputs[key] = Number(userValue)
            } else if (inputType === 'checkbox') {
              finalInputs[key] = userValue === 'true'
            } else if (inputType === 'textarea') {
              try {
                finalInputs[key] = JSON.parse(userValue)
              } catch {
                finalInputs[key] = userValue
              }
            } else {
              finalInputs[key] = userValue
            }
          } else {
            // No user input, use default value
            finalInputs[key] = exampleData[key]
          }
        })
      }

      const response = await fetch('/api/template/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          templateName: selectedTemplate.name,
          inputs: finalInputs
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        console.log('Template execution result:', result)
        // Handle success - maybe show a success message or redirect
      } else {
        console.error('Failed to run template:', response.statusText)
      }
    } catch (error) {
      console.error('Error running template:', error)
    } finally {
      setIsRunningTemplate(false)
    }
  }

  const handleBackToTemplates = () => {
    setShowTemplateForm(false)
    setSelectedTemplate(null)
    setTemplateInputs({})
  }

  const renderInputField = (key: string, value: any) => {
    const inputType = getInputType(value)
    const currentValue = templateInputs[key] || ''
    const placeholderValue = getDefaultValue(value)

    switch (inputType) {
      case 'number':
        return (
          <Input
            type="number"
            value={currentValue}
            onChange={(e) => handleInputChange(key, e.target.value)}
            placeholder={placeholderValue}
          />
        )
      
      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={currentValue === 'true'}
              onChange={(e) => handleInputChange(key, e.target.checked ? 'true' : 'false')}
              className="rounded border-gray-300"
            />
            <Label className="text-sm text-gray-500">
              Default: {typeof value === 'boolean' ? String(value) : 'true/false'}
            </Label>
          </div>
        )
      
      case 'textarea':
        return (
          <Textarea
            value={currentValue}
            onChange={(e) => handleInputChange(key, e.target.value)}
            placeholder={placeholderValue}
            className="min-h-[100px] font-mono text-sm"
          />
        )
      
      default:
        return (
          <Input
            type="text"
            value={currentValue}
            onChange={(e) => handleInputChange(key, e.target.value)}
            placeholder={placeholderValue}
          />
        )
    }
  }

  return (
    <div className="space-y-6">
      {!showTemplateForm ? (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Available Templates</h2>
            {isLoadingTemplates && (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-gray-600">Loading templates...</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templateData.map((template, index) => (
              <Card 
                key={index} 
                className="cursor-pointer transition-all hover:shadow-lg border-gray-200 hover:border-pink-300"
                onClick={() => handleTemplateSelect(template)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <Badge variant="secondary" className="text-xs">
                      v{template.starfish_version}
                    </Badge>
                  </div>
                  <CardDescription className="text-sm text-gray-600">
                    by {template.author}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700 mb-4 line-clamp-3">
                    {template.description}
                  </p>
                  
                  {template.dependencies.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-gray-600 mb-1">Dependencies:</p>
                      <div className="flex flex-wrap gap-1">
                        {template.dependencies.map((dep, depIndex) => (
                          <Badge key={depIndex} variant="outline" className="text-xs">
                            {dep}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {template.input_example && (
                    <div>
                      <p className="text-xs font-medium text-gray-600 mb-1">Example:</p>
                      <code className="text-xs bg-gray-100 p-2 rounded block overflow-hidden text-ellipsis whitespace-nowrap">
                        {typeof template.input_example === 'object' 
                          ? JSON.stringify(template.input_example) 
                          : template.input_example}
                      </code>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {!isLoadingTemplates && templateData.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No templates available</p>
            </div>
          )}
        </>
      ) : (
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
            <h2 className="text-2xl font-bold">Configure Template: {selectedTemplate?.name}</h2>
          </div>

          <Card className="border-pink-200 bg-pink-50">
            <CardHeader>
              <CardTitle className="text-pink-800">{selectedTemplate?.name}</CardTitle>
              <CardDescription>{selectedTemplate?.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-pink-700">Author:</Label>
                  <p className="text-sm text-pink-600">{selectedTemplate?.author}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-pink-700">Version:</Label>
                  <p className="text-sm text-pink-600">v{selectedTemplate?.starfish_version}</p>
                </div>
                {selectedTemplate?.dependencies && selectedTemplate.dependencies.length > 0 && (
                  <div>
                    <Label className="text-sm font-medium text-pink-700">Dependencies:</Label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedTemplate.dependencies.map((dep, depIndex) => (
                        <Badge key={depIndex} variant="outline" className="text-xs">
                          {dep}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Template Inputs</CardTitle>
              <CardDescription>
                Fill out the required inputs for this template.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedTemplate?.input_example ? (
                <>
                  {(() => {
                    const exampleData = parseTemplateExample(selectedTemplate.input_example)
                    if (!exampleData) {
                      return (
                        <div className="space-y-4">
                          <div className="space-y-2">
                            <Label className="text-sm font-medium">Input Example:</Label>
                            <div className="bg-gray-100 p-4 rounded-lg border">
                              <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
                                {typeof selectedTemplate.input_example === 'object'
                                  ? JSON.stringify(selectedTemplate.input_example, null, 2)
                                  : selectedTemplate.input_example}
                              </pre>
                            </div>
                          </div>
                          
                          <div className="space-y-4 pt-4 border-t">
                            <Label className="text-sm font-medium">Your Input (JSON format):</Label>
                            <Textarea
                              placeholder="Enter your input data in JSON format..."
                              value={templateInputs.jsonInput || ''}
                              onChange={(e) => handleInputChange('jsonInput', e.target.value)}
                              className="min-h-[200px] font-mono text-sm"
                            />
                          </div>
                        </div>
                      )
                    }

                    return (
                      <div className="space-y-6">
                        <div className="grid grid-cols-1 gap-4">
                          {Object.entries(exampleData).map(([key, value]) => (
                            <div key={key} className="space-y-2">
                              <Label className="text-sm font-medium capitalize">
                                {key.replace(/_/g, ' ')}
                              </Label>
                              <div className="space-y-1">
                                {renderInputField(key, value)}
                                <p className="text-xs text-gray-400">
                                  Default: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="pt-4 border-t">
                          <details className="space-y-2">
                            <summary className="text-sm font-medium cursor-pointer text-gray-600 hover:text-gray-800">
                              View Raw Example
                            </summary>
                            <div className="bg-gray-100 p-4 rounded-lg border">
                              <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
                                {typeof selectedTemplate.input_example === 'object'
                                  ? JSON.stringify(selectedTemplate.input_example, null, 2)
                                  : selectedTemplate.input_example}
                              </pre>
                            </div>
                          </details>
                        </div>
                      </div>
                    )
                  })()}
                </>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500">No input example available for this template</p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button 
              onClick={handleRunTemplate}
              disabled={isRunningTemplate}
              className="bg-pink-600 hover:bg-pink-700 text-white flex items-center gap-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {isRunningTemplate ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running Template...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run Template
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
} 