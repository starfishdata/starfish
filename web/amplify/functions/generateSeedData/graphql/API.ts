/* tslint:disable */
/* eslint-disable */
//  This file was automatically generated and should not be edited.

export type Datapoint = {
  __typename: "Datapoint",
  cleaningTags?: string | null,
  createdAt: string,
  data?: string | null,
  evaluationTags?: string | null,
  feedbackTags?: string | null,
  generationTags?: string | null,
  id: string,
  name?: string | null,
  project?: Project | null,
  projectId?: string | null,
  type?: DatapointType | null,
  updatedAt: string,
  version?: number | null,
};

export type Project = {
  __typename: "Project",
  createdAt: string,
  datapoints?: ModelDatapointConnection | null,
  description?: string | null,
  exportJobs?: ModelExportJobConnection | null,
  finetuneJobs?: ModelFinetuneJobConnection | null,
  id: string,
  jobs?: ModelJobConnection | null,
  latestDatasetVersion?: number | null,
  latestSeedFile?: string | null,
  name?: string | null,
  seedDataUploadJobs?: ModelSeedDataUploadJobConnection | null,
  seedDatapoints?: ModelSeedDatapointConnection | null,
  updatedAt: string,
  user?: User | null,
  userId?: string | null,
};

export type ModelDatapointConnection = {
  __typename: "ModelDatapointConnection",
  items:  Array<Datapoint | null >,
  nextToken?: string | null,
};

export type ModelExportJobConnection = {
  __typename: "ModelExportJobConnection",
  items:  Array<ExportJob | null >,
  nextToken?: string | null,
};

export type ExportJob = {
  __typename: "ExportJob",
  apiKey?: string | null,
  createdAt: string,
  datasetUrl?: string | null,
  events?: string | null,
  id: string,
  project?: Project | null,
  projectId?: string | null,
  status?: ExportJobStatus | null,
  type?: ExportJobType | null,
  updatedAt: string,
};

export enum ExportJobStatus {
  COMPLETE = "COMPLETE",
  FAILED = "FAILED",
  RUNNING = "RUNNING",
}


export enum ExportJobType {
  HUGGINGFACE = "HUGGINGFACE",
}


export type ModelFinetuneJobConnection = {
  __typename: "ModelFinetuneJobConnection",
  items:  Array<FinetuneJob | null >,
  nextToken?: string | null,
};

export type FinetuneJob = {
  __typename: "FinetuneJob",
  apiKey?: string | null,
  createdAt: string,
  events?: string | null,
  finetunedModel?: string | null,
  id: string,
  jobIdentifier?: string | null,
  model?: string | null,
  project?: Project | null,
  projectId?: string | null,
  status?: FinetuneJobStatus | null,
  trainingFileId?: string | null,
  trainingFileName?: string | null,
  type?: FinetuneJobType | null,
  updatedAt: string,
};

export enum FinetuneJobStatus {
  COMPLETE = "COMPLETE",
  FAILED = "FAILED",
  NOT_STARTED = "NOT_STARTED",
  RUNNING = "RUNNING",
  STARTED = "STARTED",
}


export enum FinetuneJobType {
  OPENAI = "OPENAI",
}


export type ModelJobConnection = {
  __typename: "ModelJobConnection",
  items:  Array<Job | null >,
  nextToken?: string | null,
};

export type Job = {
  __typename: "Job",
  config?: string | null,
  createdAt: string,
  id: string,
  project?: Project | null,
  projectId?: string | null,
  status?: JobStatus | null,
  type?: JobType | null,
  updatedAt: string,
};

export enum JobStatus {
  COMPLETE = "COMPLETE",
  NOT_STARTED = "NOT_STARTED",
  RUNNING = "RUNNING",
}


export enum JobType {
  CLEANING = "CLEANING",
  EVALUATION = "EVALUATION",
  GENERATION = "GENERATION",
  USER_FEEDBACK = "USER_FEEDBACK",
}


export type ModelSeedDataUploadJobConnection = {
  __typename: "ModelSeedDataUploadJobConnection",
  items:  Array<SeedDataUploadJob | null >,
  nextToken?: string | null,
};

export type SeedDataUploadJob = {
  __typename: "SeedDataUploadJob",
  createdAt: string,
  fileName?: string | null,
  id: string,
  project?: Project | null,
  projectId?: string | null,
  status?: SeedDataUploadJobStatus | null,
  updatedAt: string,
};

export enum SeedDataUploadJobStatus {
  COMPLETE = "COMPLETE",
  FAILED = "FAILED",
  RUNNING = "RUNNING",
}


export type ModelSeedDatapointConnection = {
  __typename: "ModelSeedDatapointConnection",
  items:  Array<SeedDatapoint | null >,
  nextToken?: string | null,
};

export type SeedDatapoint = {
  __typename: "SeedDatapoint",
  cleaningTags?: string | null,
  createdAt: string,
  data?: string | null,
  evaluationTags?: string | null,
  feedbackTags?: string | null,
  generationTags?: string | null,
  id: string,
  name?: string | null,
  project?: Project | null,
  projectId?: string | null,
  seedDataFile?: string | null,
  type?: SeedDatapointType | null,
  updatedAt: string,
};

export enum SeedDatapointType {
  SEED = "SEED",
}


export type User = {
  __typename: "User",
  createdAt: string,
  email: string,
  id: string,
  name: string,
  projects?: ModelProjectConnection | null,
  role?: string | null,
  updatedAt: string,
};

export type ModelProjectConnection = {
  __typename: "ModelProjectConnection",
  items:  Array<Project | null >,
  nextToken?: string | null,
};

export enum DatapointType {
  SYNTHETIC = "SYNTHETIC",
}


