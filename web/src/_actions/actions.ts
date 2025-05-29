"use server"

import { cookieBasedClient, getUser } from "@/src/utils/amplify-server-utils"
import OpenAI from "openai";
import fs from 'fs';
import { promisify } from "util";
import path from 'path';
import { createRepo, uploadFilesWithProgress, whoAmI } from "@huggingface/hub";
import { data } from "@/amplify/data/resource";

const proj_func_call = {
  id: 'proj_func_call',
  userId: 'user_67890',
  name: 'My func_call Project',
  template_name: 'starfish/generate_func_call_dataset',
  description: 'A project for testing AI models',
  datapoints: [],
  seedDatapoints: [],
  finetuneJobs: [],
  exportJobs: [],
  jobs: [],
  seedDataUploadJobs: [],
  latestSeedFile: 'seed_data_20231001.json',
  latestDatasetVersion: 1
};


const proj_topic_generate = {
  id: 'proj_topic_generate',
  userId: 'user_67890',
  name: 'My topic generate Project',
  template_name: 'starfish/generate_by_topic',
  description: 'A project for testing AI models',
  datapoints: [],
  seedDatapoints: [],
  finetuneJobs: [],
  exportJobs: [],
  jobs: [],
  seedDataUploadJobs: [],
  latestSeedFile: 'seed_data_20231001.json',
  latestDatasetVersion: 1
};
/** PROJECT ACTIONS */
export async function createProject(formData: FormData) {
    const currentUser = await getUser();
    
    const { data: user } = await cookieBasedClient.models.User.get({
        id: currentUser?.sub
      });
      
    const newProject = await cookieBasedClient.models.Project.create({
        name: formData.get('project_name') == null ? '' : formData.get('project_name') as string,
        description: formData.get('project_description') == null ? '' : formData.get('project_description') as string,
        userId: user?.id
    });

    return {
      name: newProject?.data?.name,
      description: newProject?.data?.description,
      id: newProject?.data?.id,
      createdAt: newProject?.data?.createdAt,
      updatedAt:  newProject?.data?.updatedAt,
    }
}

export async function getAllProjectsOfUser() {
    // const currentUser = await getUser();

    // const { data: user } = await cookieBasedClient.models.User.get({
    //     id: currentUser?.sub
    //   });

    // const projects = await user?.projects()

    // let output = projects?.data.map((project) => ({
    //     name: project.name,
    //     description: project.description,
    //     id: project.id,
    //     createdAt: project.createdAt,
    //     updatedAt:  project.updatedAt,
    //   }));
      
    // output = output?.sort((a, b) => {
    //     const dateA = new Date(a.createdAt);
    //     const dateB = new Date(b.createdAt);
    //     return dateB.getTime() - dateA.getTime(); // Sort in descending order (newest first)
    // });

    //return output;
    
    return [proj_func_call,proj_topic_generate]
}

export async function getProjectById(id: string) {
    // const { data: project } = await cookieBasedClient.models.Project.get({
    //     id: id as string
    //   });
    let project = null;
    if (id == 'proj_func_call') {
      project = proj_func_call;
    } else if (id == 'proj_topic_generate') {
      project = proj_topic_generate;
    }

    return {
        name: project?.name,
        description: project?.description,
        latestSeedFile: project?.latestSeedFile,
        latestDatasetVersion: project?.latestDatasetVersion,
        template_name: project?.template_name || ""
    }
}


export async function getAllDataPointsByProjectId(id: string) {
    const { data: project } = await cookieBasedClient.models.Project.get({
        id: id as string
    });

    const datapoints = await fetchAllDataPoints(id);

    const output = datapoints?.map((datapoint) => ({
        name: datapoint.name,
        type: datapoint.type,
        data: datapoint.data
    }));

    if (output == undefined) {
      return null;
    }

    return output;
}

export async function getDataPointsByProjectIdAndVersion(id: string, version: number | null | undefined) {
  // if (version == null || version == undefined) {
  //   version = 0;
  // }

  // const datapoints = await fetchAllDataPointsByVersion(id, version);

  // const output = datapoints?.map((datapoint) => ({
  //     id: datapoint.id,
  //     name: datapoint.name,
  //     type: datapoint.type,
  //     data: datapoint.data,
  //     topic: datapoint.topic,
  //     liked: datapoint.liked,
  //     qualityScore: datapoint.qualityScore * 10
  // }));

  // if (output == undefined) {
  //   return null;
  // }

  // return output;
  return null;
}

