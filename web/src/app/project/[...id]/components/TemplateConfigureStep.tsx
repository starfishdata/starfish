'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Loader2, Play } from "lucide-react"
import { useToast } from '@/hooks/use-toast'
import type { TemplateRegister } from '../types'
import type { WorkflowStep, TemplateResult, DatasetRecord } from './TemplateManager'

interface TemplateConfigureStepProps {
  selectedTemplate: TemplateRegister
  templateInputs: Record<string, string>
  setTemplateInputs: (inputs: Record<string, string>) => void
  parseTemplateExample: (inputExample: any) => any
  setTemplateResult: (result: TemplateResult | null) => void
  setCurrentStep: (step: WorkflowStep) => void
//   setEvaluatedData: (data: DatasetRecord[]) => void
}

export default function TemplateConfigureStep({
  selectedTemplate,
  templateInputs,
  setTemplateInputs,
  parseTemplateExample,
  setTemplateResult,
  setCurrentStep,
//   setEvaluatedData
}: TemplateConfigureStepProps) {
  const [isRunningTemplate, setIsRunningTemplate] = useState(false)
  const { toast } = useToast()

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

  const handleInputChange = (key: string, value: string) => {
    setTemplateInputs({
      ...templateInputs,
      [key]: value
    })
  }

  const renderInputField = (key: string, value: any) => {
    const inputType = getInputType(value)
    const currentValue = templateInputs[key] || ''

    if (inputType === 'textarea') {
      return (
        <Textarea
          value={currentValue}
          onChange={(e) => handleInputChange(key, e.target.value)}
          placeholder={getDefaultValue(value)}
          className="min-h-[100px] font-mono text-sm"
        />
      )
    }

    if (inputType === 'number') {
      return (
        <Input
          type="number"
          value={currentValue}
          onChange={(e) => handleInputChange(key, e.target.value)}
          placeholder={String(value)}
        />
      )
    }

    if (inputType === 'checkbox') {
      return (
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={currentValue === 'true'}
            onChange={(e) => handleInputChange(key, e.target.checked ? 'true' : 'false')}
            className="rounded border-gray-300"
          />
          <span className="text-sm text-gray-600">
            Default: {String(value)}
          </span>
        </div>
      )
    }

    return (
      <Input
        type="text"
        value={currentValue}
        onChange={(e) => handleInputChange(key, e.target.value)}
        placeholder={String(value)}
      />
    )
  }

  const handleRunTemplate = async () => {
    setIsRunningTemplate(true)
    
    // First transition to running step
    setCurrentStep('running')
    
    try {
      const exampleData = parseTemplateExample(selectedTemplate.input_example)
      const finalInputs: Record<string, any> = {}
      
      if (exampleData) {
        Object.keys(exampleData).forEach(key => {
          const userValue = templateInputs[key]
          if (userValue && userValue.trim()) {
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
        
        // Use actual API response data
        const templateResult: TemplateResult = {
          success: true,
          data: result || [],
          metadata: {
            total_records: result?.length || 0,
            execution_time: result.execution_time || 0,
            template_name: selectedTemplate.name
          }
        }

        setTemplateResult(templateResult)
        // setEvaluatedData(templateResult.data)
        
        toast({
          title: "Template executed successfully",
          description: `Generated ${templateResult.data.length} records`,
          duration: 3000,
        })

        // Transition to results step after execution completes
        setCurrentStep('results')

      } else {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Template execution failed')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'An unknown error occurred'
      toast({
        title: "Template execution failed",
        description: message,
        variant: "destructive",
        duration: 5000,
      })
      // Go back to configure step on error
      setCurrentStep('configure')
    } finally {
      setIsRunningTemplate(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Template: {selectedTemplate.name}</h2>
        <p className="text-gray-600 mt-1">Configure and run your template</p>
      </div>

      <Card className="border-pink-200 bg-pink-50">
        <CardHeader>
          <CardTitle className="text-pink-800">{selectedTemplate.name}</CardTitle>
          <CardDescription>{selectedTemplate.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label className="text-sm font-medium text-pink-700">Author:</Label>
              <p className="text-sm text-pink-600">{selectedTemplate.author}</p>
            </div>
            <div>
              <Label className="text-sm font-medium text-pink-700">Version:</Label>
              <p className="text-sm text-pink-600">v{selectedTemplate.starfish_version}</p>
            </div>
            {selectedTemplate.dependencies && selectedTemplate.dependencies.length > 0 && (
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
          {selectedTemplate.input_example ? (
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
  )
} 