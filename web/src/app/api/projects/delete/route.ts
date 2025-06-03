import { NextRequest } from 'next/server';
import { proxyToBackend, createCORSResponse } from '../../utils/proxy';

export async function DELETE(req: NextRequest) {
  // const url = new URL(req.url);
  // const projectId = url.searchParams.get('id');
  
  // if (!projectId) {
  //   return new Response('Project ID is required', { status: 400 });
  // }
  
  return proxyToBackend(req, `/project/delete`);
}   

// Optional: Handle OPTIONS requests for CORS if you ever call this from a different origin
// or use custom headers that trigger preflight requests. For same-origin, it's less critical.
export async function OPTIONS() {
  return createCORSResponse();
} 