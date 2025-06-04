import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL, derived from environment variable or defaulted.
// This should match the logic in your frontend's page.tsx for consistency.
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8002';

export async function POST(req: NextRequest) {
  try {
    const requestBody = await req.json(); // Assuming the frontend sends JSON
    const targetUrl = `${TARGET_SERVER_BASE_URL}/dataset/evaluate`;

    // Make the actual request to the backend service
    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // If the backend service returned an error, forward that error to the client
    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      const errorHeaders = new Headers();
      backendResponse.headers.forEach((value, key) => {
        errorHeaders.set(key, value);
      });
      return new NextResponse(errorBody, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        headers: errorHeaders,
      });
    }

    // Ensure the backend response has a body to stream
    if (!backendResponse.body) {
      return new NextResponse('Stream body from backend is null', { status: 500 });
    }

    return new NextResponse(backendResponse.body, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: backendResponse.headers,
    });
  } catch (error) {
    console.error('Error in template/run route:', error);
    return new NextResponse('Internal server error', { status: 500 });
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