export async function createUser() {
    const currentUser = await getUser();
    let storedUser = await cookieBasedClient.models.User.get({
        id: currentUser?.sub
    });

    if (storedUser.data == null) {
        await cookieBasedClient.models.User.create({
            id: currentUser?.sub,
            name: currentUser?.family_name == null ? "" : currentUser?.family_name,
            email: currentUser?.email == null ? "" : currentUser?.email
        });
    }
}

export async function generateData(projectId: string, prompt: string, datapointNumber: string, model: string) {
    try {
        const llmEndpoint = process.env.LLM || 'http://starfish-llm-dev-env.us-east-1.elasticbeanstalk.com';

        const project = await cookieBasedClient.models.Project.get({
          id: projectId as string
        });

        const newJob: any = await cookieBasedClient.models.Job.create({
            projectId: projectId,
            type: 'GENERATION',
            status: 'RUNNING',
            userPrompt: prompt,
            model: model,
            inputNumOfRecords: datapointNumber,
            requestedRecords: parseInt(datapointNumber),
            version: project?.data?.latestDatasetVersion  ? project.data?.latestDatasetVersion + 1 : 0
        });

        const request = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            accept: 'application/json',
          },
          body: JSON.stringify({
            project_id: projectId,
            job_id: newJob.data?.id,
            total_num_datapoints: datapointNumber,
            topic_step: {},
            generation_step: {
              model_name: model,
              user_instruction: prompt,
            }
          }),
        }

        await fetch(llmEndpoint + '/api/v1/producer/generations/vanilla/invoke', request);
        await cookieBasedClient.models.Job.update({
          id: newJob.data?.id,
          config: JSON.stringify(request)
        })

      } catch (error) {
        console.log('error!')
      } 
}

async function fetchAllDataPoints(id: string) {
  const { data: project } = await cookieBasedClient.models.Project.get({
    id: id as string  
  });

  let datapoints: any = await project?.datapoints({
    limit: 1000
  });

  let allData = [...datapoints?.data];
  
  while (datapoints?.nextToken !== null) {
    allData = [...allData, ...datapoints.data];
    datapoints = await project?.datapoints({
      limit: 1000,
      nextToken: datapoints.nextToken
    });
  }

  return allData;
}

async function fetchAllDataPointsByVersion(id: string, version: number) {
  // let datapoints: any = await cookieBasedClient.models.Datapoint.listDatapointByProjectIdAndVersion({
  //   projectId: id,
  //   version: {
  //     eq: version
  //   }
  // },
  // {
  //   limit: 1000
  // });

  // let allData = [...datapoints?.data];
  // let nextToken = datapoints?.nextToken;
  
  // while (nextToken !== null) {
  //   datapoints = await cookieBasedClient.models.Datapoint.listDatapointByProjectIdAndVersion({
  //     projectId: id,
  //     version: {
  //       eq: version
  //     }
  //   }, 
  //   {
  //     limit: 1000,
  //     nextToken: datapoints?.nextToken
  //   });
  //   allData = [...allData, ...datapoints?.data];
  //   nextToken = datapoints.nextToken;
  // }

  // return allData;

  return []
}


export async function fetchLatestGenerationJobByProjectId(projectId: string) {
  // let generationJobs: any = await cookieBasedClient.models.Job.listJobByProjectId({
  //     projectId: projectId
  //   },
  //   {
  //     limit: 1000
  //   });

  // const sortedAndFiltered = generationJobs?.data
  // .filter((job: any) => job.type === 'GENERATION')
  // .sort((a: { createdAt: string | number | Date; }, b: { createdAt: string | number | Date; }) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  // const latestJob = sortedAndFiltered?.length > 0 ? sortedAndFiltered[0] : [];
  const latestJob = []
  if (latestJob.length == 0) {
    return {
      jobId: null,
      status: 'NOT_STARTED',
      numberOfRecords: null,
      model: null,
      prompt: null
    }
  }

  // return {
  //   jobId: latestJob.id,
  //   status: latestJob.status,
  //   numberOfRecords: latestJob.inputNumOfRecords,
  //   model: latestJob.model,
  //   prompt: latestJob.userPrompt
  // }
}

