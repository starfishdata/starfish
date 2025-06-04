// 'use client'

// import { useState } from 'react'
// import { Button } from "@/components/ui/button"
// import { Input } from "@/components/ui/input"
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
// import { Alert, AlertDescription, AlertTitle } from '@/src/components/ui/alert'
// import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
// import { InfoIcon } from 'lucide-react'
// import Editor from '@monaco-editor/react'
// import { generateData } from '@/src/_actions/actions'
// import { schemaExample } from '../constants'
// import type { GenerateJobStatus } from '../types'

// interface DataFactoryProps {
//   projectId: string
//   numRecords: string
//   setNumRecords: (value: string) => void
//   selectedModel: string
//   setSelectedModel: (value: string) => void
//   prompt: string
//   setPrompt: (value: string) => void
//   generateJobStatus: GenerateJobStatus
//   setGenerateJobStatus: (status: GenerateJobStatus) => void
//   isGenerating: boolean
//   setIsGenerating: (value: boolean) => void
//   datasetVersions: string[]
//   setDatasetVersions: (versions: string[]) => void
//   setSelectedVersion: (version: string) => void
//   setDataset: (dataset: any) => void
//   setGenerationAndEvaluationJobMetadata: (metadata: any) => void
// }

// export default function DataFactory({
//   projectId,
//   numRecords,
//   setNumRecords,
//   selectedModel,
//   setSelectedModel,
//   prompt,
//   setPrompt,
//   generateJobStatus,
//   setGenerateJobStatus,
//   isGenerating,
//   setIsGenerating,
//   datasetVersions,
//   setDatasetVersions,
//   setSelectedVersion,
//   setDataset,
//   setGenerationAndEvaluationJobMetadata
// }: DataFactoryProps) {
//   const [numRecordsError, setNumRecordsError] = useState('')
//   const [promptError, setPromptError] = useState('')
//   const [isResuming, setIsResuming] = useState(false)
//   const [isDryRunning, setIsDryRunning] = useState(false)

//   const isFieldsDisabled = generateJobStatus === 'RUNNING'

//   const handleGenerate = async () => {
//     if (parseInt(numRecords) > 500) {
//       setNumRecordsError('Number of records cannot be greater than 500')
//       return
//     }
//     if (!prompt.trim()) {
//       setPromptError('Please enter a prompt for synthetic data generation')
//       return
//     }
//     setNumRecordsError('')
//     setIsGenerating(true)
//     try {
//       setGenerateJobStatus('STARTING')
//       await generateData(projectId, prompt, numRecords, selectedModel);
//       setGenerateJobStatus('RUNNING')
      
//       // add a new version to the page and then select it right after the generate button is clicked
//       let latestVersion = 'V0';
//       if (datasetVersions.length > 0) {
//         latestVersion = datasetVersions[datasetVersions.length - 1];
//         let numericLatestVersion = parseInt(latestVersion?.replace('V', ''), 10)
//         const newVersions = [...datasetVersions, `V${numericLatestVersion + 1}`];
//         setDatasetVersions(newVersions);
//         setSelectedVersion(newVersions[newVersions.length - 1]);
//       }

//       setDataset(prevDataset => ({
//         ...prevDataset,
//         records:[],
//         isLatestVersion: true
//       }))
//       setGenerationAndEvaluationJobMetadata({
//         generationJob: null,
//         evaluationJob: null
//       });

//     } catch (error) {
//       console.error('Error generating data:', error)
//       setGenerateJobStatus('ERROR')
//     }
//   }

//   const handleResume = async () => {
//     setIsResuming(true);
//     try {
//       // Add resume logic here
//     } catch (error) {
//       console.error('Error resuming:', error);
//     } finally {
//       setIsResuming(false);
//     }
//   };

//   const handleDryRun = async () => {
//     setIsDryRunning(true);
//     try {
//       // Add dry run logic here
//     } catch (error) {
//       console.error('Error during dry run:', error);
//     } finally {
//       setIsDryRunning(false);
//     }
//   };

//   return (
//     <div>
//       <div className="flex gap-4 mb-8">
//         <Button 
//           onClick={handleGenerate} 
//           disabled={isGenerating}
//           className="bg-pink-600 hover:bg-pink-700 text-white"
//         >
//           {isGenerating ? 'Generating...' : 'Run'}
//         </Button>
//         <Button 
//           onClick={handleResume} 
//           disabled={isResuming}
//           className="bg-pink-600 hover:bg-pink-700 text-white"
//         >
//           {isResuming ? 'Resuming...' : 'Resume'}
//         </Button>
//         <Button 
//           onClick={handleDryRun} 
//           disabled={isDryRunning}
//           className="bg-pink-600 hover:bg-pink-700 text-white"
//         >
//           {isDryRunning ? 'Running...' : 'Dry Run'}
//         </Button>
//       </div>