export type ModelDatapointFilterInput = {
  and?: Array< ModelDatapointFilterInput | null > | null,
  cleaningTags?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  data?: ModelStringInput | null,
  evaluationTags?: ModelStringInput | null,
  feedbackTags?: ModelStringInput | null,
  generationTags?: ModelStringInput | null,
  id?: ModelIDInput | null,
  name?: ModelStringInput | null,
  not?: ModelDatapointFilterInput | null,
  or?: Array< ModelDatapointFilterInput | null > | null,
  projectId?: ModelIDInput | null,
  type?: ModelDatapointTypeInput | null,
  updatedAt?: ModelStringInput | null,
  version?: ModelIntInput | null,
};

export type ModelStringInput = {
  attributeExists?: boolean | null,
  attributeType?: ModelAttributeTypes | null,
  beginsWith?: string | null,
  between?: Array< string | null > | null,
  contains?: string | null,
  eq?: string | null,
  ge?: string | null,
  gt?: string | null,
  le?: string | null,
  lt?: string | null,
  ne?: string | null,
  notContains?: string | null,
  size?: ModelSizeInput | null,
};

export enum ModelAttributeTypes {
  _null = "_null",
  binary = "binary",
  binarySet = "binarySet",
  bool = "bool",
  list = "list",
  map = "map",
  number = "number",
  numberSet = "numberSet",
  string = "string",
  stringSet = "stringSet",
}


export type ModelSizeInput = {
  between?: Array< number | null > | null,
  eq?: number | null,
  ge?: number | null,
  gt?: number | null,
  le?: number | null,
  lt?: number | null,
  ne?: number | null,
};

export type ModelIDInput = {
  attributeExists?: boolean | null,
  attributeType?: ModelAttributeTypes | null,
  beginsWith?: string | null,
  between?: Array< string | null > | null,
  contains?: string | null,
  eq?: string | null,
  ge?: string | null,
  gt?: string | null,
  le?: string | null,
  lt?: string | null,
  ne?: string | null,
  notContains?: string | null,
  size?: ModelSizeInput | null,
};

export type ModelDatapointTypeInput = {
  eq?: DatapointType | null,
  ne?: DatapointType | null,
};

export type ModelIntInput = {
  attributeExists?: boolean | null,
  attributeType?: ModelAttributeTypes | null,
  between?: Array< number | null > | null,
  eq?: number | null,
  ge?: number | null,
  gt?: number | null,
  le?: number | null,
  lt?: number | null,
  ne?: number | null,
};

export enum ModelSortDirection {
  ASC = "ASC",
  DESC = "DESC",
}


