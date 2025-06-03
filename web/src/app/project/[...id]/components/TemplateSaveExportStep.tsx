'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Save, Upload, Loader2 } from "lucide-react"
import { useToast } from '@/hooks/use-toast'
import type { DatasetRecord } from './TemplateManager'
import type { TemplateRegister } from '../types'

interface TemplateSaveExportStepProps {
  evaluatedData: DatasetRecord[]
  selectedTemplate: TemplateRegister
  projectId: string
  onBackToStep: (step: string) => void
  onStartNew: () => void
}

export default function TemplateSaveExportStep({
  evaluatedData,
  selectedTemplate,
  projectId,
  onBackToStep,
  onStartNew
}: TemplateSaveExportStepProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [datasetName, setDatasetName] = useState(() => {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const hours = String(now.getHours()).padStart(2, '0')
    const minutes = String(now.getMinutes()).padStart(2, '0')
    const seconds = String(now.getSeconds()).padStart(2, '0')
    return `dataset__${year}-${month}-${day}_${hours}-${minutes}-${seconds}`
  })
  const [huggingFaceRepo, setHuggingFaceRepo] = useState('')
  const { toast } = useToast()

  const handleSaveDataset = async () => {
    setIsSaving(true)
    try {
      const response = await fetch('/api/dataset/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          projectId,
          datasetName,
          data: evaluatedData,
          templateName: selectedTemplate.name
        })
      })

      if (response.ok) {
        toast({
          title: "Dataset saved successfully",
          description: `Dataset "${datasetName}" has been saved to your project.`,
          duration: 3000,
        })
      } else {
        throw new Error('Failed to save dataset')
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save dataset. Please try again.",
        variant: "destructive",
        duration: 5000,
      })
    } finally {
      setIsSaving(false)
    }
  }
  const handleBackToEvaluate = () => {
    onBackToStep("evaluate")
  }
  const handleBackToResults = () => {
    onBackToStep("results")
  }
  const handleExportToHuggingFace = async () => {
    setIsExporting(true)
    try {
      const response = await fetch('/api/datasets/export-hf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repoName: huggingFaceRepo,
          data: evaluatedData,
          datasetName,
          templateName: selectedTemplate.name
        })
      })

      if (response.ok) {
        toast({
          title: "Dataset exported successfully",
          description: `Dataset has been exported to Hugging Face: ${huggingFaceRepo}`,
          duration: 5000,
        })
      } else {
        throw new Error('Failed to export to Hugging Face')
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to export to Hugging Face. Please try again.",
        variant: "destructive",
        duration: 5000,
      })
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Save & Export Dataset</h2>
        <p className="text-gray-600 mt-1">
          Save your evaluated dataset and export to Hugging Face
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Save className="h-5 w-5" />
              Save Dataset
            </CardTitle>
            <CardDescription>
              Save the dataset to your project
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="dataset-name">Dataset Name</Label>
              <Input
                id="dataset-name"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="Enter dataset name"
              />
            </div>
            <div className="text-sm text-gray-600">
              <p>Records: {evaluatedData.length}</p>
              <p>Evaluated: {evaluatedData.filter(r => r.score).length}</p>
              <p>Average Score: {evaluatedData.filter(r => r.score).length > 0 
                ? (evaluatedData.filter(r => r.score).reduce((sum, r) => sum + (r.score || 0), 0) / evaluatedData.filter(r => r.score).length).toFixed(1)
                : 'N/A'}</p>
            </div>
            <Button 
              onClick={handleSaveDataset}
              disabled={isSaving || !datasetName.trim()}
              className="w-full"
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Dataset
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Export to Hugging Face
            </CardTitle>
            <CardDescription>
              Share your dataset on Hugging Face Hub
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="hf-repo">Repository Name</Label>
              <Input
                id="hf-repo"
                value={huggingFaceRepo}
                onChange={(e) => setHuggingFaceRepo(e.target.value)}
                placeholder="username/dataset-name"
              />
            </div>
            <div className="text-sm text-gray-500">
              <p>Format: username/repository-name</p>
              <p>Example: john/my-awesome-dataset</p>
            </div>
            <Button 
              onClick={handleExportToHuggingFace}
              disabled={isExporting || !huggingFaceRepo.trim()}
              className="w-full bg-orange-600 hover:bg-orange-700"
            >
              {isExporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Export to HF
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-between">
        <div className="flex items-center gap-2">
          <Button 
            variant="outline"
            onClick={handleBackToEvaluate}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Evaluate
          </Button>
          <Button 
            variant="outline"
            onClick={handleBackToResults}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Results
          </Button>   
        </div>
        <Button 
          onClick={onStartNew}
          variant="outline"
        >
          Start New Run
        </Button>
      </div>
    </div>
  )
} 