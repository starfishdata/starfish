/* tslint:disable */
/* eslint-disable */
// this is an auto generated file. This will be overwritten

import * as APITypes from "./API";
type GeneratedMutation<InputType, OutputType> = string & {
  __generatedMutationInput: InputType;
  __generatedMutationOutput: OutputType;
};

export const createDatapoint = /* GraphQL */ `mutation CreateDatapoint(
  $condition: ModelDatapointConditionInput
  $input: CreateDatapointInput!
) {
  createDatapoint(condition: $condition, input: $input) {
    cleaningTags
    createdAt
    data
    evaluationTags
    feedbackTags
    generationTags
    id
    name
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    type
    updatedAt
    version
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateDatapointMutationVariables,
  APITypes.CreateDatapointMutation
>;
export const createExportJob = /* GraphQL */ `mutation CreateExportJob(
  $condition: ModelExportJobConditionInput
  $input: CreateExportJobInput!
) {
  createExportJob(condition: $condition, input: $input) {
    apiKey
    createdAt
    datasetUrl
    events
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateExportJobMutationVariables,
  APITypes.CreateExportJobMutation
>;
export const createFinetuneJob = /* GraphQL */ `mutation CreateFinetuneJob(
  $condition: ModelFinetuneJobConditionInput
  $input: CreateFinetuneJobInput!
) {
  createFinetuneJob(condition: $condition, input: $input) {
    apiKey
    createdAt
    events
    finetunedModel
    id
    jobIdentifier
    model
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    trainingFileId
    trainingFileName
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateFinetuneJobMutationVariables,
  APITypes.CreateFinetuneJobMutation
>;
export const createJob = /* GraphQL */ `mutation CreateJob(
  $condition: ModelJobConditionInput
  $input: CreateJobInput!
) {
  createJob(condition: $condition, input: $input) {
    config
    createdAt
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateJobMutationVariables,
  APITypes.CreateJobMutation
>;
export const createProject = /* GraphQL */ `mutation CreateProject(
  $condition: ModelProjectConditionInput
  $input: CreateProjectInput!
) {
  createProject(condition: $condition, input: $input) {
    createdAt
    datapoints {
      nextToken
      __typename
    }
    description
    exportJobs {
      nextToken
      __typename
    }
    finetuneJobs {
      nextToken
      __typename
    }
    id
    jobs {
      nextToken
      __typename
    }
    latestDatasetVersion
    latestSeedFile
    name
    seedDataUploadJobs {
      nextToken
      __typename
    }
    seedDatapoints {
      nextToken
      __typename
    }
    updatedAt
    user {
      createdAt
      email
      id
      name
      role
      updatedAt
      __typename
    }
    userId
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateProjectMutationVariables,
  APITypes.CreateProjectMutation
>;
export const createSeedDataUploadJob = /* GraphQL */ `mutation CreateSeedDataUploadJob(
  $condition: ModelSeedDataUploadJobConditionInput
  $input: CreateSeedDataUploadJobInput!
) {
  createSeedDataUploadJob(condition: $condition, input: $input) {
    createdAt
    fileName
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateSeedDataUploadJobMutationVariables,
  APITypes.CreateSeedDataUploadJobMutation
>;
export const createSeedDatapoint = /* GraphQL */ `mutation CreateSeedDatapoint(
  $condition: ModelSeedDatapointConditionInput
  $input: CreateSeedDatapointInput!
) {
  createSeedDatapoint(condition: $condition, input: $input) {
    cleaningTags
    createdAt
    data
    evaluationTags
    feedbackTags
    generationTags
    id
    name
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    seedDataFile
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateSeedDatapointMutationVariables,
  APITypes.CreateSeedDatapointMutation
>;
export const createUser = /* GraphQL */ `mutation CreateUser(
  $condition: ModelUserConditionInput
  $input: CreateUserInput!
) {
  createUser(condition: $condition, input: $input) {
    createdAt
    email
    id
    name
    projects {
      nextToken
      __typename
    }
    role
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.CreateUserMutationVariables,
  APITypes.CreateUserMutation
>;
export const deleteDatapoint = /* GraphQL */ `mutation DeleteDatapoint(
  $condition: ModelDatapointConditionInput
  $input: DeleteDatapointInput!
) {
  deleteDatapoint(condition: $condition, input: $input) {
    cleaningTags
    createdAt
    data
    evaluationTags
    feedbackTags
    generationTags
    id
    name
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    type
    updatedAt
    version
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteDatapointMutationVariables,
  APITypes.DeleteDatapointMutation
>;
export const deleteExportJob = /* GraphQL */ `mutation DeleteExportJob(
  $condition: ModelExportJobConditionInput
  $input: DeleteExportJobInput!
) {
  deleteExportJob(condition: $condition, input: $input) {
    apiKey
    createdAt
    datasetUrl
    events
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteExportJobMutationVariables,
  APITypes.DeleteExportJobMutation
>;
export const deleteFinetuneJob = /* GraphQL */ `mutation DeleteFinetuneJob(
  $condition: ModelFinetuneJobConditionInput
  $input: DeleteFinetuneJobInput!
) {
  deleteFinetuneJob(condition: $condition, input: $input) {
    apiKey
    createdAt
    events
    finetunedModel
    id
    jobIdentifier
    model
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    trainingFileId
    trainingFileName
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteFinetuneJobMutationVariables,
  APITypes.DeleteFinetuneJobMutation
>;
export const deleteJob = /* GraphQL */ `mutation DeleteJob(
  $condition: ModelJobConditionInput
  $input: DeleteJobInput!
) {
  deleteJob(condition: $condition, input: $input) {
    config
    createdAt
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteJobMutationVariables,
  APITypes.DeleteJobMutation
>;
export const deleteProject = /* GraphQL */ `mutation DeleteProject(
  $condition: ModelProjectConditionInput
  $input: DeleteProjectInput!
) {
  deleteProject(condition: $condition, input: $input) {
    createdAt
    datapoints {
      nextToken
      __typename
    }
    description
    exportJobs {
      nextToken
      __typename
    }
    finetuneJobs {
      nextToken
      __typename
    }
    id
    jobs {
      nextToken
      __typename
    }
    latestDatasetVersion
    latestSeedFile
    name
    seedDataUploadJobs {
      nextToken
      __typename
    }
    seedDatapoints {
      nextToken
      __typename
    }
    updatedAt
    user {
      createdAt
      email
      id
      name
      role
      updatedAt
      __typename
    }
    userId
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteProjectMutationVariables,
  APITypes.DeleteProjectMutation
>;
export const deleteSeedDataUploadJob = /* GraphQL */ `mutation DeleteSeedDataUploadJob(
  $condition: ModelSeedDataUploadJobConditionInput
  $input: DeleteSeedDataUploadJobInput!
) {
  deleteSeedDataUploadJob(condition: $condition, input: $input) {
    createdAt
    fileName
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteSeedDataUploadJobMutationVariables,
  APITypes.DeleteSeedDataUploadJobMutation
>;
export const deleteSeedDatapoint = /* GraphQL */ `mutation DeleteSeedDatapoint(
  $condition: ModelSeedDatapointConditionInput
  $input: DeleteSeedDatapointInput!
) {
  deleteSeedDatapoint(condition: $condition, input: $input) {
    cleaningTags
    createdAt
    data
    evaluationTags
    feedbackTags
    generationTags
    id
    name
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    seedDataFile
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteSeedDatapointMutationVariables,
  APITypes.DeleteSeedDatapointMutation
>;
export const deleteUser = /* GraphQL */ `mutation DeleteUser(
  $condition: ModelUserConditionInput
  $input: DeleteUserInput!
) {
  deleteUser(condition: $condition, input: $input) {
    createdAt
    email
    id
    name
    projects {
      nextToken
      __typename
    }
    role
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.DeleteUserMutationVariables,
  APITypes.DeleteUserMutation
>;
export const updateDatapoint = /* GraphQL */ `mutation UpdateDatapoint(
  $condition: ModelDatapointConditionInput
  $input: UpdateDatapointInput!
) {
  updateDatapoint(condition: $condition, input: $input) {
    cleaningTags
    createdAt
    data
    evaluationTags
    feedbackTags
    generationTags
    id
    name
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    type
    updatedAt
    version
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateDatapointMutationVariables,
  APITypes.UpdateDatapointMutation
>;
export const updateExportJob = /* GraphQL */ `mutation UpdateExportJob(
  $condition: ModelExportJobConditionInput
  $input: UpdateExportJobInput!
) {
  updateExportJob(condition: $condition, input: $input) {
    apiKey
    createdAt
    datasetUrl
    events
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateExportJobMutationVariables,
  APITypes.UpdateExportJobMutation
>;
export const updateFinetuneJob = /* GraphQL */ `mutation UpdateFinetuneJob(
  $condition: ModelFinetuneJobConditionInput
  $input: UpdateFinetuneJobInput!
) {
  updateFinetuneJob(condition: $condition, input: $input) {
    apiKey
    createdAt
    events
    finetunedModel
    id
    jobIdentifier
    model
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    trainingFileId
    trainingFileName
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateFinetuneJobMutationVariables,
  APITypes.UpdateFinetuneJobMutation
>;
export const updateJob = /* GraphQL */ `mutation UpdateJob(
  $condition: ModelJobConditionInput
  $input: UpdateJobInput!
) {
  updateJob(condition: $condition, input: $input) {
    config
    createdAt
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateJobMutationVariables,
  APITypes.UpdateJobMutation
>;
export const updateProject = /* GraphQL */ `mutation UpdateProject(
  $condition: ModelProjectConditionInput
  $input: UpdateProjectInput!
) {
  updateProject(condition: $condition, input: $input) {
    createdAt
    datapoints {
      nextToken
      __typename
    }
    description
    exportJobs {
      nextToken
      __typename
    }
    finetuneJobs {
      nextToken
      __typename
    }
    id
    jobs {
      nextToken
      __typename
    }
    latestDatasetVersion
    latestSeedFile
    name
    seedDataUploadJobs {
      nextToken
      __typename
    }
    seedDatapoints {
      nextToken
      __typename
    }
    updatedAt
    user {
      createdAt
      email
      id
      name
      role
      updatedAt
      __typename
    }
    userId
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateProjectMutationVariables,
  APITypes.UpdateProjectMutation
>;
export const updateSeedDataUploadJob = /* GraphQL */ `mutation UpdateSeedDataUploadJob(
  $condition: ModelSeedDataUploadJobConditionInput
  $input: UpdateSeedDataUploadJobInput!
) {
  updateSeedDataUploadJob(condition: $condition, input: $input) {
    createdAt
    fileName
    id
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    status
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateSeedDataUploadJobMutationVariables,
  APITypes.UpdateSeedDataUploadJobMutation
>;
export const updateSeedDatapoint = /* GraphQL */ `mutation UpdateSeedDatapoint(
  $condition: ModelSeedDatapointConditionInput
  $input: UpdateSeedDatapointInput!
) {
  updateSeedDatapoint(condition: $condition, input: $input) {
    cleaningTags
    createdAt
    data
    evaluationTags
    feedbackTags
    generationTags
    id
    name
    project {
      createdAt
      description
      id
      latestDatasetVersion
      latestSeedFile
      name
      updatedAt
      userId
      __typename
    }
    projectId
    seedDataFile
    type
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateSeedDatapointMutationVariables,
  APITypes.UpdateSeedDatapointMutation
>;
export const updateUser = /* GraphQL */ `mutation UpdateUser(
  $condition: ModelUserConditionInput
  $input: UpdateUserInput!
) {
  updateUser(condition: $condition, input: $input) {
    createdAt
    email
    id
    name
    projects {
      nextToken
      __typename
    }
    role
    updatedAt
    __typename
  }
}
` as GeneratedMutation<
  APITypes.UpdateUserMutationVariables,
  APITypes.UpdateUserMutation
>;