//       <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
//         {/* Generate Dataset Card */}
//         <Card>
//           <CardHeader>
//             <CardTitle>Data Factory Configuration</CardTitle>
//           </CardHeader>
//           <CardContent>
//             <div className="grid grid-cols-2 gap-4 mb-4">
//               <div>
//                 <label htmlFor="numRecords" className="block text-sm font-medium text-gray-700 mb-2">
//                   Max Concurrency
//                 </label>
//                 <Input
//                   type="number"
//                   id="numRecords"
//                   value={numRecords}
//                   onChange={(e) => setNumRecords(e.target.value)}
//                   min="1"
//                   max="500"
//                   className="w-full"
//                   disabled={isFieldsDisabled}
//                 />
//                 {numRecordsError && (
//                   <p className="text-red-500 text-sm mt-1">{numRecordsError}</p>
//                 )}
//               </div>
//               <div>
//                 <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-2">
//                   Model
//                 </label>
//                 <Select 
//                   value={selectedModel} 
//                   onValueChange={setSelectedModel}
//                   disabled={isFieldsDisabled}
//                 >
//                   <SelectTrigger className="w-full">
//                     <SelectValue placeholder="Select a model" />
//                   </SelectTrigger>
//                   <SelectContent>
//                     {[
//                       { value: 'gpt-4o-mini-2024-07-18' },
//                       { value: 'gpt-4o-2024-08-06'},
//                       { value: 'gpt-4-turbo-2024-04-09' },
//                     ].map((model) => (
//                       <SelectItem key={model.value} value={model.value}>
//                         {model.value}
//                       </SelectItem>
//                     ))}
//                   </SelectContent>
//                 </Select>
//               </div>
//             </div>

//             <div className="mb-4">
//               <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
//                 Prompt for synthetic data generation
//               </label>
//               <div className="relative">
//                 <textarea
//                   id="prompt"
//                   value={prompt}
//                   onChange={(e) => {
//                     setPrompt(e.target.value)
//                     setPromptError('')
//                   }}
//                   className={`w-full p-2 border ${promptError ? 'border-red-500' : 'border-gray-300'} rounded-md`}
//                   rows={3}
//                   placeholder="Enter your prompt here..."
//                   disabled={isFieldsDisabled}
//                 />
//                 <div className="absolute right-2 top-2">
//                   <TooltipProvider>
//                     <Tooltip>
//                       <TooltipTrigger>
//                         <InfoIcon className="h-5 w-5 text-gray-400" />
//                       </TooltipTrigger>
//                       <TooltipContent>
//                         <p>Enter a prompt to guide the synthetic data generation process.</p>
//                       </TooltipContent>
//                     </Tooltip>
//                   </TooltipProvider>
//                 </div>
//               </div>
//               {promptError && (
//                 <Alert variant="destructive" className="mt-2">
//                   <AlertTitle>Error</AlertTitle>
//                   <AlertDescription>{promptError}</AlertDescription>
//                 </Alert>
//               )}
//             </div>

//             <div className="mb-4">
//               <div className="flex items-center mb-2">
//                 <label htmlFor="schema" className="block text-sm font-medium text-gray-700 mr-2">
//                   Generated Data Schema
//                 </label>
//                 <TooltipProvider>
//                   <Tooltip>
//                     <TooltipTrigger>
//                       <InfoIcon className="h-4 w-4 text-gray-400" />
//                     </TooltipTrigger>
//                     <TooltipContent>
//                       <p>The generated data will only be in question and answer format for now.</p>
//                     </TooltipContent>
//                   </Tooltip>
//                 </TooltipProvider>
//               </div>
//               <pre className="bg-gray-100 p-2 rounded-md text-sm overflow-x-auto">
//                 {schemaExample}
//               </pre>
//             </div>
//           </CardContent>
//         </Card>

//         {/* Python Functions Card */}
//         <Card>
//           <CardHeader>
//             <CardTitle>Python Functions</CardTitle>
//           </CardHeader>
//           <CardContent>
//             <div className="space-y-4">
//               <div className="h-[400px]">
//                 <Editor
//                   height="100%"
//                   defaultLanguage="python"
//                   defaultValue={`def process_data(data):\n    # Your code here\n    return processed_data`}
//                   theme="vs-dark"
//                   options={{
//                     minimap: { enabled: false },
//                     fontSize: 14,
//                     scrollBeyondLastLine: false,
//                     automaticLayout: true,
//                     padding: { top: 10 },
//                   }}
//                 />
//               </div>
//               <div className="flex justify-end">
//                 <Button className="bg-pink-600 hover:bg-pink-700 text-white">
//                   Save Function
//                 </Button>
//               </div>
//             </div>
//           </CardContent>
//         </Card>
//       </div>
//     </div>
//   )
// } 