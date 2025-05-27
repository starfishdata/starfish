import type { S3Handler } from 'aws-lambda';
import { S3 } from '@aws-sdk/client-s3';
import { Readable } from 'stream';
import readline from 'readline';
import { env } from "$amplify/env/generateSeedData";
import { generateClient } from "aws-amplify/data";
import { Amplify } from "aws-amplify";
import { Schema } from '../../data/resource';
import { createSeedDatapoint, updateSeedDataUploadJob } from './graphql/mutations';
import { SeedDataUploadJobStatus, SeedDatapointType } from './graphql/API';

const s3 = new S3();
const BATCH_SIZE = 500;

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

export const handler: S3Handler = async (event) => {
  const objectKeys = event.Records.map((record) => record.s3.object.key);
  console.log(`Upload handler invoked for objects [${objectKeys.join(', ')}]`);

  const bucket = event.Records[0].s3.bucket.name;
  const key = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, ' '));
  const projectId = key.split('/')[1];
  const fileName = key.split('/')[3];
  const seedDataUploadRunId = key.split('/')[4];

  console.log('Project ID:', projectId, 'File Name:', fileName, 'Seed Data Upload Run ID:', seedDataUploadRunId)

  try {
    const { Body } = await s3.getObject({ Bucket: bucket, Key: key });
    
    if (Body instanceof Readable) {
      await processFileInBatches(Body, projectId, fileName);
      console.log('File processing completed');
      await completeSeedDataRun(projectId, fileName, seedDataUploadRunId);
      console.log('Job Updated!');
    } else {
      throw new Error('S3 object body is not a readable stream');
    }
  } catch (error) {
    console.error('Error processing file:', error);
  }
}; 

async function processFileInBatches(stream: Readable, projectId: string, fileName: string) {
  const rl = readline.createInterface({
    input: stream,
    crlfDelay: Infinity
  });

  let batch: any[] = [];

  for await (const line of rl) {
    try {
      const item = JSON.parse(line);
      batch.push(item);

      if (batch.length >= BATCH_SIZE) {
        await processBatch(batch, projectId, fileName);
        batch = [];
      }
    } catch (error) {
      console.error('Error parsing JSON line:', error);
    }
  }

  // Process any remaining items
  if (batch.length > 0) {
    await processBatch(batch, projectId, fileName);
  }
}

async function processBatch(batch: any[], projectId: string, fileName: string) {
  const mutations = batch.map(item => 
    client.graphql({
      query: createSeedDatapoint,
      variables: {
        input: {
          projectId,
          data: JSON.stringify(item),
          type: SeedDatapointType.SEED,
          seedDataFile: fileName
        }
      }
    })
  );

  try {
    const results = await Promise.all(mutations);
    console.log(`Successfully processed ${results.length} items in batch`);
    return results;
  } catch (error) {
    console.error('Error processing batch:', error);
    // Implement retry logic or error reporting here
    throw error; // Re-throw if you want calling code to handle the error
  }
}

async function completeSeedDataRun(projectId: string, fileName: string, seedDataUploadRunId: string) {
  console.log('Completing Seed Data Upload Run');
  console.log('Project ID:', projectId, 'File Name:', fileName, 'Seed Data Upload Run ID:', seedDataUploadRunId);
  
  try {
    const result = await client.graphql({
      query: updateSeedDataUploadJob,
      variables: {
        input: {
          id: seedDataUploadRunId,
          status: SeedDataUploadJobStatus.COMPLETE,
        }
      }
    });
    console.log('Update successful:', result);
    return result;
  } catch (error) {
    console.error('Error updating SeedDataUploadJob:', error);
    throw error;
  }
}
