'use client'

import { Loader2 } from "lucide-react"
import type { TemplateRegister } from '../types'

interface TemplateRunningStepProps {
  selectedTemplate: TemplateRegister
}

export default function TemplateRunningStep({ selectedTemplate }: TemplateRunningStepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center py-12">
        <div className="flex justify-center mb-4">
          <Loader2 className="h-12 w-12 animate-spin text-pink-600" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Running Template</h2>
        <p className="text-gray-600 mb-4">
          Executing "{selectedTemplate.name}" with your configured parameters...
        </p>
        <div className="bg-gray-50 rounded-lg p-4 max-w-md mx-auto">
          <div className="text-sm text-gray-600 space-y-1">
            <div>✓ Template loaded: {selectedTemplate.name}</div>
            <div>✓ Parameters configured</div>
            <div className="flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              Generating dataset...
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 