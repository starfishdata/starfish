export type Job = {
  id: any;
  type: any;
  model: any;
  status: any;
  events: any;
  result?: any;
  finetunedModel: any;
}

export type ExportJob = {
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

export type GenerateJobStatus = 'RUNNING' | 'COMPLETE' | 'NOT_STARTED' | 'COMPLETE_WITH_ERROR' | 'ERROR' | 'STARTING';

export type SeedDataPoint = {
  id: string;
  type: string;
  data: string;
}

export type EvaluationJob = {
  id: string;
  status: 'RUNNING' | 'COMPLETE' | 'FAILED';
  version: number;
  overallScore: number | null;
}

export type TemplateRegister = {
  name: string;
  input_schema?: any;
  output_schema?: any;
  description: string;
  author: string;
  starfish_version: string;
  dependencies: string[];
  input_example: any;
}

export type DatasetPageClientProps = {
  projectId: string;
  initialProject: {
    name: string | null | undefined;
    description: string | null | undefined;
    template_name: string;
  };
}

export interface Project {
  id: string
  name: string
  description: string
  template_name?: string
  template_description?: string
  owner: string
  repo: string
  repo_type: string
  language: string
  submittedAt: number
  created_at?: string
  // ... other fields
} 