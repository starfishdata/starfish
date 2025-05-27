import type { APIGatewayProxyHandler } from "aws-lambda";
import { generateClient } from "aws-amplify/data";
import { Amplify } from "aws-amplify";
import { Schema } from "../../data/resource";
import { createJob, createProject, updateJob } from "../api-functions/graphql/mutations";
import { JobStatus, JobType } from "../api-functions/graphql/API";
import { env } from "$amplify/env/generateSeedData";
import { listApiKeysByApiKey, getJob, listDatapointByProjectIdAndVersion, listJobByProjectIdAndVersionAndType, getProject } from "./graphql/queries";

Amplify.configure(
    {
      API: {
        GraphQL: {
          endpoint: env.AMPLIFY_DATA_GRAPHQL_ENDPOINT,
          region: env.AWS_REGION, 
          defaultAuthMode: "iam",
        },
      },
    },
    {
      Auth: {
        credentialsProvider: {
          getCredentialsAndIdentityId: async () => ({
            credentials: {
              accessKeyId: env.AWS_ACCESS_KEY_ID,
              secretAccessKey: env.AWS_SECRET_ACCESS_KEY,
              sessionToken: env.AWS_SESSION_TOKEN,
            },
          }),
          clearCredentialsAndIdentityId: () => {
            /* noop */
          },
        },
      },
    }
  );
  
  const client = generateClient<Schema>({
    authMode: "iam",
  });


export const handler: APIGatewayProxyHandler = async (event) => {
  console.log(event)
  console.log('Starting user info fetch');  
  let output = {};
  

  try {
    if (event.path.includes('/v1/generateData')) {
        output  = await generateData(event)
    }

    if (event.path.includes('/v1/jobStatus')) {
        output  = await getJobStatus(event)
    }

    if (event.path.includes('/v1/data')) {
        output  = await fetchData(event)
    }

    if (event.path.includes('/v1/evaluateData')) {
        output  = await evaluateData(event)
    }
    
    return {
        statusCode: 200,
        // Modify the CORS settings below to match your specific requirements
        headers: {
          "Access-Control-Allow-Origin": "*", // Restrict this to domains you trust
          "Access-Control-Allow-Headers": "*", // Specify only the headers you need to allow
        },
        body: JSON.stringify(output),
      };
  } catch (error) {
    console.error('Error fetching data:', error);
    // if error message is "Unauthorized" return a 401 error
    if ((error as Error).message === 'Unauthorized') {
      return {
        statusCode: 401,
        body: JSON.stringify({ error: (error as Error).message })
      };
    }
    return {
      statusCode: 500,
      body: JSON.stringify({ error: (error as Error).message })
    };
  }
};

async function generateData(event: any) {
    const llmEndpoint = process.env.LLM || 'http://starfish-llm-dev-env.us-east-1.elasticbeanstalk.com';
    const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;

    // Verify project access
    await verifyProjectAccess(body.projectId, event.headers['x-api-key']);

    // Define allowed models
    const allowedModels = [
        'gpt-4o-2024-08-06',
        'gpt-4o-mini-2024-07-18',
        'gpt-4-turbo-2024-04-09'
    ];

    // Validate required fields
    if (!body.prompt) {
        throw new Error('prompt is required');
    }
    if (!body.numOfRecords) {
        throw new Error('numOfRecords is required'); 
    }
    if (!body.model) {    
        throw new Error('model is required'); 
    }

    // Validate model
    if (!allowedModels.includes(body.model)) {
        throw new Error(`Invalid model. Allowed models are: ${allowedModels.join(', ')}`);
    }

    // Get the user id from api key
    const apiKey = event.headers['x-api-key'];
    const apiKeyData = await client.graphql({
        query: listApiKeysByApiKey,
        variables: {
          apiKey: apiKey
        }
    });

    const userId = apiKeyData.data.listApiKeysByApiKey.items[0].userId;

    const newProject = await client.graphql({
        query: createProject,
        variables: {    
          input: {
            name: 'api request project',
            description: [body.prompt, body.numOfRecords, body.model].join('_'),
            userId: userId
          }
        }
    });

    // Rest of your existing code...
    const newJob: any = await client.graphql({
        query: createJob,
        variables: {
            input: {
                projectId: newProject.data.createProject.id,
                type: JobType.GENERATION,
                status: JobStatus.RUNNING,
                userPrompt: body.prompt,
                model: body.model,
                inputNumOfRecords: body.numOfRecords,
                requestedRecords: parseInt(body.numOfRecords),
                version: 0
            }   
        }
    });

    const apiRequest = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          accept: 'application/json',
        },
        body: JSON.stringify({
          project_id: newProject.data.createProject.id,
          job_id: newJob.data.createJob.id,
          total_num_datapoints: body.numOfRecords,
          topic_step: {},
          generation_step: {
            model_name: body.model,
            user_instruction: body.prompt,
          }
        }),
    }

    await fetch(llmEndpoint + '/api/v1/producer/generations/vanilla/invoke', apiRequest);

    const updateJobQuery = await client.graphql({
        query: updateJob,
        variables: {
          input: {
            id: newJob.data.createJob.id,
            config: JSON.stringify(apiRequest)
          }
        }
    });

    return {
        projectId: newProject.data.createProject.id,
        jobId: newJob.data?.createJob.id,
        success: true
    };
}

