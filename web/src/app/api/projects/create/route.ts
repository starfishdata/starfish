import { NextRequest, NextResponse } from 'next/server'

interface CreateProjectRequest {
  project_name: string
  project_description: string
  template_name?: string
}

interface ProjectData {
  name: string
  description: string
  template_name?: string
}


// Get backend URL from environment
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_HOST || 'http://localhost:8002'

export async function POST(request: NextRequest) {
  try {
    const body: CreateProjectRequest = await request.json()
    
    // Validate required fields
    if (!body.project_name || !body.project_description || !body.template_name) {
      return NextResponse.json(
        { error: 'Project name, description and template name are required' },
        { status: 400 }
      )
    }

    // Prepare project data with both project and template information
    const projectData: ProjectData = {
      name: body.project_name.trim(),
      description: body.project_description.trim(),
      template_name: body.template_name || undefined,
    }

    // Send to Python backend
    const backendResponse = await fetch(`${PYTHON_BACKEND_URL}/project/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(projectData)
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

      console.error(`Error creating project in backend: ${backendResponse.status} - ${errorMessage}`)
      
      return NextResponse.json(
        { error: `Failed to create project: ${errorMessage}` },
        { status: backendResponse.status }
      )
    }

    // Get the created project from backend response
    const createdProject = await backendResponse.json()

    // Log successful creation with template info
    console.log("Project created successfully:", {
      projectName: createdProject.name,
      templateName: createdProject.template_name || 'none'
    })

    return NextResponse.json(createdProject, { status: 201 })

  } catch (error: unknown) {
    console.error('Error in createProject API route:', error)
    
    // Handle different types of errors
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
      { error: `Failed to create project: ${message}` },
      { status: 500 }
    )
  }
}

// Optional: Handle GET requests to return creation form or validation
export async function GET() {
  return NextResponse.json({
    message: 'Project creation endpoint',
    required_fields: ['project_name', 'project_description'],
    optional_fields: ['template_name', 'template_description'],
    method: 'POST'
  })
} 