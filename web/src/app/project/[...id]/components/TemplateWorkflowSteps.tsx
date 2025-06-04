'use client'

import { CheckCircle, Circle } from "lucide-react"
import type { WorkflowStep } from './TemplateManager'

interface TemplateWorkflowStepsProps {
  currentStep: WorkflowStep
}

const steps = [
  { id: 'configure', label: 'Configure', description: 'Set template parameters' },
  { id: 'running', label: 'Running', description: 'Execute template' },
  { id: 'results', label: 'Results', description: 'View generated data' },
  { id: 'evaluate', label: 'Evaluate', description: 'Score data quality' },
  { id: 'save-export', label: 'Save & Export', description: 'Publish dataset' },
]

export default function TemplateWorkflowSteps({ currentStep }: TemplateWorkflowStepsProps) {
  const getCurrentStepIndex = () => steps.findIndex(step => step.id === currentStep)
  const currentStepIndex = getCurrentStepIndex()

  return (
    <div className="bg-white border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Template Workflow</h3>
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentStepIndex
          const isCurrent = index === currentStepIndex
          const isUpcoming = index > currentStepIndex

          return (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                  isCompleted 
                    ? 'bg-green-100 border-green-500 text-green-700' 
                    : isCurrent 
                    ? 'bg-pink-100 border-pink-500 text-pink-700' 
                    : 'bg-gray-100 border-gray-300 text-gray-500'
                }`}>
                  {isCompleted ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    <Circle className="h-5 w-5" />
                  )}
                </div>
                <div className="mt-2 text-center">
                  <p className={`text-sm font-medium ${
                    isCurrent ? 'text-pink-700' : isCompleted ? 'text-green-700' : 'text-gray-500'
                  }`}>
                    {step.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{step.description}</p>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div className={`flex-1 h-0.5 mx-4 ${
                  isCompleted ? 'bg-green-500' : 'bg-gray-300'
                }`} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
} 