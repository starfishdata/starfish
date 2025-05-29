'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowLeft, Save, Star } from "lucide-react"
import type { DatasetRecord, TemplateResult } from './TemplateManager'

interface TemplateEvaluateStepProps {
  evaluatedData: DatasetRecord[]
  setEvaluatedData: (data: DatasetRecord[]) => void
  templateResult: TemplateResult | null
  onSaveExport: () => void
  onBackToResults: () => void
}

export default function TemplateEvaluateStep({
  evaluatedData,
  setEvaluatedData,
  templateResult,
  onSaveExport,
  onBackToResults
}: TemplateEvaluateStepProps) {
  const handleScoreChange = (recordId: string, score: number) => {
    setEvaluatedData(
      evaluatedData.map(record =>
        record.id === recordId ? { ...record, score } : record
      )
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Evaluate Dataset</h2>
          <p className="text-gray-600 mt-1">
            Add quality scores to each record (1-5 scale)
          </p>
        </div>
        <Button 
          onClick={onSaveExport}
          className="bg-pink-600 hover:bg-pink-700 text-white flex items-center gap-2"
        >
          <Save className="h-4 w-4" />
          Save & Export
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-5 w-5" />
            Quality Evaluation
          </CardTitle>
          <CardDescription>
            Rate each record's quality from 1 (poor) to 5 (excellent)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {evaluatedData.map((record, index) => (
              <div key={record.id} className="border rounded-lg p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="font-medium mb-2">Record {index + 1}</h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      {Object.entries(record).filter(([key]) => key !== 'id' && key !== 'score').slice(0, 3).map(([key, value]) => (
                        <div key={key}>
                          <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                          <span className="truncate">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Label className="text-sm">Score:</Label>
                    <Select
                      value={record.score?.toString() || ''}
                      onValueChange={(value) => handleScoreChange(record.id, parseInt(value))}
                    >
                      <SelectTrigger className="w-20">
                        <SelectValue placeholder="Rate" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1</SelectItem>
                        <SelectItem value="2">2</SelectItem>
                        <SelectItem value="3">3</SelectItem>
                        <SelectItem value="4">4</SelectItem>
                        <SelectItem value="5">5</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button 
          variant="outline"
          onClick={onBackToResults}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Results
        </Button>
      </div>
    </div>
  )
} 