export async function likeDataPoint(datapointId: string, liked: number) {
    await cookieBasedClient.models.Datapoint.update({
      id: datapointId,
      liked: liked,
    });
}

export async function getJobDataForProjectAndVersion(projectId: string, version: number | null | undefined) {
  // const allJobs: any = await cookieBasedClient.models.Job.listJobByProjectId({
  //   projectId: projectId
  // }, {
  //   limit: 1000
  // });

  // const latestGenerationJob = allJobs?.data
  // .filter((job: { type: string; version: number }) => job.type === 'GENERATION' && job.version === version)
  // .sort((a: { createdAt: string | number | Date; }, b: { createdAt: string | number | Date; }) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0] || null;

  // const latestEvaluationJob = allJobs?.data
  // .filter((job: { type: string; version: number }) => job.type === 'EVALUATION' && job.version === version)
  // .sort((a: { createdAt: string | number | Date; }, b: { createdAt: string | number | Date; }) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0] || null;

  // return {
  //   generationJob: {
  //     jobId: latestGenerationJob?.id,
  //     status: latestGenerationJob?.status,
  //   },
  //   evaluationJob: {
  //     jobId: latestEvaluationJob?.id,
  //     status: latestEvaluationJob?.status,
  //     averageQualityScore: latestEvaluationJob?.averageQualityScore * 10,
  //   }
  // }

  const sampleJobData = {
    generationJob: {
      jobId: 'gen_job_12345',
      status: 'COMPLETE'
    },
    evaluationJob: {
      jobId: 'eval_job_67890',
      status: 'RUNNING',
      averageQualityScore: 8.5
    }
  };
  return  sampleJobData
}

/** SEED DATA ACTIONS */
export async function startSeedDataRun(projectId: string, seedDataFileName: string) {
  await cookieBasedClient.models.Project.update({
    id: projectId,
    latestSeedFile: seedDataFileName
  });
  const uploadJob: any = await cookieBasedClient.models.SeedDataUploadJob.create({
    projectId: projectId,
    status: 'STARTING',
    fileName: seedDataFileName
  });
  return uploadJob?.data?.id;
}

export async function updateSeedDataRunStatus(id: string, status: 'STARTING' | 'RUNNING' | 'COMPLETE' | 'FAILED') {
  await cookieBasedClient.models.SeedDataUploadJob.update({
    id: id,
    status: status,
  });
}

export async function fetchAllSeedDataPoints(projectId: string) {
  // const { data: seedDataPoints } = await cookieBasedClient.models.SeedDatapoint.list({
  //   limit: 100,
  //   filter: { projectId: { eq: projectId } }
  // });

  // let allData = [ ...seedDataPoints ];
  
  // // while (seedDataPoints.nextToken !== null) {
  // //   allData = [...allData, ...seedDataPoints.data];
  // //   seedDataPoints = await project?.seedDatapoints({
  // //     limit: 1000,
  // //     nextToken: seedDataPoints.nextToken
  // //   });
  // // }

  // const output = allData?.map((datapoint: { id: any; type: any; data: any; }) => ({
  //   id: datapoint.id,
  //   type: datapoint.type,
  //   data: datapoint.data
  // }));

  // if (output == undefined || output == null) {
  //   return [];
  // }

  // return output;
  return []
}

export async function fetchSeedDataUploadJobStatus(projectId: string) {
  // let project = await cookieBasedClient.models.Project.get({
  //   id: projectId,
  // });

  // const seedDatUploadJobs = await project.data?.seedDataUploadJobs();

  // if (seedDatUploadJobs?.data == undefined || seedDatUploadJobs?.data == null || seedDatUploadJobs?.data.length == 0) {
  //   return "NOT STARTED";
  // }

  // seedDatUploadJobs?.data.sort((a: { createdAt: string | number | Date; }, b: { createdAt: string | number | Date; }) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  // let status =  seedDatUploadJobs.data[0].status;

  // if (status == null || status == undefined) {
  //   return "NOT STARTED";
  // }

  // return seedDatUploadJobs.data[0].status;
  return "NOT STARTED";
}


