'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Loader2, InfoIcon, ThumbsUp, ThumbsDown, ChevronLeft, ChevronRight, ExternalLink, ChevronDown, Download, Upload, CheckCircle2 } from 'lucide-react'
import { generateData, getAllFineTuningJobForProject, createFineTuneRun, checkJobEvents, generateJsonlData, uploadToHuggingFace, getAllExportJobForProject, startSeedDataRun, updateSeedDataRunStatus, fetchAllSeedDataPoints, fetchSeedDataUploadJobStatus, getDataPointsByProjectIdAndVersion, likeDataPoint, createEvaluationJob, getJobDataForProjectAndVersion, getAllEvaluationJobForProject } from '@/src/_actions/actions'
import { Alert, AlertDescription, AlertTitle } from '@/src/components/ui/alert'
import { uploadData } from 'aws-amplify/storage'
import { Checkbox } from '@/src/components/ui/checkbox'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'

const openAIModels = [
  { value: 'gpt-4o-2024-08-06' },
  { value: 'gpt-4o-mini-2024-07-18' },
  { value: 'gpt-4-0613' },
  { value: 'gpt-3.5-turbo-0125' },
  { value: 'gpt-3.5-turbo-1106' },
  { value: 'gpt-3.5-turbo-0613' },
]

type Job = {
  id: any;
  type: any;
  model: any;
  status: any;
  events: any;
  result?: any;
  finetunedModel: any;
}

type ExportJob = {
  id: string;
  type: string;
  events: {
    data: Array<{
      created_at: string;
      message: string;
    }>;
  };
  status: string;
  datasetUrl: string;
}
type GenerateJobStatus = 'RUNNING' | 'COMPLETE' | 'NOT_STARTED' | 'COMPLETE_WITH_ERROR' | 'ERROR' | 'STARTING';

type DatasetPageClientProps = {
  projectId: string;
  initialProject: {
    name: string | null | undefined;
    description: string | null | undefined;
    latestSeedFile: string | null | undefined;
    latestDatasetVersion: number | null | undefined;
  };
  inputFinetuneJobs: Job[];
  inputExportJobs: ExportJob[];
  inputEvaluationJobs: EvaluationJob[];
  inputSeedData: SeedDataPoint[];
  inputDataset: any[];
  inputSeedDataJobStatus: string;
  inputLatestGenerationJobStatus: {
    jobId: any;
    status: 'RUNNING' | 'COMPLETE' | 'NOT_STARTED' | 'COMPLETE_WITH_ERROR' | 'ERROR';
    numberOfRecords: any;
    model: any;
    prompt: any;
  },
  inputGenerationAndEvaluationJobMetadata: {
    generationJob: {
      jobId: string,
      status: 'RUNNING' | 'COMPLETE' | 'NOT_STARTED' | 'COMPLETE_WITH_ERROR' | 'ERROR';
    } | null,
    evaluationJob: {
      jobId: string,
      status: 'RUNNING' | 'COMPLETE' | 'NOT_STARTED' | 'COMPLETE_WITH_ERROR' | 'ERROR',
      averageQualityScore: number;
    } | null
  };
}

type SeedDataPoint = {
  id: string;
  type: string;
  data: string;
}

type EvaluationJob = {
  id: string;
  status: 'RUNNING' | 'COMPLETE' | 'FAILED';
  version: number;
  overallScore: number | null;
}


