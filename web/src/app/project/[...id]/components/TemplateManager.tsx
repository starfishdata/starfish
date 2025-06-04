'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from "lucide-react"
import TemplateWorkflowSteps from './TemplateWorkflowSteps'
import TemplateConfigureStep from './TemplateConfigureStep'
import TemplateRunningStep from './TemplateRunningStep'
import TemplateResultsStep from './TemplateResultsStep'
import TemplateEvaluateStep from './TemplateEvaluateStep'
import TemplateSaveExportStep from './TemplateSaveExportStep'
import type { TemplateRegister } from '../types'

interface TemplateManagerProps {
  projectId: string
  templateName: string
}

export type WorkflowStep = 'configure' | 'running' | 'results' | 'evaluate' | 'save-export'

export interface DatasetRecord {
  id: string
  [key: string]: any
  score?: number
}

export interface ToEvaluateDatasetRecord {
    id: string
    [key: string]: any
    rating?: number
    comments?: string
  }

export interface TemplateResult {
  success: boolean
  data: DatasetRecord[]
  metadata?: {
    total_records: number
    execution_time: number
    template_name: string
  }
}

export default function TemplateManager({ projectId, templateName }: TemplateManagerProps) {
  // Template data state
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateRegister | null>(null)
  const [isLoadingTemplate, setIsLoadingTemplate] = useState(false)
  const [templateLoaded, setTemplateLoaded] = useState(false)

  // Workflow state
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('configure')
  const [templateInputs, setTemplateInputs] = useState<Record<string, string>>({})
  const [templateResult, setTemplateResult] = useState<TemplateResult | null>(null)
  const [evaluatedData, setEvaluatedData] = useState<DatasetRecord[]>([])

  // Fetch specific template data
  useEffect(() => {
    if (templateLoaded || !templateName) return
    
    const fetchTemplateData = async () => {
      setIsLoadingTemplate(true)
      try {
        const response = await fetch('/api/template/list')
        if (response.ok) {
          const data: TemplateRegister[] = await response.json()
          const template = data.find(t => t.name === templateName)
          if (template) {
            setSelectedTemplate(template)
            // Initialize form inputs
            if (template.input_example) {
              const exampleData = parseTemplateExample(template.input_example)
              if (exampleData) {
                const initialInputs: Record<string, string> = {}
                Object.keys(exampleData).forEach(key => {
                  initialInputs[key] = ''
                })
                setTemplateInputs(initialInputs)
              }
            }
          } else {
            console.error(`Template "${templateName}" not found`)
          }
          setTemplateLoaded(true)
        } else {
          console.error('Failed to fetch template data:', response.statusText)
        }
      } catch (error) {
        console.error('Error fetching template data:', error)
      } finally {
        setIsLoadingTemplate(false)
      }
    }

    fetchTemplateData()
  }, [templateLoaded, templateName])

  const parseTemplateExample = (inputExample: any) => {
    try {
      if (typeof inputExample === 'object' && inputExample !== null) {
        return inputExample
      }
      
      if (typeof inputExample === 'string') {
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

  const handleDatasetEvaluation = async (evaluatedData: DatasetRecord[], skipEvaluation: boolean) => {
    try {

        if (skipEvaluation) {
            setCurrentStep('save-export')
            return
        }
      setCurrentStep('running') // Show loading state during API call
      
      // Update templateResult with the evaluated data (ratings and comments)
      if (templateResult) {
        setTemplateResult({
          ...templateResult,
          data: evaluatedData
        })
      }
      
      
      
      const response = await fetch('/api/dataset/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_name: "gpt-4o-mini",
          evaluatedData: evaluatedData
        })
      })

      if (!response.ok) {
        throw new Error('Failed to evaluate dataset')
      }

      const finalEvaluatedData = await response.json()
      //const finalEvaluatedData = result.evaluatedData || evaluatedData
      
      // Update both evaluatedData and templateResult
      setEvaluatedData(finalEvaluatedData)
    //   if (templateResult) {
    //     setTemplateResult({
    //       ...templateResult,
    //       data: finalEvaluatedData
    //     })
    //   }
      
      setCurrentStep('evaluate')
    } catch (error) {
      console.error('Error evaluating dataset:', error)
      // Fallback to using the original evaluated data
      setEvaluatedData(evaluatedData)
      if (templateResult) {
        setTemplateResult({
          ...templateResult,
          data: evaluatedData
        })
      }
      setCurrentStep('evaluate')
      // You might want to show an error message to the user here
    }
  }

  if (isLoadingTemplate) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-2">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="text-lg text-gray-600">Loading template...</span>
          </div>
        </div>
      </div>
    )
  }

  if (!selectedTemplate) {
    return (
      <div className="space-y-6">
        <div className="text-center py-12">
          <p className="text-gray-500">
            {templateName ? `Template "${templateName}" not found` : 'No template associated with this project'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <TemplateWorkflowSteps currentStep={currentStep} />
      
      {currentStep === 'configure' && (

        <TemplateConfigureStep
            selectedTemplate={selectedTemplate}
            templateInputs={templateInputs}
            setTemplateInputs={setTemplateInputs}
            parseTemplateExample={parseTemplateExample}
            setTemplateResult={setTemplateResult}
            setCurrentStep={setCurrentStep}
            // setEvaluatedData={setEvaluatedData}
        />
      )}
      
      {currentStep === 'running' && (
        <TemplateRunningStep selectedTemplate={selectedTemplate} />
      )}
      
      {currentStep === 'results' && (
        <TemplateResultsStep
          templateResult={templateResult}
          onEvaluate={handleDatasetEvaluation}
          onBackToConfigure={() => setCurrentStep('configure')}
        />
      )}
      
      {currentStep === 'evaluate' && (
        <TemplateEvaluateStep
          evaluatedData={evaluatedData}
          setEvaluatedData={setEvaluatedData}
          templateResult={templateResult}
          onSaveExport={() => setCurrentStep('save-export')}
          onBackToResults={() => setCurrentStep('results')}
        />
      )}
      
      {currentStep === 'save-export' && (
        <TemplateSaveExportStep
          evaluatedData={evaluatedData}
          selectedTemplate={selectedTemplate}
          projectId={projectId}
          onBackToStep={(step) => setCurrentStep(step as WorkflowStep)}
          onStartNew={() => {
            setCurrentStep('configure')
            setTemplateResult(null)
            setEvaluatedData([])
          }}
        />
      )}
    </div>
  )
} 