/** FINE TUNING ACTIONS */
export async function getAllFineTuningJobForProject(projectId: string) {
  // const { data: project } = await cookieBasedClient.models.Project.get({
  //   id: projectId
  // });

  // const finetuneJobs = await project?.finetuneJobs()


  // finetuneJobs?.data.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  // const output = finetuneJobs?.data.map((job) => ({
  //   id: job.id,
  //   type: job.type,
  //   model: job.model,
  //   events: JSON.parse(job.events as string),
  //   status: job.status,
  //   finetunedModel: job.finetunedModel
  // }));

  // if (output == null || output == undefined) {
  //   return [];
  // }

  // return output;
  return []
}

export async function checkJobEvents(jobId: string) {
  const { data: finetuneJob } = await cookieBasedClient.models.FinetuneJob.get({
    id: jobId
  });

  const openai = new OpenAI({
    apiKey: finetuneJob?.apiKey!
  });
  
  const openAiFinetuneJob = await openai.fineTuning.jobs.retrieve(finetuneJob?.jobIdentifier!);
  const list = await openai.fineTuning.jobs.listEvents(finetuneJob?.jobIdentifier!, {
    limit: 100
  });

  if (openAiFinetuneJob.status === 'succeeded') {
    await cookieBasedClient.models.FinetuneJob.update({
      id: jobId,
      events:  JSON.stringify(list),
      status: 'COMPLETE',
      finetunedModel: openAiFinetuneJob.fine_tuned_model
    });
  } else if (openAiFinetuneJob.status === 'failed' || openAiFinetuneJob.status === 'cancelled') {
    await cookieBasedClient.models.FinetuneJob.update({
      id: jobId,
      events: JSON.stringify(list),
      status: 'FAILED'
    });
    }  else {
    await cookieBasedClient.models.FinetuneJob.update({
      id: jobId,
      events:  JSON.stringify(list),
      status: 'RUNNING'
    });  
  }

  const freshFineTuneFetch = await cookieBasedClient.models.FinetuneJob.get({id: jobId});
  const freshFetchEvents = freshFineTuneFetch.data?.events as string;
  return {
    status: freshFineTuneFetch.data?.status,
    events: JSON.parse(freshFetchEvents),
    finetunedModel: openAiFinetuneJob.fine_tuned_model !== null ? openAiFinetuneJob.fine_tuned_model : null,
    baseModel: finetuneJob?.model
  }
}

export async function createFineTuneRun(id: string, apiKey: string, model: string, version: number, filterDownvote: boolean, filterScoreUnder: number) {
  const writeFileAsync = promisify(fs.writeFile);


  if (Number.isNaN(filterScoreUnder)) {
    filterScoreUnder = 0
  }

  const openai = new OpenAI({
    apiKey: apiKey
  });

  const { data: project } = await cookieBasedClient.models.Project.get({
    id: id as string  
  });

  const datapoints: any = await fetchAllDataPointsByVersion(id, version);

  const tuningdata: any[] = [];

  // Format Data for OpenAI Fine-Tuning
  datapoints.map((item: any) => {
    const jsonData = JSON.parse(item.data);
    if (jsonData.question) {
      const message = {
        messages: [
          {
            role: 'user',
            content: JSON.stringify(jsonData.question)
          },
          {
            role: 'assistant',
            content: JSON.stringify(jsonData.answer)
          }
        ]
      }
      const itemDisliked = item.liked === -1;
      if (filterDownvote && itemDisliked) {
        return;
      }

      if (item.qualityScore && item.qualityScore * 10 < filterScoreUnder) {
        return;
      }

      tuningdata.push(message);
    }
  });

  if (tuningdata.length === 0) {
    throw new Error('No data for fine tuning!');
  }

  const jsonlString = tuningdata.map((item) => JSON.stringify(item)).join('\n');

  // 3. Write JSONL to a temporary file
  const tempFilePath = path.join(process.cwd(), `starfishdata-${id}-${model}-${Date.now()}.jsonl`);
  await writeFileAsync(tempFilePath, jsonlString, 'utf8');

   // 4. Use fs.createReadStream to upload the file to OpenAI
   const fileStream = fs.createReadStream(tempFilePath);

  // Upload the file to OpenAI (using the OpenAI SDK)
  const uploadResponse = await openai.files.create({
    file: fileStream,
    purpose: 'fine-tune',
  });

  const fileId = uploadResponse.id;

  // 5. Create Fine-Tune Job
  const fineTune = await openai.fineTuning.jobs.create({
    training_file: fileId, 
    model: 'gpt-4o-mini-2024-07-18'
  });

  await cookieBasedClient.models.FinetuneJob.create({
    projectId: id,
    apiKey: apiKey,
    trainingFileName: uploadResponse.filename,
    trainingFileId: uploadResponse.id,
    model: 'gpt-4o-mini-2024-07-18',
    type: 'OPENAI',
    jobIdentifier: fineTune.id,
    status: 'RUNNING'
  });

  fs.unlinkSync(tempFilePath);

  return;
}


