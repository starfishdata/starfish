'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Eye, Calendar, ChevronDown, ChevronUp } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

interface Dataset {
  id: string
  name: string
  created_at: string
  record_count: number
  status: 'completed' | 'processing' | 'failed'
  data: any[]
}

interface DatasetViewerProps {
  projectId: string
  datasetType: 'factory' | 'template'
}

export default function DatasetViewer({ projectId, datasetType }: DatasetViewerProps) {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)
  const [datasetData, setDatasetData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [viewingData, setViewingData] = useState(false)
  const [isDatasetListOpen, setIsDatasetListOpen] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const recordsPerPage = 2

  useEffect(() => {
    fetchDatasets()
  }, [projectId, datasetType])

  const fetchDatasets = async () => {
    try {
      setLoading(true)
      // Replace with your actual API endpoint
      const response = await fetch(`/api/dataset/list`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          projectId: projectId,
          datasetType: datasetType,
        }),
      })
      const data = await response.json()
      // Ensure data is always an array
      setDatasets(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Error fetching datasets:', error)
      setDatasets([])
    } finally {
      setLoading(false)
    }
  }

  const viewDataset = async (dataset: Dataset) => {
    try {
      setViewingData(true)
      setSelectedDataset(dataset)
      setCurrentPage(1) // Reset to first page when viewing new dataset
      const dataset_data = datasets.find((d) => d.id === dataset.id)?.data
      // Replace with your actual API endpoint
    //   const response = await fetch(`/api/dataset/get`, {
    //     method: 'POST',
    //     headers: {
    //       'Content-Type': 'application/json',
    //     },
    //     body: JSON.stringify({
    //       projectId: projectId,
    //       datasetName: dataset.name,
    //     }),
    //   })
    //   const data = await response.json()
      setDatasetData(dataset_data || [])
    } catch (error) {
      console.error('Error fetching dataset data:', error)
      setDatasetData([])
    } finally {
      setViewingData(false)
    }
  }

  // Pagination calculations
  const totalPages = Math.ceil(datasetData.length / recordsPerPage)
  const startIndex = (currentPage - 1) * recordsPerPage
  const endIndex = startIndex + recordsPerPage
  const currentPageData = datasetData.slice(startIndex, endIndex)

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="text-gray-500">Loading datasets...</div>
      </div>
    )
  }

  if (datasets.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">
          No {datasetType === 'factory' ? 'data factory' : 'data template'} datasets found for this project
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Collapsible Dataset List */}
      <Collapsible open={isDatasetListOpen} onOpenChange={setIsDatasetListOpen}>
        <Card>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-gray-50 transition-colors">
              <div className="flex items-center justify-between">
                <CardTitle>Available Datasets</CardTitle>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">
                    {datasets.length} dataset{datasets.length !== 1 ? 's' : ''}
                  </span>
                  {isDatasetListOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </div>
              </div>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Records</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Array.isArray(datasets) && datasets.map((dataset) => (
                    <TableRow key={dataset.id}>
                      <TableCell className="font-medium">{dataset.name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-gray-400" />
                          {(() => {
                            if (!dataset.created_at) return 'N/A'
                            // Parse yyyy-mm-dd_hh-mm-ss format
                            const [datePart, timePart] = dataset.created_at.split('_')
                            if (!datePart || !timePart) return dataset.created_at
                            const [year, month, day] = datePart.split('-')
                            const [hours, minutes, seconds] = timePart.split('-')
                            const dateStr = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`
                            return new Date(dateStr).toLocaleString()
                          })()}
                        </div>
                      </TableCell>
                      <TableCell>{dataset.record_count.toLocaleString()}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          dataset.status === 'completed' ? 'bg-green-100 text-green-800' :
                          dataset.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {dataset.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => viewDataset(dataset)}
                          disabled={dataset.status !== 'completed'}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      {/* Dataset Data Viewer with Pagination */}
      {selectedDataset && (
        <Card>
          <CardHeader>
            <CardTitle>Dataset: {selectedDataset.name}</CardTitle>
          </CardHeader>
          <CardContent>
            {viewingData ? (
              <div className="flex justify-center items-center py-8">
                <div className="text-gray-500">Loading dataset data...</div>
              </div>
            ) : datasetData.length > 0 ? (
              <div className="space-y-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>id</TableHead>
                        {Object.keys(datasetData[0] || {}).filter(key => key !== 'id').map((key) => (
                          <TableHead key={key}>{key}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {currentPageData.map((record, index) => (
                        <TableRow key={startIndex + index}>
                          <TableCell className="max-w-xs truncate">
                            {typeof record.id === 'object' ? JSON.stringify(record.id) : String(record.id)}
                          </TableCell>
                          {Object.entries(record).filter(([key]) => key !== 'id').map(([key, value], cellIndex) => (
                            <TableCell key={cellIndex} className="max-w-xs truncate">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                
                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-500">
                      Showing {startIndex + 1}-{Math.min(endIndex, datasetData.length)} of {datasetData.length} records
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => goToPage(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </Button>
                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          
                          return (
                            <Button
                              key={pageNum}
                              variant={currentPage === pageNum ? "default" : "outline"}
                              size="sm"
                              onClick={() => goToPage(pageNum)}
                              className="w-8 h-8 p-0"
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => goToPage(currentPage + 1)}
                        disabled={currentPage === totalPages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No data available for this dataset
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
} 