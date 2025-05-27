/* tslint:disable */
/* eslint-disable */
// this is an auto generated file. This will be overwritten

import * as APITypes from "./API";
type GeneratedQuery<InputType, OutputType> = string & {
  __generatedQueryInput: InputType;
  __generatedQueryOutput: OutputType;
};

export const getDatapoint = /* GraphQL */ `query GetDatapoint($id: ID!) {
  getDatapoint(id: $id) {
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
` as GeneratedQuery<
  APITypes.GetDatapointQueryVariables,
  APITypes.GetDatapointQuery
>;
export const getExportJob = /* GraphQL */ `query GetExportJob($id: ID!) {
  getExportJob(id: $id) {
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
` as GeneratedQuery<
  APITypes.GetExportJobQueryVariables,
  APITypes.GetExportJobQuery
>;
export const getFinetuneJob = /* GraphQL */ `query GetFinetuneJob($id: ID!) {
  getFinetuneJob(id: $id) {
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
` as GeneratedQuery<
  APITypes.GetFinetuneJobQueryVariables,
  APITypes.GetFinetuneJobQuery
>;
export const getJob = /* GraphQL */ `query GetJob($id: ID!) {
  getJob(id: $id) {
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
` as GeneratedQuery<APITypes.GetJobQueryVariables, APITypes.GetJobQuery>;
export const getProject = /* GraphQL */ `query GetProject($id: ID!) {
  getProject(id: $id) {
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
` as GeneratedQuery<
  APITypes.GetProjectQueryVariables,
  APITypes.GetProjectQuery
>;
export const getSeedDataUploadJob = /* GraphQL */ `query GetSeedDataUploadJob($id: ID!) {
  getSeedDataUploadJob(id: $id) {
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
` as GeneratedQuery<
  APITypes.GetSeedDataUploadJobQueryVariables,
  APITypes.GetSeedDataUploadJobQuery
>;
export const getSeedDatapoint = /* GraphQL */ `query GetSeedDatapoint($id: ID!) {
  getSeedDatapoint(id: $id) {
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
` as GeneratedQuery<
  APITypes.GetSeedDatapointQueryVariables,
  APITypes.GetSeedDatapointQuery
>;
export const getUser = /* GraphQL */ `query GetUser($id: ID!) {
  getUser(id: $id) {
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
` as GeneratedQuery<APITypes.GetUserQueryVariables, APITypes.GetUserQuery>;
export const listDatapoints = /* GraphQL */ `query ListDatapoints(
  $filter: ModelDatapointFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listDatapoints(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      cleaningTags
      createdAt
      data
      evaluationTags
      feedbackTags
      generationTags
      id
      name
      projectId
      type
      updatedAt
      version
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<
  APITypes.ListDatapointsQueryVariables,
  APITypes.ListDatapointsQuery
>;
export const listExportJobs = /* GraphQL */ `query ListExportJobs(
  $filter: ModelExportJobFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listExportJobs(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      apiKey
      createdAt
      datasetUrl
      events
      id
      projectId
      status
      type
      updatedAt
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<
  APITypes.ListExportJobsQueryVariables,
  APITypes.ListExportJobsQuery
>;
export const listFinetuneJobs = /* GraphQL */ `query ListFinetuneJobs(
  $filter: ModelFinetuneJobFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listFinetuneJobs(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      apiKey
      createdAt
      events
      finetunedModel
      id
      jobIdentifier
      model
      projectId
      status
      trainingFileId
      trainingFileName
      type
      updatedAt
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<
  APITypes.ListFinetuneJobsQueryVariables,
  APITypes.ListFinetuneJobsQuery
>;
export const listJobs = /* GraphQL */ `query ListJobs(
  $filter: ModelJobFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listJobs(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      config
      createdAt
      id
      projectId
      status
      type
      updatedAt
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<APITypes.ListJobsQueryVariables, APITypes.ListJobsQuery>;
export const listProjects = /* GraphQL */ `query ListProjects(
  $filter: ModelProjectFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listProjects(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
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
    nextToken
    __typename
  }
}
` as GeneratedQuery<
  APITypes.ListProjectsQueryVariables,
  APITypes.ListProjectsQuery
>;
export const listSeedDataUploadJobs = /* GraphQL */ `query ListSeedDataUploadJobs(
  $filter: ModelSeedDataUploadJobFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listSeedDataUploadJobs(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      createdAt
      fileName
      id
      projectId
      status
      updatedAt
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<
  APITypes.ListSeedDataUploadJobsQueryVariables,
  APITypes.ListSeedDataUploadJobsQuery
>;
export const listSeedDatapoints = /* GraphQL */ `query ListSeedDatapoints(
  $filter: ModelSeedDatapointFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listSeedDatapoints(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      cleaningTags
      createdAt
      data
      evaluationTags
      feedbackTags
      generationTags
      id
      name
      projectId
      seedDataFile
      type
      updatedAt
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<
  APITypes.ListSeedDatapointsQueryVariables,
  APITypes.ListSeedDatapointsQuery
>;
export const listUsers = /* GraphQL */ `query ListUsers(
  $filter: ModelUserFilterInput
  $id: ID
  $limit: Int
  $nextToken: String
  $sortDirection: ModelSortDirection
) {
  listUsers(
    filter: $filter
    id: $id
    limit: $limit
    nextToken: $nextToken
    sortDirection: $sortDirection
  ) {
    items {
      createdAt
      email
      id
      name
      role
      updatedAt
      __typename
    }
    nextToken
    __typename
  }
}
` as GeneratedQuery<APITypes.ListUsersQueryVariables, APITypes.ListUsersQuery>;
