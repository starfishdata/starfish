'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, Star, Eye, ChevronLeft, ChevronRight } from "lucide-react"
import { useState, useRef, useCallback, useEffect } from "react"
import type { TemplateResult } from './TemplateManager'

interface TemplateResultsStepProps {
  templateResult: TemplateResult | null
  onEvaluate: (evaluatedData: any[], skipEvaluation: boolean) => void
  onBackToConfigure: () => void
}

export default function TemplateResultsStep({
  templateResult,
  onEvaluate,
  onBackToConfigure
}: TemplateResultsStepProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({})
  const [isResizing, setIsResizing] = useState(false)
  const [resizingColumn, setResizingColumn] = useState<string | null>(null)
  const [ratings, setRatings] = useState<Record<string, number>>({})
  const [comments, setComments] = useState<Record<string, string>>({})
  const tableRef = useRef<HTMLTableElement>(null)
  const recordsPerPage = 10
  
  const totalRecords = templateResult?.data.length || 0
  const totalPages = Math.ceil(totalRecords / recordsPerPage)
  const startIndex = (currentPage - 1) * recordsPerPage
  const endIndex = startIndex + recordsPerPage
  const currentRecords = templateResult?.data.slice(startIndex, endIndex) || []

  const dataColumns = templateResult?.data && templateResult.data.length > 0 
    ? Object.keys(templateResult.data[0]).filter(key => key !== 'id').slice(0, 5)
    : []
  
  const columns = [...dataColumns, 'rating', 'comments']

  // Initialize ratings and comments from existing data
  useEffect(() => {
    if (templateResult?.data) {
      const initialRatings: Record<string, number> = {}
      const initialComments: Record<string, string> = {}
      
      templateResult.data.forEach(record => {
        if (record.rating) initialRatings[record.id] = record.rating
        if (record.comments) initialComments[record.id] = record.comments
      })
      
      setRatings(initialRatings)
      setComments(initialComments)
    }
  }, [templateResult])

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  const handleMouseDown = useCallback((e: React.MouseEvent, columnKey: string) => {
    e.preventDefault()
    setIsResizing(true)
    setResizingColumn(columnKey)
    
    const startX = e.clientX
    const startWidth = columnWidths[columnKey] || (columnKey === 'id' ? 80 : 192) // default widths
    
    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - startX
      const newWidth = Math.max(60, startWidth + diff) // minimum width of 60px
      setColumnWidths(prev => ({
        ...prev,
        [columnKey]: newWidth
      }))
    }
    
    const handleMouseUp = () => {
      setIsResizing(false)
      setResizingColumn(null)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [columnWidths])

  const getColumnWidth = (columnKey: string) => {
    if (columnKey === 'rating') return columnWidths[columnKey] || 120
    if (columnKey === 'comments') return columnWidths[columnKey] || 200
    return columnWidths[columnKey] || 192
  }

  const handleRatingClick = (recordId: string, rating: number) => {
    setRatings(prev => ({
      ...prev,
      [recordId]: rating
    }))
  }

  const handleCommentChange = (recordId: string, comment: string) => {
    setComments(prev => ({
      ...prev,
      [recordId]: comment
    }))
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
            onClick={() => handleRatingClick(recordId, star)}
            onMouseEnter={() => setHoveredRating(star)}
            onMouseLeave={() => setHoveredRating(0)}
          />
        ))}
      </div>
    )
  }

  const handleEvaluate = () => {
    if (!templateResult?.data) return

    // Update existing records with ratings and comments, don't add new columns
    const evaluatedData = templateResult.data.map(record => ({
      ...record,
      rating: ratings[record.id] || record.rating || 0,
      comments: comments[record.id] || record.comments || ''
    }))

    onEvaluate(evaluatedData, false)
  }

  const handleSkipEvaluation = () => {
    onEvaluate([], true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Template Results</h2>
          <p className="text-gray-600 mt-1">
            Generated {templateResult?.data.length} records • 
            Execution time: {templateResult?.metadata?.execution_time}s
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={handleEvaluate}
            className="bg-pink-600 hover:bg-pink-700 text-white flex items-center gap-2"
          >
            Evaluate Results
          </Button>
          <Button 
            onClick={handleSkipEvaluation}
            className="bg-pink-600 hover:bg-pink-700 text-white flex items-center gap-2"
          >
            Skip Evaluation
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Dataset Preview
          </CardTitle>
          <CardDescription>
            Review the generated data before evaluation. Rate each record and add comments.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {templateResult?.data && templateResult.data.length > 0 ? (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <Table ref={tableRef} className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      {columns.map((columnKey) => (
                        <TableHead 
                          key={columnKey} 
                          className="capitalize relative border-r border-gray-200 last:border-r-0"
                          style={{ width: `${getColumnWidth(columnKey)}px` }}
                        >
                          <div className="flex items-center justify-between">
                            <span>
                              {columnKey === 'rating' ? 'Rating' : 
                               columnKey === 'comments' ? 'Comments' : 
                               columnKey.replace(/_/g, ' ')}
                            </span>
                            <div
                              className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 hover:opacity-50 transition-colors"
                              onMouseDown={(e) => handleMouseDown(e, columnKey)}
                              style={{
                                backgroundColor: resizingColumn === columnKey ? '#3b82f6' : 'transparent'
                              }}
                            />
                          </div>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentRecords.map((record) => (
                      <TableRow key={record.id}>
                        {dataColumns.map((columnKey) => (
                          <TableCell 
                            key={columnKey} 
                            className="border-r border-gray-200"
                            style={{ width: `${getColumnWidth(columnKey)}px` }}
                          >
                            <div className="whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                              {typeof record[columnKey] === 'object' 
                                ? JSON.stringify(record[columnKey], null, 2) 
                                : String(record[columnKey] || '')
                              }
                            </div>
                          </TableCell>
                        ))}
                        <TableCell 
                          className="border-r border-gray-200"
                          style={{ width: `${getColumnWidth('rating')}px` }}
                        >
                          <StarRating 
                            recordId={record.id} 
                            currentRating={ratings[record.id] || 0} 
                          />
                        </TableCell>
                        <TableCell 
                          className="last:border-r-0"
                          style={{ width: `${getColumnWidth('comments')}px` }}
                        >
                          <Textarea
                            placeholder="Add comments..."
                            value={comments[record.id] || ''}
                            onChange={(e) => handleCommentChange(record.id, e.target.value)}
                            className="min-h-[60px] resize-none text-sm"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              
              {totalPages > 1 && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-500">
                    Showing {startIndex + 1}-{Math.min(endIndex, totalRecords)} of {totalRecords} records
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
                    <span className="text-sm">
                      Page {currentPage} of {totalPages}
                    </span>
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
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">No data generated</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button 
          variant="outline"
          onClick={onBackToConfigure}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Configure
        </Button>
      </div>
    </div>
  )
} 