export type ModelExportJobFilterInput = {
  and?: Array< ModelExportJobFilterInput | null > | null,
  apiKey?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  datasetUrl?: ModelStringInput | null,
  events?: ModelStringInput | null,
  id?: ModelIDInput | null,
  not?: ModelExportJobFilterInput | null,
  or?: Array< ModelExportJobFilterInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelExportJobStatusInput | null,
  type?: ModelExportJobTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type ModelExportJobStatusInput = {
  eq?: ExportJobStatus | null,
  ne?: ExportJobStatus | null,
};

export type ModelExportJobTypeInput = {
  eq?: ExportJobType | null,
  ne?: ExportJobType | null,
};

export type ModelFinetuneJobFilterInput = {
  and?: Array< ModelFinetuneJobFilterInput | null > | null,
  apiKey?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  events?: ModelStringInput | null,
  finetunedModel?: ModelStringInput | null,
  id?: ModelIDInput | null,
  jobIdentifier?: ModelStringInput | null,
  model?: ModelStringInput | null,
  not?: ModelFinetuneJobFilterInput | null,
  or?: Array< ModelFinetuneJobFilterInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelFinetuneJobStatusInput | null,
  trainingFileId?: ModelStringInput | null,
  trainingFileName?: ModelStringInput | null,
  type?: ModelFinetuneJobTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type ModelFinetuneJobStatusInput = {
  eq?: FinetuneJobStatus | null,
  ne?: FinetuneJobStatus | null,
};

export type ModelFinetuneJobTypeInput = {
  eq?: FinetuneJobType | null,
  ne?: FinetuneJobType | null,
};

export type ModelJobFilterInput = {
  and?: Array< ModelJobFilterInput | null > | null,
  config?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  id?: ModelIDInput | null,
  not?: ModelJobFilterInput | null,
  or?: Array< ModelJobFilterInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelJobStatusInput | null,
  type?: ModelJobTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type ModelJobStatusInput = {
  eq?: JobStatus | null,
  ne?: JobStatus | null,
};

export type ModelJobTypeInput = {
  eq?: JobType | null,
  ne?: JobType | null,
};

export type ModelProjectFilterInput = {
  and?: Array< ModelProjectFilterInput | null > | null,
  createdAt?: ModelStringInput | null,
  description?: ModelStringInput | null,
  id?: ModelIDInput | null,
  latestDatasetVersion?: ModelIntInput | null,
  latestSeedFile?: ModelStringInput | null,
  name?: ModelStringInput | null,
  not?: ModelProjectFilterInput | null,
  or?: Array< ModelProjectFilterInput | null > | null,
  updatedAt?: ModelStringInput | null,
  userId?: ModelIDInput | null,
};

export type ModelSeedDataUploadJobFilterInput = {
  and?: Array< ModelSeedDataUploadJobFilterInput | null > | null,
  createdAt?: ModelStringInput | null,
  fileName?: ModelStringInput | null,
  id?: ModelIDInput | null,
  not?: ModelSeedDataUploadJobFilterInput | null,
  or?: Array< ModelSeedDataUploadJobFilterInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelSeedDataUploadJobStatusInput | null,
  updatedAt?: ModelStringInput | null,
};

export type ModelSeedDataUploadJobStatusInput = {
  eq?: SeedDataUploadJobStatus | null,
  ne?: SeedDataUploadJobStatus | null,
};

export type ModelSeedDatapointFilterInput = {
  and?: Array< ModelSeedDatapointFilterInput | null > | null,
  cleaningTags?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  data?: ModelStringInput | null,
  evaluationTags?: ModelStringInput | null,
  feedbackTags?: ModelStringInput | null,
  generationTags?: ModelStringInput | null,
  id?: ModelIDInput | null,
  name?: ModelStringInput | null,
  not?: ModelSeedDatapointFilterInput | null,
  or?: Array< ModelSeedDatapointFilterInput | null > | null,
  projectId?: ModelIDInput | null,
  seedDataFile?: ModelStringInput | null,
  type?: ModelSeedDatapointTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type ModelSeedDatapointTypeInput = {
  eq?: SeedDatapointType | null,
  ne?: SeedDatapointType | null,
};

export type ModelUserFilterInput = {
  and?: Array< ModelUserFilterInput | null > | null,
  createdAt?: ModelStringInput | null,
  email?: ModelStringInput | null,
  id?: ModelIDInput | null,
  name?: ModelStringInput | null,
  not?: ModelUserFilterInput | null,
  or?: Array< ModelUserFilterInput | null > | null,
  role?: ModelStringInput | null,
  updatedAt?: ModelStringInput | null,
};

export type ModelUserConnection = {
  __typename: "ModelUserConnection",
  items:  Array<User | null >,
  nextToken?: string | null,
};

export type ModelDatapointConditionInput = {
  and?: Array< ModelDatapointConditionInput | null > | null,
  cleaningTags?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  data?: ModelStringInput | null,
  evaluationTags?: ModelStringInput | null,
  feedbackTags?: ModelStringInput | null,
  generationTags?: ModelStringInput | null,
  name?: ModelStringInput | null,
  not?: ModelDatapointConditionInput | null,
  or?: Array< ModelDatapointConditionInput | null > | null,
  projectId?: ModelIDInput | null,
  type?: ModelDatapointTypeInput | null,
  updatedAt?: ModelStringInput | null,
  version?: ModelIntInput | null,
};

export type CreateDatapointInput = {
  cleaningTags?: string | null,
  data?: string | null,
  evaluationTags?: string | null,
  feedbackTags?: string | null,
  generationTags?: string | null,
  id?: string | null,
  name?: string | null,
  projectId?: string | null,
  type?: DatapointType | null,
  version?: number | null,
};

export type ModelExportJobConditionInput = {
  and?: Array< ModelExportJobConditionInput | null > | null,
  apiKey?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  datasetUrl?: ModelStringInput | null,
  events?: ModelStringInput | null,
  not?: ModelExportJobConditionInput | null,
  or?: Array< ModelExportJobConditionInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelExportJobStatusInput | null,
  type?: ModelExportJobTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type CreateExportJobInput = {
  apiKey?: string | null,
  datasetUrl?: string | null,
  events?: string | null,
  id?: string | null,
  projectId?: string | null,
  status?: ExportJobStatus | null,
  type?: ExportJobType | null,
};

export type ModelFinetuneJobConditionInput = {
  and?: Array< ModelFinetuneJobConditionInput | null > | null,
  apiKey?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  events?: ModelStringInput | null,
  finetunedModel?: ModelStringInput | null,
  jobIdentifier?: ModelStringInput | null,
  model?: ModelStringInput | null,
  not?: ModelFinetuneJobConditionInput | null,
  or?: Array< ModelFinetuneJobConditionInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelFinetuneJobStatusInput | null,
  trainingFileId?: ModelStringInput | null,
  trainingFileName?: ModelStringInput | null,
  type?: ModelFinetuneJobTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type CreateFinetuneJobInput = {
  apiKey?: string | null,
  events?: string | null,
  finetunedModel?: string | null,
  id?: string | null,
  jobIdentifier?: string | null,
  model?: string | null,
  projectId?: string | null,
  status?: FinetuneJobStatus | null,
  trainingFileId?: string | null,
  trainingFileName?: string | null,
  type?: FinetuneJobType | null,
};

export type ModelJobConditionInput = {
  and?: Array< ModelJobConditionInput | null > | null,
  config?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  not?: ModelJobConditionInput | null,
  or?: Array< ModelJobConditionInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelJobStatusInput | null,
  type?: ModelJobTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type CreateJobInput = {
  config?: string | null,
  id?: string | null,
  projectId?: string | null,
  status?: JobStatus | null,
  type?: JobType | null,
};

export type ModelProjectConditionInput = {
  and?: Array< ModelProjectConditionInput | null > | null,
  createdAt?: ModelStringInput | null,
  description?: ModelStringInput | null,
  latestDatasetVersion?: ModelIntInput | null,
  latestSeedFile?: ModelStringInput | null,
  name?: ModelStringInput | null,
  not?: ModelProjectConditionInput | null,
  or?: Array< ModelProjectConditionInput | null > | null,
  updatedAt?: ModelStringInput | null,
  userId?: ModelIDInput | null,
};

export type CreateProjectInput = {
  description?: string | null,
  id?: string | null,
  latestDatasetVersion?: number | null,
  latestSeedFile?: string | null,
  name?: string | null,
  userId?: string | null,
};

export type ModelSeedDataUploadJobConditionInput = {
  and?: Array< ModelSeedDataUploadJobConditionInput | null > | null,
  createdAt?: ModelStringInput | null,
  fileName?: ModelStringInput | null,
  not?: ModelSeedDataUploadJobConditionInput | null,
  or?: Array< ModelSeedDataUploadJobConditionInput | null > | null,
  projectId?: ModelIDInput | null,
  status?: ModelSeedDataUploadJobStatusInput | null,
  updatedAt?: ModelStringInput | null,
};

export type CreateSeedDataUploadJobInput = {
  fileName?: string | null,
  id?: string | null,
  projectId?: string | null,
  status?: SeedDataUploadJobStatus | null,
};

export type ModelSeedDatapointConditionInput = {
  and?: Array< ModelSeedDatapointConditionInput | null > | null,
  cleaningTags?: ModelStringInput | null,
  createdAt?: ModelStringInput | null,
  data?: ModelStringInput | null,
  evaluationTags?: ModelStringInput | null,
  feedbackTags?: ModelStringInput | null,
  generationTags?: ModelStringInput | null,
  name?: ModelStringInput | null,
  not?: ModelSeedDatapointConditionInput | null,
  or?: Array< ModelSeedDatapointConditionInput | null > | null,
  projectId?: ModelIDInput | null,
  seedDataFile?: ModelStringInput | null,
  type?: ModelSeedDatapointTypeInput | null,
  updatedAt?: ModelStringInput | null,
};

export type CreateSeedDatapointInput = {
  cleaningTags?: string | null,
  data?: string | null,
  evaluationTags?: string | null,
  feedbackTags?: string | null,
  generationTags?: string | null,
  id?: string | null,
  name?: string | null,
  projectId?: string | null,
  seedDataFile?: string | null,
  type?: SeedDatapointType | null,
};

export type ModelUserConditionInput = {
  and?: Array< ModelUserConditionInput | null > | null,
  createdAt?: ModelStringInput | null,
  email?: ModelStringInput | null,
  name?: ModelStringInput | null,
  not?: ModelUserConditionInput | null,
  or?: Array< ModelUserConditionInput | null > | null,
  role?: ModelStringInput | null,
  updatedAt?: ModelStringInput | null,
};

export type CreateUserInput = {
  email: string,
  id?: string | null,
  name: string,
  role?: string | null,
};

export type DeleteDatapointInput = {
  id: string,
};

export type DeleteExportJobInput = {
  id: string,
};

export type DeleteFinetuneJobInput = {
  id: string,
};

export type DeleteJobInput = {
  id: string,
};

export type DeleteProjectInput = {
  id: string,
};

export type DeleteSeedDataUploadJobInput = {
  id: string,
};

export type DeleteSeedDatapointInput = {
  id: string,
};

export type DeleteUserInput = {
  id: string,
};

export type UpdateDatapointInput = {
  cleaningTags?: string | null,
  data?: string | null,
  evaluationTags?: string | null,
  feedbackTags?: string | null,
  generationTags?: string | null,
  id: string,
  name?: string | null,
  projectId?: string | null,
  type?: DatapointType | null,
  version?: number | null,
};

export type UpdateExportJobInput = {
  apiKey?: string | null,
  datasetUrl?: string | null,
  events?: string | null,
  id: string,
  projectId?: string | null,
  status?: ExportJobStatus | null,
  type?: ExportJobType | null,
};

export type UpdateFinetuneJobInput = {
  apiKey?: string | null,
  events?: string | null,
  finetunedModel?: string | null,
  id: string,
  jobIdentifier?: string | null,
  model?: string | null,
  projectId?: string | null,
  status?: FinetuneJobStatus | null,
  trainingFileId?: string | null,
  trainingFileName?: string | null,
  type?: FinetuneJobType | null,
};

export type UpdateJobInput = {
  config?: string | null,
  id: string,
  projectId?: string | null,
  status?: JobStatus | null,
  type?: JobType | null,
};

export type UpdateProjectInput = {
  description?: string | null,
  id: string,
  latestDatasetVersion?: number | null,
  latestSeedFile?: string | null,
  name?: string | null,
  userId?: string | null,
};

export type UpdateSeedDataUploadJobInput = {
  fileName?: string | null,
  id: string,
  projectId?: string | null,
  status?: SeedDataUploadJobStatus | null,
};

export type UpdateSeedDatapointInput = {
  cleaningTags?: string | null,
  data?: string | null,
  evaluationTags?: string | null,
  feedbackTags?: string | null,
  generationTags?: string | null,
  id: string,
  name?: string | null,
  projectId?: string | null,
  seedDataFile?: string | null,
  type?: SeedDatapointType | null,
};

export type UpdateUserInput = {
  email?: string | null,
  id: string,
  name?: string | null,
  role?: string | null,
};

export type ModelSubscriptionDatapointFilterInput = {
  and?: Array< ModelSubscriptionDatapointFilterInput | null > | null,
  cleaningTags?: ModelSubscriptionStringInput | null,
  createdAt?: ModelSubscriptionStringInput | null,
  data?: ModelSubscriptionStringInput | null,
  evaluationTags?: ModelSubscriptionStringInput | null,
  feedbackTags?: ModelSubscriptionStringInput | null,
  generationTags?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  name?: ModelSubscriptionStringInput | null,
  or?: Array< ModelSubscriptionDatapointFilterInput | null > | null,
  projectId?: ModelSubscriptionIDInput | null,
  type?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
  version?: ModelSubscriptionIntInput | null,
};

export type ModelSubscriptionStringInput = {
  beginsWith?: string | null,
  between?: Array< string | null > | null,
  contains?: string | null,
  eq?: string | null,
  ge?: string | null,
  gt?: string | null,
  in?: Array< string | null > | null,
  le?: string | null,
  lt?: string | null,
  ne?: string | null,
  notContains?: string | null,
  notIn?: Array< string | null > | null,
};

export type ModelSubscriptionIDInput = {
  beginsWith?: string | null,
  between?: Array< string | null > | null,
  contains?: string | null,
  eq?: string | null,
  ge?: string | null,
  gt?: string | null,
  in?: Array< string | null > | null,
  le?: string | null,
  lt?: string | null,
  ne?: string | null,
  notContains?: string | null,
  notIn?: Array< string | null > | null,
};

export type ModelSubscriptionIntInput = {
  between?: Array< number | null > | null,
  eq?: number | null,
  ge?: number | null,
  gt?: number | null,
  in?: Array< number | null > | null,
  le?: number | null,
  lt?: number | null,
  ne?: number | null,
  notIn?: Array< number | null > | null,
};

export type ModelSubscriptionExportJobFilterInput = {
  and?: Array< ModelSubscriptionExportJobFilterInput | null > | null,
  apiKey?: ModelSubscriptionStringInput | null,
  createdAt?: ModelSubscriptionStringInput | null,
  datasetUrl?: ModelSubscriptionStringInput | null,
  events?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  or?: Array< ModelSubscriptionExportJobFilterInput | null > | null,
  projectId?: ModelSubscriptionIDInput | null,
  status?: ModelSubscriptionStringInput | null,
  type?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
};

export type ModelSubscriptionFinetuneJobFilterInput = {
  and?: Array< ModelSubscriptionFinetuneJobFilterInput | null > | null,
  apiKey?: ModelSubscriptionStringInput | null,
  createdAt?: ModelSubscriptionStringInput | null,
  events?: ModelSubscriptionStringInput | null,
  finetunedModel?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  jobIdentifier?: ModelSubscriptionStringInput | null,
  model?: ModelSubscriptionStringInput | null,
  or?: Array< ModelSubscriptionFinetuneJobFilterInput | null > | null,
  projectId?: ModelSubscriptionIDInput | null,
  status?: ModelSubscriptionStringInput | null,
  trainingFileId?: ModelSubscriptionStringInput | null,
  trainingFileName?: ModelSubscriptionStringInput | null,
  type?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
};

export type ModelSubscriptionJobFilterInput = {
  and?: Array< ModelSubscriptionJobFilterInput | null > | null,
  config?: ModelSubscriptionStringInput | null,
  createdAt?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  or?: Array< ModelSubscriptionJobFilterInput | null > | null,
  projectId?: ModelSubscriptionIDInput | null,
  status?: ModelSubscriptionStringInput | null,
  type?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
};

export type ModelSubscriptionProjectFilterInput = {
  and?: Array< ModelSubscriptionProjectFilterInput | null > | null,
  createdAt?: ModelSubscriptionStringInput | null,
  description?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  latestDatasetVersion?: ModelSubscriptionIntInput | null,
  latestSeedFile?: ModelSubscriptionStringInput | null,
  name?: ModelSubscriptionStringInput | null,
  or?: Array< ModelSubscriptionProjectFilterInput | null > | null,
  updatedAt?: ModelSubscriptionStringInput | null,
  userId?: ModelSubscriptionIDInput | null,
};

export type ModelSubscriptionSeedDataUploadJobFilterInput = {
  and?: Array< ModelSubscriptionSeedDataUploadJobFilterInput | null > | null,
  createdAt?: ModelSubscriptionStringInput | null,
  fileName?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  or?: Array< ModelSubscriptionSeedDataUploadJobFilterInput | null > | null,
  projectId?: ModelSubscriptionIDInput | null,
  status?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
};

export type ModelSubscriptionSeedDatapointFilterInput = {
  and?: Array< ModelSubscriptionSeedDatapointFilterInput | null > | null,
  cleaningTags?: ModelSubscriptionStringInput | null,
  createdAt?: ModelSubscriptionStringInput | null,
  data?: ModelSubscriptionStringInput | null,
  evaluationTags?: ModelSubscriptionStringInput | null,
  feedbackTags?: ModelSubscriptionStringInput | null,
  generationTags?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  name?: ModelSubscriptionStringInput | null,
  or?: Array< ModelSubscriptionSeedDatapointFilterInput | null > | null,
  projectId?: ModelSubscriptionIDInput | null,
  seedDataFile?: ModelSubscriptionStringInput | null,
  type?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
};

export type ModelSubscriptionUserFilterInput = {
  and?: Array< ModelSubscriptionUserFilterInput | null > | null,
  createdAt?: ModelSubscriptionStringInput | null,
  email?: ModelSubscriptionStringInput | null,
  id?: ModelSubscriptionIDInput | null,
  name?: ModelSubscriptionStringInput | null,
  or?: Array< ModelSubscriptionUserFilterInput | null > | null,
  role?: ModelSubscriptionStringInput | null,
  updatedAt?: ModelSubscriptionStringInput | null,
};

export type GetDatapointQueryVariables = {
  id: string,
};

export type GetDatapointQuery = {
  getDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type GetExportJobQueryVariables = {
  id: string,
};

export type GetExportJobQuery = {
  getExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type GetFinetuneJobQueryVariables = {
  id: string,
};

export type GetFinetuneJobQuery = {
  getFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type GetJobQueryVariables = {
  id: string,
};

export type GetJobQuery = {
  getJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type GetProjectQueryVariables = {
  id: string,
};

export type GetProjectQuery = {
  getProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type GetSeedDataUploadJobQueryVariables = {
  id: string,
};

export type GetSeedDataUploadJobQuery = {
  getSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type GetSeedDatapointQueryVariables = {
  id: string,
};

export type GetSeedDatapointQuery = {
  getSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type GetUserQueryVariables = {
  id: string,
};

export type GetUserQuery = {
  getUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};

export type ListDatapointsQueryVariables = {
  filter?: ModelDatapointFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListDatapointsQuery = {
  listDatapoints?:  {
    __typename: "ModelDatapointConnection",
    items:  Array< {
      __typename: "Datapoint",
      cleaningTags?: string | null,
      createdAt: string,
      data?: string | null,
      evaluationTags?: string | null,
      feedbackTags?: string | null,
      generationTags?: string | null,
      id: string,
      name?: string | null,
      projectId?: string | null,
      type?: DatapointType | null,
      updatedAt: string,
      version?: number | null,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListExportJobsQueryVariables = {
  filter?: ModelExportJobFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListExportJobsQuery = {
  listExportJobs?:  {
    __typename: "ModelExportJobConnection",
    items:  Array< {
      __typename: "ExportJob",
      apiKey?: string | null,
      createdAt: string,
      datasetUrl?: string | null,
      events?: string | null,
      id: string,
      projectId?: string | null,
      status?: ExportJobStatus | null,
      type?: ExportJobType | null,
      updatedAt: string,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListFinetuneJobsQueryVariables = {
  filter?: ModelFinetuneJobFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListFinetuneJobsQuery = {
  listFinetuneJobs?:  {
    __typename: "ModelFinetuneJobConnection",
    items:  Array< {
      __typename: "FinetuneJob",
      apiKey?: string | null,
      createdAt: string,
      events?: string | null,
      finetunedModel?: string | null,
      id: string,
      jobIdentifier?: string | null,
      model?: string | null,
      projectId?: string | null,
      status?: FinetuneJobStatus | null,
      trainingFileId?: string | null,
      trainingFileName?: string | null,
      type?: FinetuneJobType | null,
      updatedAt: string,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListJobsQueryVariables = {
  filter?: ModelJobFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListJobsQuery = {
  listJobs?:  {
    __typename: "ModelJobConnection",
    items:  Array< {
      __typename: "Job",
      config?: string | null,
      createdAt: string,
      id: string,
      projectId?: string | null,
      status?: JobStatus | null,
      type?: JobType | null,
      updatedAt: string,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListProjectsQueryVariables = {
  filter?: ModelProjectFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListProjectsQuery = {
  listProjects?:  {
    __typename: "ModelProjectConnection",
    items:  Array< {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListSeedDataUploadJobsQueryVariables = {
  filter?: ModelSeedDataUploadJobFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListSeedDataUploadJobsQuery = {
  listSeedDataUploadJobs?:  {
    __typename: "ModelSeedDataUploadJobConnection",
    items:  Array< {
      __typename: "SeedDataUploadJob",
      createdAt: string,
      fileName?: string | null,
      id: string,
      projectId?: string | null,
      status?: SeedDataUploadJobStatus | null,
      updatedAt: string,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListSeedDatapointsQueryVariables = {
  filter?: ModelSeedDatapointFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListSeedDatapointsQuery = {
  listSeedDatapoints?:  {
    __typename: "ModelSeedDatapointConnection",
    items:  Array< {
      __typename: "SeedDatapoint",
      cleaningTags?: string | null,
      createdAt: string,
      data?: string | null,
      evaluationTags?: string | null,
      feedbackTags?: string | null,
      generationTags?: string | null,
      id: string,
      name?: string | null,
      projectId?: string | null,
      seedDataFile?: string | null,
      type?: SeedDatapointType | null,
      updatedAt: string,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type ListUsersQueryVariables = {
  filter?: ModelUserFilterInput | null,
  id?: string | null,
  limit?: number | null,
  nextToken?: string | null,
  sortDirection?: ModelSortDirection | null,
};

export type ListUsersQuery = {
  listUsers?:  {
    __typename: "ModelUserConnection",
    items:  Array< {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null >,
    nextToken?: string | null,
  } | null,
};

export type CreateDatapointMutationVariables = {
  condition?: ModelDatapointConditionInput | null,
  input: CreateDatapointInput,
};

export type CreateDatapointMutation = {
  createDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type CreateExportJobMutationVariables = {
  condition?: ModelExportJobConditionInput | null,
  input: CreateExportJobInput,
};

export type CreateExportJobMutation = {
  createExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type CreateFinetuneJobMutationVariables = {
  condition?: ModelFinetuneJobConditionInput | null,
  input: CreateFinetuneJobInput,
};

export type CreateFinetuneJobMutation = {
  createFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type CreateJobMutationVariables = {
  condition?: ModelJobConditionInput | null,
  input: CreateJobInput,
};

export type CreateJobMutation = {
  createJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type CreateProjectMutationVariables = {
  condition?: ModelProjectConditionInput | null,
  input: CreateProjectInput,
};

export type CreateProjectMutation = {
  createProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type CreateSeedDataUploadJobMutationVariables = {
  condition?: ModelSeedDataUploadJobConditionInput | null,
  input: CreateSeedDataUploadJobInput,
};

export type CreateSeedDataUploadJobMutation = {
  createSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type CreateSeedDatapointMutationVariables = {
  condition?: ModelSeedDatapointConditionInput | null,
  input: CreateSeedDatapointInput,
};

export type CreateSeedDatapointMutation = {
  createSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type CreateUserMutationVariables = {
  condition?: ModelUserConditionInput | null,
  input: CreateUserInput,
};

export type CreateUserMutation = {
  createUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};

export type DeleteDatapointMutationVariables = {
  condition?: ModelDatapointConditionInput | null,
  input: DeleteDatapointInput,
};

export type DeleteDatapointMutation = {
  deleteDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type DeleteExportJobMutationVariables = {
  condition?: ModelExportJobConditionInput | null,
  input: DeleteExportJobInput,
};

export type DeleteExportJobMutation = {
  deleteExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type DeleteFinetuneJobMutationVariables = {
  condition?: ModelFinetuneJobConditionInput | null,
  input: DeleteFinetuneJobInput,
};

export type DeleteFinetuneJobMutation = {
  deleteFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type DeleteJobMutationVariables = {
  condition?: ModelJobConditionInput | null,
  input: DeleteJobInput,
};

export type DeleteJobMutation = {
  deleteJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type DeleteProjectMutationVariables = {
  condition?: ModelProjectConditionInput | null,
  input: DeleteProjectInput,
};

export type DeleteProjectMutation = {
  deleteProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type DeleteSeedDataUploadJobMutationVariables = {
  condition?: ModelSeedDataUploadJobConditionInput | null,
  input: DeleteSeedDataUploadJobInput,
};

export type DeleteSeedDataUploadJobMutation = {
  deleteSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type DeleteSeedDatapointMutationVariables = {
  condition?: ModelSeedDatapointConditionInput | null,
  input: DeleteSeedDatapointInput,
};

export type DeleteSeedDatapointMutation = {
  deleteSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type DeleteUserMutationVariables = {
  condition?: ModelUserConditionInput | null,
  input: DeleteUserInput,
};

export type DeleteUserMutation = {
  deleteUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};

export type UpdateDatapointMutationVariables = {
  condition?: ModelDatapointConditionInput | null,
  input: UpdateDatapointInput,
};

export type UpdateDatapointMutation = {
  updateDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type UpdateExportJobMutationVariables = {
  condition?: ModelExportJobConditionInput | null,
  input: UpdateExportJobInput,
};

export type UpdateExportJobMutation = {
  updateExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type UpdateFinetuneJobMutationVariables = {
  condition?: ModelFinetuneJobConditionInput | null,
  input: UpdateFinetuneJobInput,
};

export type UpdateFinetuneJobMutation = {
  updateFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type UpdateJobMutationVariables = {
  condition?: ModelJobConditionInput | null,
  input: UpdateJobInput,
};

export type UpdateJobMutation = {
  updateJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type UpdateProjectMutationVariables = {
  condition?: ModelProjectConditionInput | null,
  input: UpdateProjectInput,
};

export type UpdateProjectMutation = {
  updateProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type UpdateSeedDataUploadJobMutationVariables = {
  condition?: ModelSeedDataUploadJobConditionInput | null,
  input: UpdateSeedDataUploadJobInput,
};

export type UpdateSeedDataUploadJobMutation = {
  updateSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type UpdateSeedDatapointMutationVariables = {
  condition?: ModelSeedDatapointConditionInput | null,
  input: UpdateSeedDatapointInput,
};

export type UpdateSeedDatapointMutation = {
  updateSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type UpdateUserMutationVariables = {
  condition?: ModelUserConditionInput | null,
  input: UpdateUserInput,
};

export type UpdateUserMutation = {
  updateUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};

export type OnCreateDatapointSubscriptionVariables = {
  filter?: ModelSubscriptionDatapointFilterInput | null,
};

export type OnCreateDatapointSubscription = {
  onCreateDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type OnCreateExportJobSubscriptionVariables = {
  filter?: ModelSubscriptionExportJobFilterInput | null,
};

export type OnCreateExportJobSubscription = {
  onCreateExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type OnCreateFinetuneJobSubscriptionVariables = {
  filter?: ModelSubscriptionFinetuneJobFilterInput | null,
};

export type OnCreateFinetuneJobSubscription = {
  onCreateFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type OnCreateJobSubscriptionVariables = {
  filter?: ModelSubscriptionJobFilterInput | null,
};

export type OnCreateJobSubscription = {
  onCreateJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type OnCreateProjectSubscriptionVariables = {
  filter?: ModelSubscriptionProjectFilterInput | null,
};

export type OnCreateProjectSubscription = {
  onCreateProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type OnCreateSeedDataUploadJobSubscriptionVariables = {
  filter?: ModelSubscriptionSeedDataUploadJobFilterInput | null,
};

export type OnCreateSeedDataUploadJobSubscription = {
  onCreateSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type OnCreateSeedDatapointSubscriptionVariables = {
  filter?: ModelSubscriptionSeedDatapointFilterInput | null,
};

export type OnCreateSeedDatapointSubscription = {
  onCreateSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type OnCreateUserSubscriptionVariables = {
  filter?: ModelSubscriptionUserFilterInput | null,
};

export type OnCreateUserSubscription = {
  onCreateUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};

export type OnDeleteDatapointSubscriptionVariables = {
  filter?: ModelSubscriptionDatapointFilterInput | null,
};

export type OnDeleteDatapointSubscription = {
  onDeleteDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type OnDeleteExportJobSubscriptionVariables = {
  filter?: ModelSubscriptionExportJobFilterInput | null,
};

export type OnDeleteExportJobSubscription = {
  onDeleteExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type OnDeleteFinetuneJobSubscriptionVariables = {
  filter?: ModelSubscriptionFinetuneJobFilterInput | null,
};

export type OnDeleteFinetuneJobSubscription = {
  onDeleteFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type OnDeleteJobSubscriptionVariables = {
  filter?: ModelSubscriptionJobFilterInput | null,
};

export type OnDeleteJobSubscription = {
  onDeleteJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type OnDeleteProjectSubscriptionVariables = {
  filter?: ModelSubscriptionProjectFilterInput | null,
};

export type OnDeleteProjectSubscription = {
  onDeleteProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type OnDeleteSeedDataUploadJobSubscriptionVariables = {
  filter?: ModelSubscriptionSeedDataUploadJobFilterInput | null,
};

export type OnDeleteSeedDataUploadJobSubscription = {
  onDeleteSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type OnDeleteSeedDatapointSubscriptionVariables = {
  filter?: ModelSubscriptionSeedDatapointFilterInput | null,
};

export type OnDeleteSeedDatapointSubscription = {
  onDeleteSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type OnDeleteUserSubscriptionVariables = {
  filter?: ModelSubscriptionUserFilterInput | null,
};

export type OnDeleteUserSubscription = {
  onDeleteUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};

export type OnUpdateDatapointSubscriptionVariables = {
  filter?: ModelSubscriptionDatapointFilterInput | null,
};

export type OnUpdateDatapointSubscription = {
  onUpdateDatapoint?:  {
    __typename: "Datapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    type?: DatapointType | null,
    updatedAt: string,
    version?: number | null,
  } | null,
};

export type OnUpdateExportJobSubscriptionVariables = {
  filter?: ModelSubscriptionExportJobFilterInput | null,
};

export type OnUpdateExportJobSubscription = {
  onUpdateExportJob?:  {
    __typename: "ExportJob",
    apiKey?: string | null,
    createdAt: string,
    datasetUrl?: string | null,
    events?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: ExportJobStatus | null,
    type?: ExportJobType | null,
    updatedAt: string,
  } | null,
};

export type OnUpdateFinetuneJobSubscriptionVariables = {
  filter?: ModelSubscriptionFinetuneJobFilterInput | null,
};

export type OnUpdateFinetuneJobSubscription = {
  onUpdateFinetuneJob?:  {
    __typename: "FinetuneJob",
    apiKey?: string | null,
    createdAt: string,
    events?: string | null,
    finetunedModel?: string | null,
    id: string,
    jobIdentifier?: string | null,
    model?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: FinetuneJobStatus | null,
    trainingFileId?: string | null,
    trainingFileName?: string | null,
    type?: FinetuneJobType | null,
    updatedAt: string,
  } | null,
};

export type OnUpdateJobSubscriptionVariables = {
  filter?: ModelSubscriptionJobFilterInput | null,
};

export type OnUpdateJobSubscription = {
  onUpdateJob?:  {
    __typename: "Job",
    config?: string | null,
    createdAt: string,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: JobStatus | null,
    type?: JobType | null,
    updatedAt: string,
  } | null,
};

export type OnUpdateProjectSubscriptionVariables = {
  filter?: ModelSubscriptionProjectFilterInput | null,
};

export type OnUpdateProjectSubscription = {
  onUpdateProject?:  {
    __typename: "Project",
    createdAt: string,
    datapoints?:  {
      __typename: "ModelDatapointConnection",
      nextToken?: string | null,
    } | null,
    description?: string | null,
    exportJobs?:  {
      __typename: "ModelExportJobConnection",
      nextToken?: string | null,
    } | null,
    finetuneJobs?:  {
      __typename: "ModelFinetuneJobConnection",
      nextToken?: string | null,
    } | null,
    id: string,
    jobs?:  {
      __typename: "ModelJobConnection",
      nextToken?: string | null,
    } | null,
    latestDatasetVersion?: number | null,
    latestSeedFile?: string | null,
    name?: string | null,
    seedDataUploadJobs?:  {
      __typename: "ModelSeedDataUploadJobConnection",
      nextToken?: string | null,
    } | null,
    seedDatapoints?:  {
      __typename: "ModelSeedDatapointConnection",
      nextToken?: string | null,
    } | null,
    updatedAt: string,
    user?:  {
      __typename: "User",
      createdAt: string,
      email: string,
      id: string,
      name: string,
      role?: string | null,
      updatedAt: string,
    } | null,
    userId?: string | null,
  } | null,
};

export type OnUpdateSeedDataUploadJobSubscriptionVariables = {
  filter?: ModelSubscriptionSeedDataUploadJobFilterInput | null,
};

export type OnUpdateSeedDataUploadJobSubscription = {
  onUpdateSeedDataUploadJob?:  {
    __typename: "SeedDataUploadJob",
    createdAt: string,
    fileName?: string | null,
    id: string,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    status?: SeedDataUploadJobStatus | null,
    updatedAt: string,
  } | null,
};

export type OnUpdateSeedDatapointSubscriptionVariables = {
  filter?: ModelSubscriptionSeedDatapointFilterInput | null,
};

export type OnUpdateSeedDatapointSubscription = {
  onUpdateSeedDatapoint?:  {
    __typename: "SeedDatapoint",
    cleaningTags?: string | null,
    createdAt: string,
    data?: string | null,
    evaluationTags?: string | null,
    feedbackTags?: string | null,
    generationTags?: string | null,
    id: string,
    name?: string | null,
    project?:  {
      __typename: "Project",
      createdAt: string,
      description?: string | null,
      id: string,
      latestDatasetVersion?: number | null,
      latestSeedFile?: string | null,
      name?: string | null,
      updatedAt: string,
      userId?: string | null,
    } | null,
    projectId?: string | null,
    seedDataFile?: string | null,
    type?: SeedDatapointType | null,
    updatedAt: string,
  } | null,
};

export type OnUpdateUserSubscriptionVariables = {
  filter?: ModelSubscriptionUserFilterInput | null,
};

export type OnUpdateUserSubscription = {
  onUpdateUser?:  {
    __typename: "User",
    createdAt: string,
    email: string,
    id: string,
    name: string,
    projects?:  {
      __typename: "ModelProjectConnection",
      nextToken?: string | null,
    } | null,
    role?: string | null,
    updatedAt: string,
  } | null,
};
