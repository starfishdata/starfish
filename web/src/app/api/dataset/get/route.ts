import { NextRequest } from 'next/server';
import { proxyToBackend, createCORSResponse } from '../../utils/proxy';

export async function POST(req: NextRequest) {
  return proxyToBackend(req, '/dataset/get');
}

// Optional: Handle OPTIONS requests for CORS if you ever call this from a different origin
// or use custom headers that trigger preflight requests. For same-origin, it's less critical.
export async function OPTIONS() {
  return createCORSResponse();
} 