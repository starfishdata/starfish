'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ArrowLeft, Star, Eye } from "lucide-react"
import type { TemplateResult } from './TemplateManager'

interface TemplateResultsStepProps {
  templateResult: TemplateResult | null
  onEvaluate: () => void
  onBackToConfigure: () => void
}

export default function TemplateResultsStep({
  templateResult,
  onEvaluate,
  onBackToConfigure
}: TemplateResultsStepProps) {
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
        <Button 
          onClick={onEvaluate}
          className="bg-pink-600 hover:bg-pink-700 text-white flex items-center gap-2"
        >
          <Star className="h-4 w-4" />
          Evaluate Results
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Dataset Preview
          </CardTitle>
          <CardDescription>
            Review the generated data before evaluation
          </CardDescription>
        </CardHeader>
        <CardContent>
          {templateResult?.data && templateResult.data.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    {Object.keys(templateResult.data[0]).filter(key => key !== 'id').slice(0, 5).map(key => (
                      <TableHead key={key} className="capitalize">
                        {key.replace(/_/g, ' ')}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {templateResult.data.slice(0, 10).map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="font-medium">{record.id}</TableCell>
                      {Object.entries(record).filter(([key]) => key !== 'id').slice(0, 5).map(([key, value]) => (
                        <TableCell key={key} className="max-w-xs truncate">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {templateResult.data.length > 10 && (
                <p className="text-sm text-gray-500 mt-2 text-center">
                  Showing 10 of {templateResult.data.length} records
                </p>
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