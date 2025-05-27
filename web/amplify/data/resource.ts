import { a, defineData, type ClientSchema } from '@aws-amplify/backend';
import { generateSeedData } from '../functions/generateSeedData/resource';
import { myApiFunction } from '../functions/api-functions/resource';
import { apiKeyManager } from '../functions/api-key-manager/resource';

const schema = a.schema({
    User: a.model({
      id: a.id(),
      name: a.string().required(),
      email: a.email().required(),
      role: a.string(),
      projects: a.hasMany('Project', 'userId'),
      apiKeys: a.hasMany('ApiKeys', 'userId'),
    })
    .authorization(allow => [allow.publicApiKey()]),
    
    Project: a.model({
      id: a.id(),
      userId: a.id(),
      user: a.belongsTo('User', 'userId'),
      name: a.string(),
      description: a.string(),
      datapoints: a.hasMany('Datapoint', 'projectId'),
      seedDatapoints: a.hasMany('SeedDatapoint', 'projectId'),
      finetuneJobs: a.hasMany('FinetuneJob', 'projectId'),
      exportJobs: a.hasMany('ExportJob', 'projectId'),
      jobs: a.hasMany('Job', 'projectId'),
      seedDataUploadJobs: a.hasMany('SeedDataUploadJob', 'projectId'),
      latestSeedFile: a.string(),
      latestDatasetVersion: a.integer(),
    })
    .authorization(allow => [allow.publicApiKey()]),

    Datapoint: a.model({
      id: a.id(),
      projectId: a.id(),
      project: a.belongsTo('Project', 'projectId'),
      name: a.string(),
      type: a.enum(['SYNTHETIC']),
      data: a.json(),
      evaluationTags: a.json(),
      generationTags: a.json(),
      feedbackTags: a.json(),
      cleaningTags: a.json(),
      version: a.integer(),
      topic: a.string(),
      jobId: a.string(),
      adherenceScore: a.float(),
      accuracyScore: a.float(),
      qualityScore: a.float(),
      generationJobTopicId: a.id(), 
      liked: a.integer().default(0)
    })
    .secondaryIndexes((index) => [index('version').sortKeys(['qualityScore', 'accuracyScore', 'adherenceScore']), index('projectId').sortKeys(['version'])])
    .authorization(allow => [allow.publicApiKey()]),

    SeedDatapoint: a.model({
      id: a.id(),
      projectId: a.id(),
      project: a.belongsTo('Project', 'projectId'),
      name: a.string(),
      type: a.enum(['SEED']),
      data: a.json(),
      evaluationTags: a.json(),
      generationTags: a.json(),
      feedbackTags: a.json(),
      cleaningTags: a.json(),
      seedDataFile: a.string()
    })
    .authorization(allow => [allow.publicApiKey()]),
  
    Job: a.model({
      id: a.id(),
      projectId: a.id(),
      project: a.belongsTo('Project', 'projectId'),
      type: a.enum(['GENERATION', 'EVALUATION', 'CLEANING', 'USER_FEEDBACK']),
      config: a.json(),
      status: a.enum(['RUNNING', 'COMPLETE', 'NOT_STARTED', 'COMPLETE_WITH_ERROR', 'ERROR']),
      useSeedData: a.boolean(),
      requestedRecords: a.integer(),
      completedRecords: a.integer(),
      duplicateRecords: a.integer(),
      failedRecords: a.integer(),
      totalSqsMessagesSent: a.integer(),
      generationJobTopics: a.hasMany('GenerationJobTopic', 'jobId'),
      model: a.string(),
      userPrompt: a.string(),
      inputNumOfRecords: a.string(),
      averageQualityScore: a.float(),
      version: a.integer()
    })
    .secondaryIndexes((index) => [index('projectId'), index('projectId').sortKeys(['version', 'type'])])
    .authorization(allow => [allow.publicApiKey()]),

    GenerationJobTopic: a.model({
      id: a.id(),
      jobId: a.id(),
      job: a.belongsTo('Job', 'jobId'),
      topic: a.string(),
      status: a.enum(['RUNNING', 'COMPLETE', 'NOT_STARTED', 'COMPLETE_WITH_ERROR', 'ERROR']),
      config: a.json(),
      requestedRecords: a.integer(),
      completedRecords: a.integer(),
      duplicateRecords: a.integer(),
    }).authorization(allow => [allow.publicApiKey()]),

    SeedDataUploadJob: a.model({
      id: a.id(),
      projectId: a.id(),
      project: a.belongsTo('Project', 'projectId'),
      status: a.enum(['STARTING', 'RUNNING', 'COMPLETE', 'FAILED']),
      fileName: a.string()
    })
    .authorization(allow => [allow.publicApiKey()]),

    FinetuneJob: a.model({
      id: a.id(),
      projectId: a.id(),
      project: a.belongsTo('Project', 'projectId'),
      apiKey: a.string(),
      events: a.json(),
      trainingFileName: a.string(),
      trainingFileId: a.string(),
      model: a.string(),
      type: a.enum(['OPENAI']),
      jobIdentifier: a.string(),
      status: a.enum(['RUNNING', 'COMPLETE', 'NOT_STARTED', 'FAILED', 'STARTED']),
      finetunedModel: a.string()
    })
    .authorization(allow => [allow.publicApiKey()]),

    ExportJob: a.model({
      id: a.id(),
      projectId: a.id(),
      project: a.belongsTo('Project', 'projectId'),
      apiKey: a.string(),
      events: a.json(),
      type: a.enum(['HUGGINGFACE']),
      status: a.enum(['RUNNING', 'COMPLETE','FAILED']),
      datasetUrl: a.string()
    })
    .authorization(allow => [allow.publicApiKey()]),

    ApiKeys: a.model({
      id: a.id(),
      apiKey: a.string(),
      userId: a.id(),
      user: a.belongsTo('User', 'userId'),
      usagePlanId: a.string(),
      apiGatewayKeyId: a.string()
    })
    .secondaryIndexes((index) => [index('apiKey'), index('apiGatewayKeyId')])
    .authorization(allow => [allow.publicApiKey()]),
})
.authorization(allow => [allow.resource(generateSeedData), allow.resource(myApiFunction), allow.resource(apiKeyManager)]);
// Used for code completion / highlighting when making requests from frontend
export type Schema = ClientSchema<typeof schema>;

// defines the data resource to be deployed
export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'apiKey',
    apiKeyAuthorizationMode: { expiresInDays: 30 }
  }
});