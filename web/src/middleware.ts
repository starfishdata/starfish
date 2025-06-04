
import { NextRequest, NextResponse } from 'next/server';
export async function middleware(request: NextRequest) {
  const response = NextResponse.next();

  // Remove all auth-related logic and just return the response
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - image files (.jpg, .jpeg, .png, .gif, etc.)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|sign-in|.*\\.(?:jpg|jpeg|png|gif|webp|svg)).*)'
  ]
};