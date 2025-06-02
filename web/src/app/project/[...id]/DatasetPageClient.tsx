'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import TemplateManager from './components/TemplateManager'
import DatasetViewer from './components/DatasetViewer'
import type { DatasetPageClientProps } from './types'

export default function DatasetPageClient({ 
  projectId, 
  initialProject
}: DatasetPageClientProps) {
  // Basic state management
  const [dataset] = useState({
    id: projectId,
    name: initialProject.name || '',
    description: initialProject.description || '',
    template_name: initialProject.template_name || '',
  })
  
  // Commented out Data Factory related state for now
  // const [numRecords, setNumRecords] = useState('500')
  // const [selectedModel, setSelectedModel] = useState('gpt-4o-mini-2024-07-18')
  // const [prompt, setPrompt] = useState('')
  // const [generateJobStatus, setGenerateJobStatus] = useState<GenerateJobStatus>('NOT_STARTED')
  // const [isGenerating, setIsGenerating] = useState(false)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">{dataset.name}</h1>
      
      <Tabs defaultValue="generate" className="mb-8">
        <TabsList className="bg-pink-100 h-12">
          <TabsTrigger value="generate" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-16">
            Data Factory
          </TabsTrigger>
          <TabsTrigger value="template" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-16">
            Data Template
          </TabsTrigger>
          <TabsTrigger value="view" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white h-10 px-16">
            View Dataset
          </TabsTrigger>
        </TabsList>

        {/* <TabsContent value="generate">
          <Tabs defaultValue={factories[0].id} className="mb-8">
            <TabsList className="bg-pink-50">
              {factories.map(factory => (
                <TabsTrigger 
                  key={factory.id} 
                  value={factory.id} 
                  className="data-[state=active]:bg-pink-600 data-[state=active]:text-white"
                >
                  {factory.name}
                </TabsTrigger>
              ))}
            </TabsList>

            {factories.map(factory => (
              <TabsContent key={factory.id} value={factory.id}>
                <h2 className="text-2xl font-bold mb-8">{dataset.name} - {dataset.description}</h2>
                <DataFactory
                  projectId={projectId}
                  numRecords={numRecords}
                  setNumRecords={setNumRecords}
                  selectedModel={selectedModel}
                  setSelectedModel={setSelectedModel}
                  prompt={prompt}
                  setPrompt={setPrompt}
                  generateJobStatus={generateJobStatus}
                  setGenerateJobStatus={setGenerateJobStatus}
                  isGenerating={isGenerating}
                  setIsGenerating={setIsGenerating}
                />
              </TabsContent>
            ))}
          </Tabs>
        </TabsContent> */}

        <TabsContent value="template">
          {dataset.template_name ? (
            <TemplateManager projectId={projectId} templateName={dataset.template_name} />
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">No template associated with this project</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="view">
          <Tabs defaultValue="template-datasets" className="mb-8">
            <TabsList className="bg-pink-50">
              <TabsTrigger 
                value="factory-datasets" 
                className="data-[state=active]:bg-pink-600 data-[state=active]:text-white"
              >
                Data Factory Datasets
              </TabsTrigger>
              <TabsTrigger 
                value="template-datasets" 
                className="data-[state=active]:bg-pink-600 data-[state=active]:text-white"
              >
                Data Template Datasets
              </TabsTrigger>
            </TabsList>

            <TabsContent value="factory-datasets">
              <h2 className="text-2xl font-bold mb-6">Data Factory Datasets</h2>
              <DatasetViewer projectId={projectId} datasetType="factory" />
            </TabsContent>

            <TabsContent value="template-datasets">
              <h2 className="text-2xl font-bold mb-6">Data Template Datasets</h2>
              <DatasetViewer projectId={projectId} datasetType="template" />
            </TabsContent>
          </Tabs>
        </TabsContent>
      </Tabs>
    </div>
  )
}