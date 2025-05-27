import { APIGatewayProxyHandler } from 'aws-lambda';
import { generateClient } from 'aws-amplify/data';
import { Amplify } from 'aws-amplify';
import { 
  APIGatewayClient, 
  CreateApiKeyCommand,
  CreateUsagePlanKeyCommand,
  GetApiKeysCommand,
  GetApiKeyCommand,
  DeleteApiKeyCommand,
  ApiKey,
  GetRestApisCommand,
} from '@aws-sdk/client-api-gateway';
import { Schema } from '../../data/resource';
import { env } from "$amplify/env/generateSeedData";
import { createApiKeys, deleteApiKeys } from "./graphql/mutations";
import { listApiKeysByApiGatewayKeyId } from './graphql/queries';

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


const apiGateway = new APIGatewayClient({});

// Helper to extract user ID from the request context
function getUserId(event: any): string {
  // Check if we have authorizer claims (Cognito authentication)
  if (event.requestContext?.authorizer?.claims) {
    const claims = event.requestContext.authorizer.claims;
    
    // The sub claim contains the user ID
    if (claims.sub) {
      return claims.sub;
    }
    
    // Fallback to username if sub is not available
    if (claims['cognito:username']) {
      return claims['cognito:username'];
    }
  }
  
  // Fallback to the old method if claims are not available
  const identity = event.requestContext?.identity;
  if (!identity) {
    throw new Error('No identity found in request context');
  }
  
  // For Cognito authentication, the user ID is in the claims
  if (identity.cognitoAuthenticationType === 'user') {
    return identity.cognitoIdentityId;
  }
  
  // For IAM authentication
  return identity.cognitoIdentityId || identity.cognitoAuthenticationProvider?.split(':').pop() || 'unknown-user';
}

// Helper to get the API ID
async function getApiId(): Promise<string> {
  // First try to get the API ID from environment variables
  
  // If not available, try to find the API by name
  try {
    const apisResponse = await apiGateway.send(new GetRestApisCommand({}));
    const starfishApi = apisResponse.items?.find(api => api.name === 'StarfishApi');
    
    if (starfishApi && starfishApi.id) {
      return starfishApi.id;
    }
    
    throw new Error('Could not find StarfishApi');
  } catch (error) {
    console.error('Error getting API ID:', error);
    throw new Error('Failed to get API ID');
  }
}

export const handler: APIGatewayProxyHandler = async (event) => {
  try {
    // Check if the request is authenticated
    if (!event.requestContext?.authorizer?.claims) {
      return {
        statusCode: 401,
        body: JSON.stringify({ error: 'Unauthorized' })
      };
    }
    
    const userId = getUserId(event);    
    // Handle different HTTP methods
    switch (event.httpMethod) {
      case 'POST':
        // Create API key
        const createBody = JSON.parse(event.body || '{}');
        const { name, description } = createBody;
        return await createApiKey(userId, name, description);
        
      case 'GET':
        // List API keys
        return await listApiKeys(userId);
        
      case 'DELETE':
        // Delete API key
        const keyId = event.pathParameters?.keyId;
        if (!keyId) {
          return {
            statusCode: 400,
            body: JSON.stringify({ error: 'API key ID is required' })
          };
        }
        return await deleteApiKey(userId, keyId);
        
      default:
        return {
          statusCode: 400,
          body: JSON.stringify({ error: 'Invalid HTTP method' })
        };
    }
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
};

async function createApiKey(userId: string, name: string, description: string) {
  // Create API key with user-specific name
  const keyName = `${userId}-${name}`;
  const keyDescription = `${description}`;

  const createKeyResponse = await apiGateway.send(new CreateApiKeyCommand({
    name: keyName,
    description: keyDescription,
    enabled: true
  }));

  // Capture the API key value immediately after creation
  // This is the only time we can get the full key value
  const apiKeyValue = createKeyResponse.value;

  // Associate API key with usage plan
  await apiGateway.send(new CreateUsagePlanKeyCommand({
      usagePlanId: 'mpysi2', //default usage plan id
      keyId: createKeyResponse.id,
      keyType: 'API_KEY'
  }));

  // Create the API key in the database
  const createApiKeyResponse = await client.graphql({
      query: createApiKeys,
      variables: {
        input: {
          userId, 
          apiKey: apiKeyValue,
          usagePlanId: 'mpysi2', //default usage plan id,
          apiGatewayKeyId: createKeyResponse.id
        }
      }
  });


  return {
    statusCode: 200,
    body: JSON.stringify({
      apiKey: apiKeyValue, // Use the value captured at creation time
      keyId: createKeyResponse.id,
      usagePlanId: 'mpysi2', //default usage plan id
      name: keyName,
      description: keyDescription
    })
  };
}

async function listApiKeys(userId: string) {
  try {
    const response = await apiGateway.send(new GetApiKeysCommand({}));

    // Filter keys to only show those belonging to the user
    const userKeys = response.items?.filter((key: ApiKey) => 
      key.name?.startsWith(`${userId}-`)
    ) || [];
    
    // Get the actual API key values for each key
    const keysWithValues = await Promise.all(
      userKeys.map(async (key) => {
        try {
          // Get the API key value
          const keyResponse = await apiGateway.send(new GetApiKeyCommand({
            apiKey: key.id
          }));
                    
          // Return the key with its value and creation date
          return {
            ...key,
            value: keyResponse.value,
            createdDate: key.createdDate || new Date().toISOString()
          };
        } catch (error) {
          console.error(`Error getting value for key ${key.id}:`, error);
          return {
            ...key,
            createdDate: key.createdDate || new Date().toISOString()
          }; // Return the key without the value if there's an error
        }
      })
    );

    return {
      statusCode: 200,
      body: JSON.stringify({
        items: keysWithValues
      })
    };
  } catch (error) {
    console.error('Error listing API keys:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: 'Failed to list API keys',
        items: [] // Return empty array instead of undefined
      })
    };
  }
}

async function deleteApiKey(userId: string, keyId: string) {
  // First verify the key belongs to the user
  const keyResponse = await apiGateway.send(new GetApiKeyCommand({
    apiKey: keyId
  }));

  if (!keyResponse.name?.startsWith(`${userId}-`)) {
    return {
      statusCode: 403,
      body: JSON.stringify({ error: 'Not authorized to delete this API key' })
    };
  }

  //get key from db
  const apiKeyDBResponse = await client.graphql({
    query: listApiKeysByApiGatewayKeyId,
    variables: {
      apiGatewayKeyId: keyId
    }
  });

  // Delete the key if it belongs to the user
  await apiGateway.send(new DeleteApiKeyCommand({
    apiKey: keyId
  }));

  const deleteApiKeyResponse = await client.graphql({
    query: deleteApiKeys,
    variables: {
      input: {
        id: apiKeyDBResponse.data.listApiKeysByApiGatewayKeyId.items[0].id as string
      }
    }
  })

  return {
    statusCode: 200,
    body: JSON.stringify({
      message: 'API key deleted successfully'
    })
  };
} 