/** EXPORT ACTIONS */
export async function uploadToHuggingFace(id: string, apiToken: string, version: number, filterDownvote: boolean, filterScoreUnder: number) {
  const job: any = await cookieBasedClient.models.ExportJob.create({
    projectId: id,
    apiKey: apiToken,
    type: 'HUGGINGFACE',
    status: 'RUNNING',
    events: JSON.stringify({data: []})
  });

  // Start the background process
  Promise.resolve().then(() => backgroundUploadProcess(id, apiToken, job!.data!.id!, version, filterDownvote, filterScoreUnder));

  // Return the initial job information immediately
  return {
    id: job.data.id,
    type: job.data.type,
    events: JSON.parse(job.data.events as string),
    status: job.data.status,
    datasetUrl: job.data.datasetUrl
  };
}

async function backgroundUploadProcess(id: string, apiToken: string, exportJobId: string, version: number, filterDownvote: boolean, filterScoreUnder: number) {
  try {
    const { data: project } = await cookieBasedClient.models.Project.get({
      id: id as string  
    });

    const who = await whoAmI({
      accessToken: apiToken
    });

    const repoName = `${who.name}/project-${project?.name?.replaceAll(' ', '')}-${exportJobId}`

    const jsonlString = await generateJsonlStringInQnAFormatWithFilter(id, version, filterDownvote, filterScoreUnder);

    const repo = await createRepo({
      repo: {type: "dataset", name: repoName},
      accessToken: apiToken
    });
    await cookieBasedClient.models.ExportJob.update({
      id: exportJobId,
      datasetUrl: repo.repoUrl
    });

    for await (const progressEvent of await uploadFilesWithProgress({
      repo: {
        type: "dataset",
        name: repoName
      },
      accessToken: apiToken,
      files: [
        {
          path: `${repoName}.jsonl`,
          content: new Blob([jsonlString], { type: 'application/jsonl' })
        }
      ],
    })) {
      await updateEvents(progressEvent, exportJobId) 
    }
    await cookieBasedClient.models.ExportJob.update({
      id: exportJobId,
      status: 'COMPLETE' 
    });
  } catch (error) {
    await updateEvents({created_at: Date.now()/1000, message: error}, exportJobId);
    await cookieBasedClient.models.ExportJob.update({
      id: exportJobId,
      status: 'FAILED' 
    });
  }  
}

export async function getAllExportJobForProject(projectId: string) {
  // const { data: project } = await cookieBasedClient.models.Project.get({
  //   id: projectId
  // });

  // const exportJobs = await project?.exportJobs()

  // exportJobs?.data.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  // const output = exportJobs?.data.map((job) => ({
  //   id: job.id,
  //   type: job.type,
  //   events: JSON.parse(job.events as string),
  //   status: job.status,
  //   datasetUrl: job.datasetUrl
  // }));

  // if (output == null || output == undefined) {
  //   return [];
  // }
  // return output;
  return []
}

