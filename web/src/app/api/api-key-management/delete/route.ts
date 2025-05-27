import { NextRequest, NextResponse } from 'next/server';
import { deleteApiKey } from '../../../../utils/api-gateway-utils';
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
    const { keyId } = body;

    // Validate the request body
    if (!keyId) {
      return NextResponse.json(
        { error: 'API key ID is required' },
        { status: 400 }
      );
    }

    // Call the API Gateway to delete an API key
    const response = await deleteApiKey(keyId);

    // Return the response
    return NextResponse.json(response.body, { status: response.statusCode });
  } catch (error) {
    console.error('Error deleting API key:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
} 