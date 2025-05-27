import { NextRequest, NextResponse } from 'next/server';
import { createApiKey } from '../../../../utils/api-gateway-utils';
import { isAuthenticated } from '../../../../utils/amplify-server-utils';

export async function POST(request: NextRequest) {
  try {
    // Check if the user is authenticated
    const authenticated = await isAuthenticated();
    if (!authenticated) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Parse the request body
    const body = await request.json();
    const { name, description } = body;

    // Validate the request body
    if (!name) {
      return NextResponse.json(
        { error: 'Name is required' },
        { status: 400 }
      );
    }

    // Call the API Gateway to create an API key
    const response = await createApiKey(name, description);

    // Return the response
    return NextResponse.json(response.body, { status: response.statusCode });
  } catch (error) {
    console.error('Error creating API key:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
} 