async function updateEvents(progressEvent: any, jobId: string) {
  const currentExportJobStatus = await cookieBasedClient.models.ExportJob.get({
    id: jobId
  });
  let events = JSON.parse(currentExportJobStatus.data?.events as string);
  events.data.push({
    created_at: Date.now()/1000,
    message: JSON.stringify(progressEvent)
  })
  await cookieBasedClient.models.ExportJob.update({
    id: jobId,
    events: JSON.stringify(events)
  });
}

/** EVALUATION JOBS */
export async function getAllEvaluationJobForProject(projectId: string) {
  // const allEvaluationJobsForProject = await cookieBasedClient.models.Job.listJobByProjectId({
  //   projectId: projectId
  // },
  // {
  //   limit: 1000,
  //   filter: { type: { eq: 'EVALUATION' } },
  // });

  // const sortedJobs = allEvaluationJobsForProject.data.sort((a: { createdAt: string | number | Date; }, b: { createdAt: string | number | Date; }) => {
  //   return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  // });

  // const mappedJobs = sortedJobs.map(
  //   (job: { id: any; status: any; version: any; averageQualityScore: any; }) => ({
  //     id: job?.id,
  //     status: job?.status,
  //     version: job?.version,
  //     overallScore: job?.averageQualityScore * 10
  //   })
  // );

  //return mappedJobs;
  return []
}

export async function createEvaluationJob(projectId: string, version: number) {
  try {
    const llmEndpoint = process.env.LLM || 'http://starfish-llm-dev-env.us-east-1.elasticbeanstalk.com';

    const evaluationJob = await cookieBasedClient.models.Job.create({
      projectId: projectId,
      type: 'EVALUATION',
      status: 'RUNNING',
      version: version,
    });
  
    const request = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        accept: 'application/json',
      },
      body: JSON.stringify({
        project_id: projectId,
        job_id: evaluationJob.data?.id,
        version: version,
        job_type: 'evaluations_vanilla',
        max_datapoints_per_run: 10
      }),
    }

    await fetch(llmEndpoint + '/api/v1/producer/evaluations/vanilla/invoke', request);
    await cookieBasedClient.models.Job.update({
      id: evaluationJob.data?.id,
      config: JSON.stringify(request)
    });

    return evaluationJob.data?.id;
  } catch (error) {
    console.log('error!')
  }
}

/** JSONL FILE FORMAT PARSING ACTIONS */
export async function generateJsonlData(id: string, version: number) {
  const { data: project } = await cookieBasedClient.models.Project.get({
    id: id as string  
  });

  const jsonlString = await generateJsonlStringInQnAFormat(id, version);

  return jsonlString;
}

async function generateJsonlStringInQnAFormat(id: string, version: number) {
  const datapoints: any = await fetchAllDataPointsByVersion(id, version);

  const uploadData: any[] = [];

  datapoints?.map((item: any) => {
    const jsonData = JSON.parse(item.data);
    if (jsonData.question) {
      const message = {
        question: jsonData.question,
        answer: jsonData.answer
      }
      uploadData.push(message);
    }
  });

  const jsonlString = uploadData.map((item: any) => JSON.stringify(item)).join('\n');
  return jsonlString;
}

async function generateJsonlStringInQnAFormatWithFilter(id: string, version: number, filterDownvote: boolean, filterScoreUnder: number) {
  const datapoints: any = await fetchAllDataPointsByVersion(id, version);

  if (Number.isNaN(filterScoreUnder)) {
    filterScoreUnder = 0
  }

  const uploadData: any[] = [];

  datapoints?.filter((item: { liked: number; qualityScore: number; }) => {
    if (filterDownvote && item.liked === -1) {
      return false;
    }
    // Skip items below quality score threshold
    if (item.qualityScore && item.qualityScore * 10 < filterScoreUnder) {
      return false;
    }
    return true;
  }).map((item: any) => {
    const jsonData = JSON.parse(item.data);
    if (jsonData.question) {
      const message = {
        question: jsonData.question,
        answer: jsonData.answer
      }

      uploadData.push(message);
    }
  });

  const jsonlString = uploadData.map((item: any) => JSON.stringify(item)).join('\n');
  return jsonlString;
}