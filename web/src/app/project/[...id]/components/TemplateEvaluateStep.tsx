'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, Save, Star, ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"
import type { ToEvaluateDatasetRecord, TemplateResult } from './TemplateManager'

interface TemplateEvaluateStepProps {
  evaluatedData: ToEvaluateDatasetRecord[]
  setEvaluatedData: (data: ToEvaluateDatasetRecord[]) => void
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
  const [currentPage, setCurrentPage] = useState(1)
  const recordsPerPage = 10
  
  const totalRecords = evaluatedData.length
  const totalPages = Math.ceil(totalRecords / recordsPerPage)
  const startIndex = (currentPage - 1) * recordsPerPage
  const endIndex = startIndex + recordsPerPage
  const currentRecords = evaluatedData.slice(startIndex, endIndex)

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  const handleScoreChange = (recordId: string, score: number) => {
    setEvaluatedData(
      evaluatedData.map(record =>
        record.id === recordId ? { ...record, score } : record
      )
    )
  }

  const handleCommentChange = (recordId: string, comments: string) => {
    setEvaluatedData(
      evaluatedData.map(record =>
        record.id === recordId ? { ...record, comments } : record
      )
    )
  }

  const StarRating = ({ recordId, currentRating }: { recordId: string, currentRating: number }) => {
    const [hoveredRating, setHoveredRating] = useState(0)
    
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`h-4 w-4 cursor-pointer transition-colors ${
              star <= (hoveredRating || currentRating)
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-gray-300 hover:text-yellow-400'
            }`}
            onClick={() => handleScoreChange(recordId, star)}
            onMouseEnter={() => setHoveredRating(star)}
            onMouseLeave={() => setHoveredRating(0)}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Evaluate Dataset</h2>
          <p className="text-gray-600 mt-1">
            Add quality scores and comments to each record
            {totalRecords > recordsPerPage && (
              <span> • Showing {startIndex + 1}-{Math.min(endIndex, totalRecords)} of {totalRecords} records</span>
            )}
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
            Rate each record's quality from 1 (poor) to 5 (excellent) and add comments
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6 max-h-96 overflow-y-auto">
            {currentRecords.map((record, index) => (
              <div key={record.id} className="border rounded-lg p-4 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="font-medium mb-2">Record {startIndex + index + 1}</h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      {Object.entries(record).filter(([key]) => 
                      // {.slice(0, 3)}
                        key !== 'id' && key !== 'score' && key !== 'rating' && key !== 'comments'
                      ).map(([key, value]) => (
                        <div key={key}>
                          <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                          <span className="break-words">
                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                
                {/* Scoring and Comments Section */}
                <div className="border-t pt-4 space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <Label className="text-sm font-medium">Rating:</Label>
                      <StarRating 
                        recordId={record.id} 
                        currentRating={record.score || record.rating || 0} 
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Label className="text-sm font-medium">Score:</Label>
                      <Select
                        value={(record.score || record.rating)?.toString() || ''}
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
                  
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Comments:</Label>
                    <Textarea
                      placeholder="Add your evaluation comments here..."
                      value={record.comments || ''}
                      onChange={(e) => handleCommentChange(record.id, e.target.value)}
                      className="min-h-[80px] resize-none text-sm"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <p className="text-sm text-gray-500">
                Page {currentPage} of {totalPages}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
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