export default function DatasetPageClient({ projectId, initialProject, inputFinetuneJobs, inputExportJobs, inputEvaluationJobs, inputSeedData, inputDataset, inputSeedDataJobStatus, inputLatestGenerationJobStatus, inputGenerationAndEvaluationJobMetadata }: DatasetPageClientProps) {
  const [dataset, setDataset] = useState({
    id: projectId,
    name: initialProject.name,
    description: initialProject.description,
    records: [] as any[],
    isLatestVersion: true,
  })
  const [numRecords, setNumRecords] = useState(inputLatestGenerationJobStatus?.numberOfRecords || '500')
  const [numRecordsError, setNumRecordsError] = useState('')
  const [selectedModel, setSelectedModel] = useState(inputLatestGenerationJobStatus?.model || 'gpt-4o-mini-2024-07-18')
  const [isGenerating, setIsGenerating] = useState(inputLatestGenerationJobStatus?.status === 'RUNNING')
  const [currentPage, setCurrentPage] = useState(1)
  const [recordsPerPage, setRecordsPerPage] = useState(20)
  const [prompt, setPrompt] = useState(inputLatestGenerationJobStatus?.prompt || '')
  const [generateJobStatus, setGenerateJobStatus] = useState<GenerateJobStatus>(inputLatestGenerationJobStatus?.status || 'NOT_STARTED')
  const [fineTuneJobs, setFineTuneJobs] = useState<Job[]>(inputFinetuneJobs)
  const [openAIKey, setOpenAIKey] = useState('')
  const [openAIModel, setOpenAIModel] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalError, setModalError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [exportJobs, setExportJobs] = useState<ExportJob[]>(inputExportJobs)
  const [isExportModalOpen, setIsExportModalOpen] = useState(false)
  const [exportPlatform, setExportPlatform] = useState('huggingface')
  const [exportApiKey, setExportApiKey] = useState('')
  const [exportModalError, setExportModalError] = useState('')
  const [isExportSubmitting, setIsExportSubmitting] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  
  const [seedFile, setSeedFile] = useState<File | null>(null)
  const [seedDataPoints, setSeedDataPoints] = useState<SeedDataPoint[]>(inputSeedData)
  const [isGeneratingSeedData, setIsGeneratingSeedData] = useState(false)
  const [latestSeedFile, setLatestSeedFile] = useState<string | null | undefined>(initialProject?.latestSeedFile)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [useSeedData, setUseSeedData] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [currentSeedDataPage, setCurrentSeedDataPage] = useState(1)
  const seedDataPerPage = 10
  const [seedDataJobStatus, setSeedDataJobStatus] = useState<string | null>(inputSeedDataJobStatus);
  const [activeTab, setActiveTab] = useState<'dataset' | 'seeddata'>('dataset')
  const [datasetVersions, setDatasetVersions] = useState<string[]>([])
  const [selectedVersion, setSelectedVersion] = useState<string>('')
  const [isLoadingDataset, setIsLoadingDataset] = useState(false)

  const [selectedFineTuneVersion, setSelectedFineTuneVersion] = useState<string>('')
  const [selectedExportVersion, setSelectedExportVersion] = useState<string>('')

  const isFieldsDisabled = generateJobStatus === 'RUNNING'

  const [evaluationJobs, setEvaluationJobs] = useState<EvaluationJob[]>(inputEvaluationJobs)
  const [selectedEvaluationVersion, setSelectedEvaluationVersion] = useState<string>('')
  const [isEvaluationModalOpen, setIsEvaluationModalOpen] = useState(false)
  const [isEvaluationSubmitting, setIsEvaluationSubmitting] = useState(false)
  const [evaluationModalError, setEvaluationModalError] = useState('')
  const [generationAndEvaluationJobMetadata, setGenerationAndEvaluationJobMetadata] = useState(inputGenerationAndEvaluationJobMetadata)
  const [isPollingEvaluationJobs, setIsPollingEvaluationJobs] = useState(false)
  const [promptError, setPromptError] = useState('')

  const [filterFineTuneDownvoted, setFilterFineTuneDownvoted] = useState(false)
  const [filterFineTuneScore, setFilterFineTuneScore] = useState('')

  const [filterExportDownvoted, setFilterExportDownvoted] = useState(false)
  const [filterExportScore, setFilterExportScore] = useState('')


  /** MAPPERS */
  useEffect(() => {
    const fetchDatasetVersions = async () => {
      let latestVersion = initialProject?.latestDatasetVersion;
      const isLatestVersionNull = latestVersion == null || latestVersion == undefined;
      if (isLatestVersionNull) {
        latestVersion = 0;
      }
      const versions = Array.from({ length: latestVersion!! + 1 }, (_, i) => `V${i}`);
      
      if (inputLatestGenerationJobStatus.status == 'RUNNING' && !isLatestVersionNull) {
        versions.push(`V${latestVersion!! + 1}`);
      }

      setDatasetVersions(versions);
      if (versions.length > 0) {
        setSelectedVersion(versions[versions.length - 1]); // Set the latest version as default
      }
    };
    fetchDatasetVersions()
  }, [projectId])

  useEffect(() => {
    const fetchDataPoints = async () => {
      let dataPoints = inputDataset;

      if (generateJobStatus == 'RUNNING') {
        setDataset(prevDataset => ({
          ...prevDataset,
          records: [],
          isLatestVersion: true
        }))
      } else {
        setDataset(prevDataset => ({
          ...prevDataset,
          records: dataPoints.map((point, index) => ({
            id: point.id,
            name: point.name,
            type: point.type,
            data: point.data,
            liked: point.liked,
            topic: point.topic,
            qualityScore: point.qualityScore,
          })),
          isLatestVersion: selectedVersion === datasetVersions[datasetVersions.length - 1]
        }))
      }
    }
    fetchDataPoints()
  }, [projectId])


  /** POLLING JOBS */
  useEffect(() => {
    const pollRunningJobs = async () => {
      const runningJobs = fineTuneJobs.filter(job => job.status === 'RUNNING' || job.status === 'STARTED');
      for (const job of runningJobs) {
        const updatedEvents: any = await checkJobEvents(job.id);
        setFineTuneJobs(prevJobs => 
          prevJobs.map(prevJob => 
            prevJob.id === job.id 
              ? { ...prevJob, events: updatedEvents.events, status: updatedEvents.status, finetunedModel: updatedEvents.finetunedModel }
              : prevJob
          )
        );
      }
    };

    const intervalId = setInterval(pollRunningJobs, 5000);

    return () => clearInterval(intervalId);
  }, [fineTuneJobs]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    const pollSeedDataStatus = async () => {
      if (seedDataJobStatus === 'RUNNING' || seedDataJobStatus === 'STARTING') {
        const status: any = await fetchSeedDataUploadJobStatus(projectId);
        if (status == 'COMPLETE') {
          clearInterval(intervalId!);
          const seedData: any = await fetchAllSeedDataPoints(projectId);
          setSeedDataPoints(seedData);
        }
        setSeedDataJobStatus(status);
      }
    };

    if (seedDataJobStatus === 'RUNNING' || seedDataJobStatus === 'STARTING') {
      intervalId = setInterval(pollSeedDataStatus, 5 * 1000); //10 seconds
    } else {
      if (intervalId !== null || intervalId !== undefined) {
        clearInterval(intervalId!);
      }
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [projectId, seedDataJobStatus]);

  const pollEvaluationJobs = useCallback(async () => {
    try {
      const allEvaluationJobs = await getAllEvaluationJobForProject(projectId)
      const runningJobs = allEvaluationJobs.filter(job => job.status === 'RUNNING')
      
      setEvaluationJobs(prevJobs => {
        const updatedJobs = prevJobs.map(prevJob => {
          const updatedJob = allEvaluationJobs.find(job => job.id === prevJob.id)
          return updatedJob || prevJob
        })
        return [...updatedJobs, ...allEvaluationJobs.filter(job => !prevJobs.some(prevJob => prevJob.id === job.id))]
      })

      return runningJobs.length > 0
    } catch (error) {
      console.error('Error polling evaluation jobs:', error)
      return false
    }
  }, [projectId])

  useEffect(() => {
    let timeoutId: NodeJS.Timeout | null = null

    const runPolling = async () => {
      if (isPollingEvaluationJobs) {
        const shouldContinuePolling = await pollEvaluationJobs()
        if (shouldContinuePolling) {
          timeoutId = setTimeout(runPolling, 5000)
        } else {
          setIsPollingEvaluationJobs(false)
          // refetch everything after polling stops to make sure that everything is up to date
          let dataPoints = await getDataPointsByProjectIdAndVersion(projectId, parseInt(selectedVersion?.replace('V', ''), 10));
          let versionMetaData = await getJobDataForProjectAndVersion(projectId, parseInt(selectedVersion?.replace('V', ''), 10));
          if (dataPoints == undefined || dataPoints == null) {
            dataPoints = []
          }
          setDataset(prevDataset => ({
            ...prevDataset,
            records: dataPoints.map((point, index) => ({
              id: point.id,
              name: point.name, 
              type: point.type,
              data: point.data,
              liked: point.liked,
              topic: point.topic,
              qualityScore: point.qualityScore
            })),
            isLatestVersion: selectedVersion === datasetVersions[datasetVersions.length - 1]
          }))
          setGenerationAndEvaluationJobMetadata(versionMetaData);
          if (versionMetaData?.generationJob.status) {
            setGenerateJobStatus(versionMetaData?.generationJob.status);
          }
        }
      }
    }

    if (isPollingEvaluationJobs) {
      runPolling()
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [isPollingEvaluationJobs, pollEvaluationJobs])

  const startEvaluationJobPolling = useCallback(() => {
    setIsPollingEvaluationJobs(true)
  }, [])

  
  /** HANDLERS */
  const handleGenerate = async () => {
    if (parseInt(numRecords) > 500) {
      setNumRecordsError('Number of records cannot be greater than 500')
      return
    }
    if (!prompt.trim()) {
      setPromptError('Please enter a prompt for synthetic data generation')
      return
    }
    setNumRecordsError('')
    setIsGenerating(true)
    try {
      setGenerateJobStatus('STARTING')
      await generateData(projectId, prompt, numRecords, selectedModel);
      setGenerateJobStatus('RUNNING')
      
      // add a new version to the page and then select it right after the generate button is clicked
      let latestVersion = 'V0';
      if (datasetVersions.length > 0 && dataset.records.length > 0) {
        latestVersion = datasetVersions[datasetVersions.length - 1];
        let numericLatestVersion = parseInt(latestVersion?.replace('V', ''), 10)
        datasetVersions.push(`V${numericLatestVersion + 1}`);
        setDatasetVersions(datasetVersions);
        setSelectedVersion(datasetVersions[datasetVersions.length - 1]); // Set the latest version as default
      }

      setDataset(prevDataset => ({
        ...prevDataset,
        records:[],
        isLatestVersion: true
      }))
      setGenerationAndEvaluationJobMetadata({
        generationJob: null,
        evaluationJob: null
      });

    } catch (error) {
      console.error('Error generating data:', error)
      setGenerateJobStatus('ERROR')
    }
  }

  const handleFineTune = async () => {
    if (!openAIKey || !openAIModel || !selectedFineTuneVersion) {
      setModalError('Please enter your OpenAI API key, select a model, and choose a dataset version')
      return
    }
    setIsSubmitting(true)
    try {
      await createFineTuneRun(projectId, openAIKey, openAIModel, parseInt(selectedFineTuneVersion?.replace('V', ''), 10), filterFineTuneDownvoted, parseInt(filterFineTuneScore))
      const jobs = await getAllFineTuningJobForProject(projectId);

      setFineTuneJobs(jobs);
      setIsModalOpen(false)
      setModalError('')
    } catch (error) {
      console.error('Error creating fine-tune job:', error)
      setModalError('Something went wrong, try again')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleExport = async () => {
    if (!exportApiKey || !selectedExportVersion) {
      setExportModalError('Please enter your API key and select a dataset version')
      return
    }
    setIsExportSubmitting(true)
    try {
      const newJob: any = await uploadToHuggingFace(projectId, exportApiKey, parseInt(selectedExportVersion?.replace('V', ''), 10), filterExportDownvoted,  parseInt(filterExportScore));
      setExportJobs(prevJobs => [newJob, ...prevJobs]);
      setIsExportModalOpen(false)
      setExportModalError('')
    } catch (error) {
      console.error('Error creating export job:', error)
      setExportModalError('Something went wrong, try again')
    } finally {
      setIsExportSubmitting(false)
    }
  }


  const handleDownloadDataset = async () => {
    setIsDownloading(true)
    try {
      // Call the server action
      let latestVersion = initialProject?.latestDatasetVersion;
      if (latestVersion == null || latestVersion == undefined) {
        latestVersion = 0;
      }

      // NOTE: ONLY SUPPORTING THE LATEST VERSION FOR DOWNLOAD FOR NOW. CAN ADD TO THIS LATER.
      const jsonlContent = await generateJsonlData(projectId, latestVersion);
            const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'data.jsonl'); // Set the filename
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error during download:', error);
    } finally {
      setIsDownloading(false)
    }
  }


  const handlePagination = (page: number) => {
    setCurrentPage(page)
  }

  const handleSeedDataPagination = (page: number) => {
    setCurrentSeedDataPage(page)
  }

  const handleLike =  async (id: number, liked: number) => {
    let unfill = false;
    dataset.records.map((record: { id: number, liked: number | null }) => {
      if (record.id === id) {
        if (record.liked === liked) {
          unfill = true;
          record.liked = 0;
        } else {
          record.liked = liked
        }
      }
    });
    setDataset(prevDataset => ({
      ...prevDataset,
      records: dataset.records
    }))
    if (unfill) {
      await likeDataPoint(id.toString(), 0);
    } else {
      await likeDataPoint(id.toString(), liked);
    }
  }

  const handleVersionChange = async (version: string) => {
    setSelectedVersion(version)
    setIsLoadingDataset(true)

    try {
      let dataPoints = await getDataPointsByProjectIdAndVersion(projectId, parseInt(version?.replace('V', ''), 10));
      let versionMetaData = await getJobDataForProjectAndVersion(projectId, parseInt(version?.replace('V', ''), 10));
      if (dataPoints == undefined || dataPoints == null) {
        dataPoints = []
      }
      setDataset(prevDataset => ({
        ...prevDataset,
        records: dataPoints.map((point, index) => ({
          id: point.id,
          name: point.name, 
          type: point.type,
          data: point.data,
          liked: point.liked,
          topic: point.topic,
          qualityScore: point.qualityScore
        })),
        isLatestVersion: version === datasetVersions[datasetVersions.length - 1]
      }))
      setGenerationAndEvaluationJobMetadata(versionMetaData);
      if (versionMetaData?.generationJob.status) {
        setGenerateJobStatus(versionMetaData?.generationJob.status);
      }
    } catch (error) {
      console.error('Error fetching dataset:', error)
    } finally {
      setIsLoadingDataset(false)
    }
  }


  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0]
      if (file.name.endsWith('.jsonl')) {
        setSeedFile(file)
        setLatestSeedFile(file.name)
        setUploadError(null)
      } else {
        setUploadError('Only JSONL files are supported.')
        setSeedFile(null)
        setLatestSeedFile(null)
      }
    }
  }

  const handleGenerateSeedData = async () => {
    if (!seedFile) return
    setIsGeneratingSeedData(true)
    setSeedDataJobStatus('STARTING')
    try {
      const seedDataRunId = await startSeedDataRun(projectId, seedFile?.name!)
      await uploadData({
        path: `project/${projectId}/seed/${seedFile?.name}/${seedDataRunId}`,
        data: seedFile!,
      }).result;
      await updateSeedDataRunStatus(seedDataRunId!, 'RUNNING');
      setSeedDataJobStatus('RUNNING')
      setSeedFile(null)
    } catch (error) {
      console.error('Error generating seed data:', error)
      setSeedDataJobStatus('FAILED')
    } finally {
      setIsGeneratingSeedData(false)
      setSeedFile(null)
    }
  }

  const handleStartEvaluation = async () => {
    if (!selectedEvaluationVersion) {
      setEvaluationModalError('Please select a dataset version')
      return
    }
    setIsEvaluationSubmitting(true)
    try {
      const jobId = await createEvaluationJob(projectId, parseInt(selectedEvaluationVersion.replace('V', ''), 10))
      const newJob: EvaluationJob = {
        id: jobId!!,
        status: 'RUNNING',
        version: parseInt(selectedEvaluationVersion.replace('V', ''), 10),
        overallScore: null
      }
      setEvaluationJobs(prevJobs => [newJob, ...prevJobs])
      setIsEvaluationModalOpen(false)
      setEvaluationModalError('')
      startEvaluationJobPolling() // Start polling after creating a new job
    } catch (error) {
      console.error('Error starting evaluation job:', error)
      setEvaluationModalError('Something went wrong, please try again')
    } finally {
      setIsEvaluationSubmitting(false)
    }
  }

  /** RENDERERS */
  const indexOfLastRecord = currentPage * recordsPerPage
  const indexOfFirstRecord = indexOfLastRecord - recordsPerPage
  const currentRecords = dataset.records.slice(indexOfFirstRecord, indexOfLastRecord)
  const currentSeedDataRecords = seedDataPoints.slice(
    (currentSeedDataPage - 1) * seedDataPerPage,
    currentSeedDataPage * seedDataPerPage
  )

  const schemaExample = JSON.stringify({
    question: 'string',
    answer: 'string'
  }, null, 2);

  const totalPages = Math.ceil(dataset.records.length / recordsPerPage)
  const totalSeedDataPages = Math.ceil(seedDataPoints.length / seedDataPerPage)
  const evaluationForVersion = generationAndEvaluationJobMetadata.evaluationJob?.status == 'COMPLETE' ? generationAndEvaluationJobMetadata.evaluationJob : null;

  const renderPaginationButtons = (total: number, current: number, handler: (page: number) => void) => {
    const buttons = []
    const maxButtons = Math.min(total, 10);
    
    for (let i = 0; i <= maxButtons; i++) {
      let curr = i + (Math.floor(current/10) * 10);
      if (curr > total) {
        break;
      }

      if (curr !== 0) {
        buttons.push(
          <button
            key={curr}
            onClick={() => handler(curr)}
            className={`mx-1 px-3 py-1 rounded ${
              curr === current ? 'bg-pink-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            {curr}
          </button>
        )
      }
    }
    return buttons
  }

 
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'border-green-800 text-green-800'
    if (score >= 50) return 'border-yellow-500 text-yellow-500'
    return 'border-red-500 text-red-500'
  }

 /** COMPONENT */
 return (
  <div className="max-w-7xl mx-auto px-4 py-8">
    <h1 className="text-3xl font-bold mb-8">{dataset.name}</h1>
    
    <Tabs defaultValue="generate" className="mb-8">
        <TabsList className="bg-pink-100">
          <TabsTrigger value="generate" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white">Generate</TabsTrigger>
          <TabsTrigger value="evaluate" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white">Evaluate</TabsTrigger>
          <TabsTrigger value="finetune" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white">Finetune</TabsTrigger>
          <TabsTrigger value="export" className="data-[state=active]:bg-pink-600 data-[state=active]:text-white">Export</TabsTrigger>
        </TabsList>
      
      <TabsContent value="generate">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Dataset Description Card */}
          <Card>
            <CardHeader>
              <CardTitle>Dataset Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{dataset.description}</p>
            </CardContent>
          </Card>

          {/* Generate Dataset Card */}
          <Card>
            <CardHeader>
              <CardTitle>Generate Dataset</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label htmlFor="numRecords" className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Records
                  </label>
                  <Input
                    type="number"
                    id="numRecords"
                    value={numRecords}
                    onChange={(e) => setNumRecords(e.target.value)}
                    min="1"
                    max="500"
                    className="w-full"
                    disabled={isFieldsDisabled}
                  />
                  {numRecordsError && (
                      <p className="text-red-500 text-sm mt-1">{numRecordsError}</p>
                    )}
                </div>
                <div>
                  <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-2">
                    Model
                  </label>
                  <Select 
                    value={selectedModel} 
                    onValueChange={setSelectedModel}
                    disabled={isFieldsDisabled}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a model" />
                    </SelectTrigger>
                    <SelectContent>
                      {[
                        { value: 'gpt-4o-mini-2024-07-18' },
                        { value: 'gpt-4o-2024-08-06'},
                        { value: 'gpt-4-turbo-2024-04-09' },
                        // NOTE: Not supporting claude for the mvp, might support right after
                        // { value: 'claude-3-haiku-20240307' },
                        // { value: 'claude-3-5-sonnet-20240620' },
                        // { value: 'claude-3-opus-20240229' },
                      ].map((model) => (
                        <SelectItem key={model.value} value={model.value}>
                          {model.value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="mb-4">
                <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
                  Prompt for synthetic data generation
                </label>
                <div className="relative">
                  <textarea
                    id="prompt"
                    value={prompt}
                    onChange={(e) => {
                      setPrompt(e.target.value)
                      setPromptError('')
                    }}
                    className={`w-full p-2 border ${promptError ? 'border-red-500' : 'border-gray-300'} rounded-md`}
                    rows={3}
                    placeholder="Enter your prompt here..."
                    disabled={isFieldsDisabled}
                  />
                  <div className="absolute right-2 top-2">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <InfoIcon className="h-5 w-5 text-gray-400" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Enter a prompt to guide the synthetic data generation process.</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
                {promptError && (
                  <Alert variant="destructive" className="mt-2">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{promptError}</AlertDescription>
                  </Alert>
                )}
              </div>

              <div className="mb-4">
                <div className="flex items-center mb-2">
                  <label htmlFor="schema" className="block text-sm font-medium text-gray-700 mr-2">
                    Generated Data Schema
                  </label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <InfoIcon className="h-4 w-4 text-gray-400" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>The generated data will only be in question and answer format for now.</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <pre className="bg-gray-100 p-2 rounded-md text-sm overflow-x-auto">
                  {schemaExample}
                </pre>
                </div>

                {/* <div className="flex items-center space-x-2 mb-4">
                  <Checkbox
                    id="useSeedData"
                    checked={useSeedData}
                    onCheckedChange={(checked) => setUseSeedData(checked as boolean)}
                  />
                  <label
                    htmlFor="useSeedData"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    Use seed data in generation
                  </label>
                </div>

                <div className="mb-4">
                  <label htmlFor="seedFile" className="block text-sm font-medium text-gray-700 mb-2">
                    Upload Seed Data (JSONL files only)
                  </label>
                  <div className="flex items-center mb-2">
                    <input
                      type="file"
                      id="seedFile"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept=".jsonl"
                      className="hidden"
                    />
                    <Button
                      onClick={() => fileInputRef.current?.click()}
                      className="mr-2 bg-gray-200 text-gray-700 hover:bg-gray-300"
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Choose File
                    </Button>
                    <span className="text-sm text-gray-500 mr-2 flex items-center">
                      {latestSeedFile && (
                        <>
                          <CheckCircle2 className="mr-2 h-4 w-4 text-green-500" />
                          {latestSeedFile}
                        </>
                      )}
                      {!latestSeedFile && seedFile && seedFile.name}
                      {!latestSeedFile && !seedFile && 'No file chosen'}
                    </span>
                    {seedFile && (
                      <Button
                        onClick={handleGenerateSeedData}
                        disabled={isGeneratingSeedData}
                        className="bg-pink-600 hover:bg-pink-700 text-white"
                      >
                        {isGeneratingSeedData ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Uploading...
                          </>
                        ) : (
                          'Upload Seed Data'
                        )}
                      </Button>
                    )}
                  </div>
                  {uploadError && (
                    <Alert  variant="destructive">
                      <AlertTitle>Error</AlertTitle>
                      <AlertDescription>{uploadError}</AlertDescription>
                    </Alert>
                  )}
                </div> */}
              </CardContent>
              <CardFooter>
                <Button 
                  onClick={handleGenerate} 
                  disabled={isGenerating}
                  className="w-full bg-pink-600 hover:bg-pink-700 text-white"
                >
                  {isGenerating ? (
                    <>
                      Generating...
                    </>
                  ) : (
                    'Generate Dataset'
                  )}
                </Button>
              </CardFooter>
            </Card>
          </div>

          {/* Dataset/Seed Data Tabs */}
          {/* <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'dataset' | 'seeddata')} className="mb-4">
            <TabsList>
              <TabsTrigger value="dataset">Dataset</TabsTrigger>
              <TabsTrigger value="seeddata">Seed Data</TabsTrigger>
            </TabsList>
          </Tabs> */}

          {/* Dataset Records / Seed Data Card */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>{activeTab === 'dataset' ? 'Dataset Records' : 'Uploaded Seed Data'}</CardTitle>
                {activeTab === 'dataset' && (
                  <div className="flex items-center space-x-4">
                    <Label htmlFor="versionSelect" className="mr-2">
                      Version:
                    </Label>
                    <Select value={selectedVersion} onValueChange={handleVersionChange}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select a version" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasetVersions.map((version) => (
                          <SelectItem key={version} value={version}>
                            {version}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>

              {activeTab === 'dataset' && !isLoadingDataset && (
                <div className="mb-4 flex justify-between items-center">
                  <div className="flex items-center space-x-4">
                    <span className="font-semibold">Status:</span>
                    <Badge variant="outline" className={`${
                      generateJobStatus === 'NOT_STARTED' ? 'bg-gray-200 text-gray-800' :
                      generateJobStatus === 'STARTING' ? 'bg-yellow-200 text-yellow-800' :
                      generateJobStatus === 'RUNNING' ? 'bg-blue-200 text-blue-800' :
                      generateJobStatus === 'COMPLETE' ? 'bg-green-200 text-green-800' :
                      generateJobStatus === 'ERROR' ? 'bg-red-200 text-red-800' : 
                      // COMPLETE_WITH_ERROR is considered complete for now, we don't want to display is as erroroneous
                      generateJobStatus === 'COMPLETE_WITH_ERROR' ? 'bg-green-200 text-green-800' : 
                      'bg-green-200 text-green-800' 
                    }`}>
                      {generateJobStatus === 'COMPLETE_WITH_ERROR' ? 'COMPLETE' : generateJobStatus.charAt(0).toUpperCase() + generateJobStatus.slice(1)}
                    </Badge>
                  </div>
                  {evaluationForVersion && !isLoadingDataset && (
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold">Overall Evaluation Score:</span>
                      <div className={`${getScoreColor(evaluationForVersion?.averageQualityScore || 0)} font-bold`}>
                        {evaluationForVersion?.averageQualityScore?.toFixed(2)}
                      </div>
                    </div>
                 )}
                </div>
              )}
              
              {activeTab === 'dataset' ? (
                isLoadingDataset ? (
                  <div className="flex justify-center items-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-pink-600" />
                  </div>
                ) : 
                dataset.isLatestVersion && generateJobStatus == 'RUNNING' ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Generation job in progress for this version.</p>
                  </div>
                ) :
                dataset.records.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">No records generated yet. Click 'Generate Dataset' to start.</p>
                  </div>
                ) : (
                  <>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Topic</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quality Score (out of 100)</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentRecords.map((record: any) => (
                          <tr key={record.id} className="border-t border-gray-200">
                            <td className="px-4 py-2 text-sm text-gray-500">
                              <div className="max-h-24 overflow-y-auto">
                                <pre className="whitespace-pre-wrap break-words">
                                  {JSON.stringify(JSON.parse(record.data), null, 2)}
                                </pre>
                              </div>
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">{record.topic}</td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                              {record.qualityScore ? (
                                <div className={`${getScoreColor(record.qualityScore)} font-bold`}>
                                  {record.qualityScore.toFixed(2)}
                                </div>
                              ) : 'N/A'}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm font-medium">
                              <button 
                                onClick={() => handleLike(record.id, 1)} 
                                className="mr-2 p-1 rounded hover:bg-gray-100"
                                aria-label={`Like ${record.name}`}
                              >
                                <ThumbsUp 
                                  className={`h-5 w-5 ${record.liked === 1 ? 'text-green-700' : 'text-gray-400'}`}
                                  fill={record.liked === 1 ? '#db2777' : 'none'}
                                  stroke={record.liked === 1 ? '#db2777' : 'currentColor'}
                                  strokeWidth={2}
                                />
                              </button>
                              <button 
                                onClick={() => handleLike(record.id, -1)} 
                                className="p-1 rounded hover:bg-gray-100"
                                aria-label={`Dislike ${record.name}`}
                              >
                                <ThumbsDown 
                                  className={`h-5 w-5 ${record.liked === -1 ? 'text-red-700' : 'text-gray-400'}`}
                                  fill={record.liked === -1 ? '#db2777' : 'none'}
                                  stroke={record.liked === -1 ? '#db2777' : 'currentColor'}
                                  strokeWidth={2}
                                />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                {/* Pagination */}
                <div className="mt-4 flex justify-center items-center">
                  <button
                    onClick={() => handlePagination(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="mx-1 px-2 py-1 rounded bg-gray-200 text-gray-700 disabled:opacity-50"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  {renderPaginationButtons(totalPages, currentPage, handlePagination)}
                  <button
                    onClick={() => handlePagination(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="mx-1 px-2 py-1 rounded bg-gray-200 text-gray-700 disabled:opacity-50"
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </>
                )
              ) : (
                <>
                  {/* Status message */}
                  <div className="mb-4">
                    {seedDataJobStatus === 'STARTING' && !seedDataPoints.length && (
                      <div className="text-center py-8">
                        <p className="text-gray-500">Seed data upload has started</p>
                      </div>
                    )}
                    {seedDataJobStatus === 'RUNNING' && !seedDataPoints.length && (
                      <div className="text-center py-8">
                        <p className="text-gray-500">Seed data upload is running</p>
                      </div>
                    )}
                    {seedDataJobStatus === 'FAILED' && !seedDataPoints.length && (
                      <div className="text-center py-8">
                        <p className="text-gray-500">Previous run failed, please try again</p>
                      </div>
                    )}
                    {seedDataJobStatus === 'NOT STARTED' && !seedDataPoints.length && (
                       <div className="text-center py-8">
                        <p className="text-gray-500">No seed data available. Please upload seed data.</p>
                      </div>
                    )}
                  </div>

                  {/* Seed data table */}
                  {seedDataPoints.length > 0 && (
                    <>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                            </tr>
                          </thead>
                          <tbody>
                            {currentSeedDataRecords.map((point) => (
                              <tr key={point.id} className="border-t border-gray-200">
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{point.id}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{point.type}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                  {JSON.stringify(JSON.parse(point.data), null, 2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {/* Seed Data Pagination */}
                      <div className="mt-4 flex justify-center items-center">
                        <button
                          onClick={() => handleSeedDataPagination(Math.max(1, currentSeedDataPage - 1))}
                          disabled={currentSeedDataPage === 1}
                          className="mx-1 px-2 py-1 rounded bg-gray-200 text-gray-700 disabled:opacity-50"
                          aria-label="Previous page"
                        >
                          <ChevronLeft className="h-5 w-5" />
                        </button>
                        {renderPaginationButtons(totalSeedDataPages, currentSeedDataPage, handleSeedDataPagination)}
                        <button
                          onClick={() => handleSeedDataPagination(Math.min(totalSeedDataPages, currentSeedDataPage + 1))}
                          disabled={currentSeedDataPage === totalSeedDataPages}
                          className="mx-1 px-2 py-1 rounded bg-gray-200 text-gray-700 disabled:opacity-50"
                          aria-label="Next page"
                        >
                          <ChevronRight className="h-5 w-5" />
                        </button>
                      </div>
                    </>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="evaluate">
          <Card>
            <CardHeader>
              <CardTitle>Evaluation Jobs</CardTitle>
            </CardHeader>
            <CardContent>
              <Dialog open={isEvaluationModalOpen} onOpenChange={setIsEvaluationModalOpen}>
                <DialogTrigger asChild>
                  <Button className="mb-4 bg-pink-600 hover:bg-pink-700 text-white">
                    Start New Evaluation
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px]">
                  <DialogHeader>
                    <DialogTitle>Start New Evaluation</DialogTitle>
                    <DialogDescription>
                      Choose a dataset version to evaluate.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="evaluationDatasetVersion" className="text-right">
                        Version
                      </Label>
                      <Select value={selectedEvaluationVersion} onValueChange={setSelectedEvaluationVersion}>
                        <SelectTrigger className="w-full  col-span-3">
                          <SelectValue placeholder="Select a version" />
                        </SelectTrigger>
                        <SelectContent>
                          {datasetVersions.map((version) => (
                            <SelectItem key={version} value={version}>
                              {version}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  {evaluationModalError && <p className="text-red-500 text-sm">{evaluationModalError}</p>}
                  <DialogFooter>
                    <Button type="submit" onClick={handleStartEvaluation} className="bg-pink-600 hover:bg-pink-700 text-white" disabled={isEvaluationSubmitting}>
                      {isEvaluationSubmitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        'Start Evaluation'
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              
              {evaluationJobs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">No evaluation jobs yet. Click 'Start New Evaluation' to begin.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {evaluationJobs.map((job) => (
                    <Card key={job.id}>
                      <CardHeader>
                        <CardTitle className="flex justify-between items-center">
                          <span>Evaluation Job - {`V${job.version}`}</span>
                          <Badge variant="outline" className={`${
                            job.status === 'RUNNING' ? 'bg-blue-200 text-blue-800' :
                            job.status === 'COMPLETE' ? 'bg-green-200 text-green-800' :
                            job.status === 'FAILED' ? 'bg-red-200 text-red-800' :
                            'bg-gray-200 text-gray-800'
                          }`}>
                            {job.status}
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        {job.status === 'COMPLETE' && (
                          <div className="flex items-center mt-2">
                            <div className={`w-16 h-16 rounded-full border-4 ${getScoreColor(job.overallScore || 0)} flex items-center justify-center font-bold text-lg mr-3`}>
                              {job.overallScore?.toFixed(2)}
                            </div>
                            <span className="text-lg font-semibold">Overall Score</span>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        

        <TabsContent value="finetune">
          <Card>
            <CardHeader>
              <CardTitle>Fine-tune Jobs</CardTitle>
            </CardHeader>
            <CardContent>
              <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogTrigger asChild>
                  <Button className="mb-4 bg-pink-600 hover:bg-pink-700 text-white">
                    Add new fine tune run
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Add New Fine-tune Run</DialogTitle>
                  <DialogDescription>
                    Enter your OpenAI API key, select a model, and choose a dataset version to start a new fine-tune run.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="openAIKey" className="text-right">
                      API Key
                    </Label>
                    <Input
                      id="openAIKey"
                      value={openAIKey}
                      onChange={(e) => setOpenAIKey(e.target.value)}
                      className="col-span-3"
                      type="password"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="openAIModel" className="text-right">
                      Model
                    </Label>
                    <Select value={openAIModel} onValueChange={setOpenAIModel}>
                      <SelectTrigger className="w-full col-span-3">
                        <SelectValue placeholder="Select a model" />
                      </SelectTrigger>
                      <SelectContent>
                        {openAIModels.map((model) => (
                          <SelectItem key={model.value} value={model.value}>
                            {model.value}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="datasetVersion" className="text-right">
                      Version
                    </Label>
                    <Select value={selectedFineTuneVersion} onValueChange={setSelectedFineTuneVersion}>
                      <SelectTrigger className="w-full col-span-3">
                        <SelectValue placeholder="Select a version" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasetVersions.map((version) => (
                          <SelectItem key={version} value={version}>
                            {version}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="filterDownvoted" className="text-right">
                      Filter Downvoted (Optional)
                    </Label>
                    <Checkbox
                      id="filterDownvoted"
                      checked={filterFineTuneDownvoted}
                      onCheckedChange={(checked) => setFilterFineTuneDownvoted(checked as boolean)}
                      className="col-span-3 text-pink-600"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="filterScore" className="text-right">
                      Filter Score Under (Optional)
                    </Label>
                    <Input
                      id="filterScore"
                      type="number"
                      min="0"
                      max="100"
                      value={filterFineTuneScore}
                      onChange={(e) => setFilterFineTuneScore(e.target.value)}
                      className="col-span-3"
                    />
                  </div>
                </div>
                {modalError && <p className="text-red-500 text-sm">{modalError}</p>}
                <DialogFooter>
                  <Button type="submit" onClick={handleFineTune} className="bg-pink-600 hover:bg-pink-700 text-white" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      'Submit'
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
              </Dialog>
              
              {fineTuneJobs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">No fine-tune jobs yet. Click 'Add new fine tune run' to start.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {fineTuneJobs.map((job) => (
                    <Accordion type="single" collapsible className="w-full" key={job.id}>
                      <AccordionItem value={job.id}>
                        <AccordionTrigger className="flex justify-between items-center p-4 border rounded hover:bg-gray-50">
                          <div className="flex items-center space-x-4">
                            <h4 className="font-semibold">
                              {job.type} Fine-tuning - {job.model}
                            </h4>
                            <span className={`px-2 py-1 rounded-full text-sm ${
                              job.status === 'RUNNING' || job.status === 'STARTED' ? 'bg-blue-200 text-blue-800' :
                              job.status === 'COMPLETE' ? 'bg-green-200 text-green-800' :
                              job.status === 'FAILED' ? 'bg-red-200 text-red-800' :
                              'bg-gray-200 text-gray-800'
                            }`}>
                              {job.status}
                            </span>
                            {job.status === 'COMPLETE' && job.finetunedModel !== null && (
                              <a
                                href={`https://platform.openai.com/playground/chat?models=${job.model}&models=${job.finetunedModel}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-pink-600 hover:text-pink-800 inline-flex items-center"
                              >
                                Try in Playground
                                <ExternalLink className="ml-1 h-4 w-4" />
                              </a>
                            )}
                          </div>
                        </AccordionTrigger>
                        <AccordionContent>
                          <div className="p-4 space-y-2 bg-gray-50 rounded-b">
                            {job.events?.data?.map((event: any, index: any) => (
                              <div key={index} className="text-sm">
                                <span className="font-mono text-gray-500 mr-2">
                                  {new Date(event.created_at * 1000).toLocaleString()}
                                </span>
                                <span>{event.message}</span>
                              </div>
                            ))}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="export">
          <Card>
            <CardHeader>
              <CardTitle>Export Dataset</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between mb-4">
                <Dialog open={isExportModalOpen} onOpenChange={setIsExportModalOpen}>
                  <DialogTrigger asChild>
                    <Button className="bg-pink-600 hover:bg-pink-700 text-white">
                      Add new export run
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Add New Export Run</DialogTitle>
                  <DialogDescription>
                    Select a platform, enter your API key, and choose a dataset version to start a new export run.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="exportPlatform" className="text-right">
                      Platform
                    </Label>
                    <Select value={exportPlatform} onValueChange={setExportPlatform}>
                      <SelectTrigger className="w-full col-span-3">
                        <SelectValue placeholder="Select a platform" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="huggingface">Hugging Face</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="exportApiKey" className="text-right">
                      API Key
                    </Label>
                    <Input
                      id="exportApiKey"
                      value={exportApiKey}
                      onChange={(e) => setExportApiKey(e.target.value)}
                      className="col-span-3"
                      type="password"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="exportDatasetVersion" className="text-right">
                      Version
                    </Label>
                    <Select value={selectedExportVersion} onValueChange={setSelectedExportVersion}>
                      <SelectTrigger className="w-full col-span-3">
                        <SelectValue placeholder="Select a version" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasetVersions.map((version) => (
                          <SelectItem key={version} value={version}>
                            {version}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="filterExportDownvoted" className="text-right">
                      Filter Downvoted (Optional)
                    </Label>
                    <Checkbox
                      id="filterExportDownvoted"
                      checked={filterExportDownvoted}
                      onCheckedChange={(checked) => setFilterExportDownvoted(checked as boolean)}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="filterExportScore" className="text-right">
                      Filter Score Under (Optional)
                    </Label>
                    <Input
                      id="filterExportScore"
                      type="number"
                      min="0"
                      max="100"
                      value={filterExportScore}
                      onChange={(e) => setFilterExportScore(e.target.value)}
                      className="col-span-3"
                      />
                  </div>
                </div>
                {exportModalError && <p className="text-red-500 text-sm">{exportModalError}</p>}
                <DialogFooter>
                  <Button type="submit" onClick={handleExport} className="bg-pink-600 hover:bg-pink-700 text-white" disabled={isExportSubmitting}>
                    {isExportSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      'Start Export'
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
                </Dialog>
                <Button 
                  onClick={handleDownloadDataset} 
                  className="bg-pink-600 hover:bg-pink-700 text-white"
                  disabled={isDownloading}
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Download dataset
                    </>
                  )}
                </Button>
              </div>
              
              {exportJobs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">No export jobs yet. Click 'Add new export run' to start.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {exportJobs.map((job) => {
                    return  (
                    <Accordion type="single" collapsible className="w-full" key={job.id}>
                      <AccordionItem value={job.id}>
                        <AccordionTrigger className="flex justify-between items-center p-4 border rounded hover:bg-gray-50">
                          <div className="flex items-center space-x-4">
                            <h4 className="font-semibold">
                              {job.type} Export
                            </h4>
                            <span className={`px-2 py-1 rounded-full text-sm ${
                              job.status === 'RUNNING' || job.status === 'STARTED' ? 'bg-blue-200 text-blue-800' :
                              job.status === 'COMPLETE' ? 'bg-green-200 text-green-800' :
                              job.status === 'FAILED' ? 'bg-red-200 text-red-800' :
                              'bg-gray-200 text-gray-800'
                            }`}>
                              {job.status}
                            </span>
                            {job.status === 'COMPLETE' && job.datasetUrl && (
                              <a
                                href={job.datasetUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-pink-600 hover:text-pink-800 inline-flex items-center"
                              >
                                View Dataset
                                <ExternalLink className="ml-1 h-4 w-4" />
                              </a>
                            )}
                          </div>
                        </AccordionTrigger>
                        <AccordionContent>
                          <div className="p-4 space-y-2 bg-gray-50 rounded-b">
                            {Array.isArray(job.events.data) ? job.events.data.map((event, index) => (
                              <div key={index} className="text-sm">
                                <span className="font-mono text-gray-500 mr-2">
                                  {new Date(parseInt(event.created_at) * 1000).toLocaleString()}
                                </span>
                                <span>{event.message}</span>
                              </div>
                            )) : (
                              <p>No events available</p>
                            )}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  )})}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}