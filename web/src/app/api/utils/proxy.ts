import { NextRequest, NextResponse } from 'next/server';

const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8000';

interface ProxyOptions {
  method?: string;
  headers?: Record<string, string>;
}

export async function proxyToBackend(
  req: NextRequest, 
  endpoint: string, 
  options: ProxyOptions = {}
) {
  try {
    const method = options.method || req.method;
    const targetUrl = `${TARGET_SERVER_BASE_URL}${endpoint}`;
    
    // Prepare request options
    const fetchOptions: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    // Add body for POST/PUT/PATCH requests
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
      const requestBody = await req.json();
      fetchOptions.body = JSON.stringify(requestBody);
    }

    // For GET requests, append query parameters if they exist
    if (method === 'GET') {
      const url = new URL(req.url);
      const searchParams = url.searchParams;
      if (searchParams.toString()) {
        const targetUrlWithParams = `${targetUrl}?${searchParams.toString()}`;
        const backendResponse = await fetch(targetUrlWithParams, fetchOptions);
        return handleBackendResponse(backendResponse, endpoint);
      }
    }

    // Make the actual request to the backend service
    const backendResponse = await fetch(targetUrl, fetchOptions);
    return handleBackendResponse(backendResponse, endpoint);

  } catch (error) {
    console.error(`Error in ${endpoint} route:`, error);
    return new NextResponse('Internal server error', { status: 500 });
  }
}

async function handleBackendResponse(backendResponse: Response, endpoint: string) {
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
}

export function createCORSResponse() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
} 