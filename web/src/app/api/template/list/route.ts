import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL, derived from environment variable or defaulted.
// This should match the logic in your frontend's page.tsx for consistency.
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8002';

export async function GET() {
  try {
    const targetUrl = `${TARGET_SERVER_BASE_URL}/template/list`;

    // Make the actual request to the backend service
    const response = await fetch(targetUrl, {
      method: 'GET',
    });
    if (!response.ok) {
      // Try to parse error from backend, otherwise use status text
      let errorBody = { error: `Failed to fetch from Python backend: ${response.statusText}` };
      try {
        errorBody = await response.json();
      } catch {
        // If parsing JSON fails, errorBody will retain its default value
        // The error from backend is logged in the next line anyway
      }
      console.error(`Error from Python backend (${targetUrl}): ${response.status} - ${JSON.stringify(errorBody)}`);
      return NextResponse.json(errorBody, { status: response.status });
    }

    const templates = await response.json();
    return NextResponse.json(templates);

  } catch (error) {
    console.error('Error in API proxy route:', error);
    let errorMessage = 'Internal Server Error in proxy';
    if (error instanceof Error) {
      errorMessage = error.message;
    }
    return new NextResponse(JSON.stringify({ error: errorMessage }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// Optional: Handle OPTIONS requests for CORS if you ever call this from a different origin
// or use custom headers that trigger preflight requests. For same-origin, it's less critical.
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204, // No Content
    headers: {
      'Access-Control-Allow-Origin': '*', // Be more specific in production if needed
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization', // Adjust as per client's request headers
    },
  });
} 