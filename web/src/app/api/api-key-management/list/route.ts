import { NextRequest, NextResponse } from 'next/server';
import { listApiKeys } from '../../../../utils/api-gateway-utils';
import { isAuthenticated } from '../../../../utils/amplify-server-utils';

export async function GET(request: NextRequest) {
  try {
    // Check if the user is authenticated
    const authenticated = await isAuthenticated();
    if (!authenticated) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Call the API Gateway to list API keys
    const response = await listApiKeys();

    // Parse the response body to ensure it has the correct structure
    let responseBody;
    try {
      // If the response body is a string, parse it
      if (typeof response.body === 'string') {
        responseBody = JSON.parse(response.body);
      } else {
        responseBody = response.body;
      }
            
      // Ensure the response has an items property
      if (!responseBody.items) {
        responseBody.items = [];
      }
    } catch (error) {
      console.error('Error parsing response body:', error);
      responseBody = { items: [] };
    }

    // Return the response
    return NextResponse.json(responseBody, { status: response.statusCode });
  } catch (error) {
    console.error('Error listing API keys:', error);
    return NextResponse.json(
      { error: 'Internal server error', items: [] },
      { status: 500 }
    );
  }
} 