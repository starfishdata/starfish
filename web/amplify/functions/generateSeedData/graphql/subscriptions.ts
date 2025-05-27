/* tslint:disable */
/* eslint-disable */
// this is an auto generated file. This will be overwritten

import * as APITypes from "./API";
type GeneratedSubscription<InputType, OutputType> = string & {
  __generatedSubscriptionInput: InputType;
  __generatedSubscriptionOutput: OutputType;
};

export const onCreateDatapoint = /* GraphQL */ `subscription OnCreateDatapoint($filter: ModelSubscriptionDatapointFilterInput) {
  onCreateDatapoint(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateDatapointSubscriptionVariables,
  APITypes.OnCreateDatapointSubscription
>;
export const onCreateExportJob = /* GraphQL */ `subscription OnCreateExportJob($filter: ModelSubscriptionExportJobFilterInput) {
  onCreateExportJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateExportJobSubscriptionVariables,
  APITypes.OnCreateExportJobSubscription
>;
export const onCreateFinetuneJob = /* GraphQL */ `subscription OnCreateFinetuneJob(
  $filter: ModelSubscriptionFinetuneJobFilterInput
) {
  onCreateFinetuneJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateFinetuneJobSubscriptionVariables,
  APITypes.OnCreateFinetuneJobSubscription
>;
export const onCreateJob = /* GraphQL */ `subscription OnCreateJob($filter: ModelSubscriptionJobFilterInput) {
  onCreateJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateJobSubscriptionVariables,
  APITypes.OnCreateJobSubscription
>;
export const onCreateProject = /* GraphQL */ `subscription OnCreateProject($filter: ModelSubscriptionProjectFilterInput) {
  onCreateProject(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateProjectSubscriptionVariables,
  APITypes.OnCreateProjectSubscription
>;
export const onCreateSeedDataUploadJob = /* GraphQL */ `subscription OnCreateSeedDataUploadJob(
  $filter: ModelSubscriptionSeedDataUploadJobFilterInput
) {
  onCreateSeedDataUploadJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateSeedDataUploadJobSubscriptionVariables,
  APITypes.OnCreateSeedDataUploadJobSubscription
>;
export const onCreateSeedDatapoint = /* GraphQL */ `subscription OnCreateSeedDatapoint(
  $filter: ModelSubscriptionSeedDatapointFilterInput
) {
  onCreateSeedDatapoint(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateSeedDatapointSubscriptionVariables,
  APITypes.OnCreateSeedDatapointSubscription
>;
export const onCreateUser = /* GraphQL */ `subscription OnCreateUser($filter: ModelSubscriptionUserFilterInput) {
  onCreateUser(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnCreateUserSubscriptionVariables,
  APITypes.OnCreateUserSubscription
>;
export const onDeleteDatapoint = /* GraphQL */ `subscription OnDeleteDatapoint($filter: ModelSubscriptionDatapointFilterInput) {
  onDeleteDatapoint(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteDatapointSubscriptionVariables,
  APITypes.OnDeleteDatapointSubscription
>;
export const onDeleteExportJob = /* GraphQL */ `subscription OnDeleteExportJob($filter: ModelSubscriptionExportJobFilterInput) {
  onDeleteExportJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteExportJobSubscriptionVariables,
  APITypes.OnDeleteExportJobSubscription
>;
export const onDeleteFinetuneJob = /* GraphQL */ `subscription OnDeleteFinetuneJob(
  $filter: ModelSubscriptionFinetuneJobFilterInput
) {
  onDeleteFinetuneJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteFinetuneJobSubscriptionVariables,
  APITypes.OnDeleteFinetuneJobSubscription
>;
export const onDeleteJob = /* GraphQL */ `subscription OnDeleteJob($filter: ModelSubscriptionJobFilterInput) {
  onDeleteJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteJobSubscriptionVariables,
  APITypes.OnDeleteJobSubscription
>;
export const onDeleteProject = /* GraphQL */ `subscription OnDeleteProject($filter: ModelSubscriptionProjectFilterInput) {
  onDeleteProject(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteProjectSubscriptionVariables,
  APITypes.OnDeleteProjectSubscription
>;
export const onDeleteSeedDataUploadJob = /* GraphQL */ `subscription OnDeleteSeedDataUploadJob(
  $filter: ModelSubscriptionSeedDataUploadJobFilterInput
) {
  onDeleteSeedDataUploadJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteSeedDataUploadJobSubscriptionVariables,
  APITypes.OnDeleteSeedDataUploadJobSubscription
>;
export const onDeleteSeedDatapoint = /* GraphQL */ `subscription OnDeleteSeedDatapoint(
  $filter: ModelSubscriptionSeedDatapointFilterInput
) {
  onDeleteSeedDatapoint(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteSeedDatapointSubscriptionVariables,
  APITypes.OnDeleteSeedDatapointSubscription
>;
export const onDeleteUser = /* GraphQL */ `subscription OnDeleteUser($filter: ModelSubscriptionUserFilterInput) {
  onDeleteUser(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnDeleteUserSubscriptionVariables,
  APITypes.OnDeleteUserSubscription
>;
export const onUpdateDatapoint = /* GraphQL */ `subscription OnUpdateDatapoint($filter: ModelSubscriptionDatapointFilterInput) {
  onUpdateDatapoint(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateDatapointSubscriptionVariables,
  APITypes.OnUpdateDatapointSubscription
>;
export const onUpdateExportJob = /* GraphQL */ `subscription OnUpdateExportJob($filter: ModelSubscriptionExportJobFilterInput) {
  onUpdateExportJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateExportJobSubscriptionVariables,
  APITypes.OnUpdateExportJobSubscription
>;
export const onUpdateFinetuneJob = /* GraphQL */ `subscription OnUpdateFinetuneJob(
  $filter: ModelSubscriptionFinetuneJobFilterInput
) {
  onUpdateFinetuneJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateFinetuneJobSubscriptionVariables,
  APITypes.OnUpdateFinetuneJobSubscription
>;
export const onUpdateJob = /* GraphQL */ `subscription OnUpdateJob($filter: ModelSubscriptionJobFilterInput) {
  onUpdateJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateJobSubscriptionVariables,
  APITypes.OnUpdateJobSubscription
>;
export const onUpdateProject = /* GraphQL */ `subscription OnUpdateProject($filter: ModelSubscriptionProjectFilterInput) {
  onUpdateProject(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateProjectSubscriptionVariables,
  APITypes.OnUpdateProjectSubscription
>;
export const onUpdateSeedDataUploadJob = /* GraphQL */ `subscription OnUpdateSeedDataUploadJob(
  $filter: ModelSubscriptionSeedDataUploadJobFilterInput
) {
  onUpdateSeedDataUploadJob(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateSeedDataUploadJobSubscriptionVariables,
  APITypes.OnUpdateSeedDataUploadJobSubscription
>;
export const onUpdateSeedDatapoint = /* GraphQL */ `subscription OnUpdateSeedDatapoint(
  $filter: ModelSubscriptionSeedDatapointFilterInput
) {
  onUpdateSeedDatapoint(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateSeedDatapointSubscriptionVariables,
  APITypes.OnUpdateSeedDatapointSubscription
>;
export const onUpdateUser = /* GraphQL */ `subscription OnUpdateUser($filter: ModelSubscriptionUserFilterInput) {
  onUpdateUser(filter: $filter) {
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
` as GeneratedSubscription<
  APITypes.OnUpdateUserSubscriptionVariables,
  APITypes.OnUpdateUserSubscription
>;
