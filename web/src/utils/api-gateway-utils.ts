import { runWithAmplifyServerContext } from './amplify-server-utils';
import { cookies } from 'next/headers';
import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth/server';

// API Gateway URL
const API_GATEWAY_URL = 'https://api.starfishdata.ai/';

/**
 * Makes an authenticated request to the API Gateway using Cognito authentication
 * @param path The API path to call
 * @param method The HTTP method (GET, POST, etc.)
 * @param body Optional request body
 * @returns The response from the API
 */
export async function callApiGateway(path: string, method: string, body?: any) {
  return await runWithAmplifyServerContext({
    nextServerContext: { cookies },
    async operation(contextSpec) {
      try {
        // Get the current user to ensure we have valid credentials
        const user = await getCurrentUser(contextSpec);
        if (!user) {
          throw new Error('User not authenticated');
        }
        
        // Get the auth session to get the ID token
        const session = await fetchAuthSession(contextSpec);
        const idToken = session.tokens?.idToken?.toString();
        
        if (!idToken) {
          throw new Error('No ID token available');
        }
        
        // Create the request URL
        const url = new URL(`${API_GATEWAY_URL}${path}`);
        
        // Make the request with the ID token in the Authorization header
        const response = await fetch(url.toString(), {
          method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${idToken}`,
          },
          body: body ? JSON.stringify(body) : undefined,
        });
        
        // Parse and return the response
        const responseData = await response.json();
        return {
          statusCode: response.status,
          body: responseData,
        };
      } catch (error) {
        console.error('Error calling API Gateway:', error);
        throw error;
      }
    },
  });
}

/**
 * Creates a new API key
 * @param name Name for the API key
 * @param description Description for the API key
 * @returns The created API key details
 */
export async function createApiKey(name: string, description: string) {
  return await callApiGateway('v1/apikeys', 'POST', {
    action: 'create',
    name,
    description,
  });
}

/**
 * Lists all API keys for the current user
 * @returns List of API keys
 */
export async function listApiKeys() {
  return await callApiGateway('v1/apikeys', 'GET');
}

/**
 * Deletes an API key
 * @param keyId The ID of the API key to delete
 * @returns Success message
 */
export async function deleteApiKey(keyId: string) {
  return await callApiGateway(`v1/apikeys/${keyId}`, 'DELETE');
} 