async function evaluateData(event: any) {
  const llmEndpoint = process.env.LLM || 'http://starfish-llm-dev-env.us-east-1.elasticbeanstalk.com';
  const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;

  if (!body?.projectId) {
      throw new Error('projectId is required');
  }

  // Verify project access
  await verifyProjectAccess(body.projectId, event.headers['x-api-key']);

  const newJob: any = await client.graphql({
      query: createJob,
      variables: {
          input: {
              projectId: body?.projectId,
              type: JobType.EVALUATION,
              status: JobStatus.RUNNING,
              version: 0
          }   
      }
  });

  const request = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      accept: 'application/json',
    },
    body: JSON.stringify({
      project_id: body?.projectId,
      job_id: newJob.data.createJob.id,
      version: 0,
      job_type: 'evaluations_vanilla',
      max_datapoints_per_run: 10
    }),
  }

  await fetch(llmEndpoint + '/api/v1/producer/evaluations/vanilla/invoke', request);

  const updateJobQuery = await client.graphql({
      query: updateJob,
      variables: {
        input: {
          id: newJob.data.createJob.id,
          config: JSON.stringify(request)
        }
      }
  });

  return {
      projectId: body?.projectId,
      jobId: newJob.data?.createJob.id,
      success: true
  };
}


async function getJobStatus(event: any) {
    const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;
    
    if (!body?.jobId) {
        throw new Error('jobId is required');
    }

    // Verify project access
    await verifyProjectAccess(body.projectId, event.headers['x-api-key']);

    try {
        const jobStatus = await client.graphql({
            query: getJob,
            variables: {
                id: body.jobId
            }
        });

        if (!jobStatus.data.getJob) {
            throw new Error('Job not found');
        }

        return {
            jobId: jobStatus.data.getJob.id,
            status: jobStatus.data.getJob.status,
            type: jobStatus.data.getJob.type,
            success: true
        };
    } catch (error) {
        console.error('Error fetching job status:', error);
        throw error;
    }
}

async function verifyProjectAccess(projectId: string, apiKey: string): Promise<void> {
    // Get the project
    const project = await client.graphql({
        query: getProject,
        variables: {
            id: projectId
        }
    });

    // Check if the project exists
    if (!project.data.getProject) {
        throw new Error('Project not found');
    }

    // Get api key
    const apiKeyData = await client.graphql({
        query: listApiKeysByApiKey,
        variables: {
            apiKey: apiKey
        }
    });

    // Check if the api key user id matches the project user id
    if (apiKeyData.data.listApiKeysByApiKey.items[0].userId !== project.data.getProject.userId) {
        throw new Error('Unauthorized');
    }
}

async function fetchData(event: any) {
    const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;

    if (!body?.projectId) {
        throw new Error('projectId is required');
    }

    // Verify project access
    await verifyProjectAccess(body.projectId, event.headers['x-api-key']);

    try {
        // Create base variables object
        const variables: any = {
            projectId: body.projectId,
            version: {
                eq: 0
            }
        };

        // Add nextToken to variables only if it exists
        if (body.nextToken) {
            variables.nextToken = body.nextToken;
        }

        const datapoints = await client.graphql({
            query: listDatapointByProjectIdAndVersion,
            variables
        });

        
        // Get latest evaluation job
        const evaluationJob = await client.graphql({
          query: listJobByProjectIdAndVersionAndType,
          variables: {
            projectId: body.projectId,
            versionType: {
              eq: {
                version: 0,
                type: JobType.EVALUATION 
              }
            }
          }
        });

        const latestEvaluationJob = evaluationJob.data.listJobByProjectIdAndVersionAndType.items
          .filter((job: { averageQualityScore?: number | null | undefined }) => job.averageQualityScore != null)
          .sort((a: { createdAt: string | number | Date; }, b: { createdAt: string | number | Date; }) => 
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          )[0];

        return {
            data: datapoints.data.listDatapointByProjectIdAndVersion.items.map((item: any) => {
                return {
                    id: item.id,
                    data: item.data,
                    topic: item.topic,
                    ...(item?.accuracyScore && item?.accuracyScore != null && { accuracyScore: item.accuracyScore }),
                    ...(item?.adherenceScore && item?.adherenceScore != null && { adherenceScore: item.adherenceScore }),
                    ...(item?.qualityScore && item?.qualityScore != null && { qualityScore: item.qualityScore }),
                }
            }),
            nextToken: datapoints.data.listDatapointByProjectIdAndVersion.nextToken,
            ...(latestEvaluationJob?.averageQualityScore != null && {
              averageQualityScore: latestEvaluationJob.averageQualityScore * 10
            }),
            success: true
        };
    } catch (error) {
        console.error('Error fetching job status:', error);
        throw error;
    }
}

