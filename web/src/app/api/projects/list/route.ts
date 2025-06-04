import { NextRequest, NextResponse } from 'next/server'

interface ListProjectsRequest {
  userId?: string
}

// Get backend URL from environment
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_HOST || 'http://localhost:8002'

export async function POST(request: NextRequest) {
  try {
    const body: ListProjectsRequest = await request.json()
    
    // Send to Python backend to get project list
    const backendResponse = await fetch(`${PYTHON_BACKEND_URL}/project/list`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body)
    })

    if (!backendResponse.ok) {
      // Try to get error details from backend
      let errorMessage = `Backend error: ${backendResponse.statusText}`
      try {
        const errorData = await backendResponse.json()
        errorMessage = errorData.error || errorMessage
      } catch {
        // If we can't parse the error, use the status text
      }

      console.error(`Error fetching projects from backend: ${backendResponse.status} - ${errorMessage}`)
      
      return NextResponse.json(
        { error: `Failed to fetch projects: ${errorMessage}` },
        { status: backendResponse.status }
      )
    }

    // Get the project list from backend response
    const projects = await backendResponse.json()

    console.log("Projects fetched successfully:", projects.length || 0, "projects")

    return NextResponse.json(projects, { status: 200 })

  } catch (error: unknown) {
    console.error('Error in listProjects API route:', error)
    
    if (error instanceof SyntaxError) {
      return NextResponse.json(
        { error: 'Invalid JSON in request body' },
        { status: 400 }
      )
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: 'Unable to connect to backend service' },
        { status: 503 }
      )
    }

    const message = error instanceof Error ? error.message : 'An unknown error occurred'
    return NextResponse.json(
      { error: `Failed to fetch projects: ${message}` },
      { status: 500 }
    )
  }
}