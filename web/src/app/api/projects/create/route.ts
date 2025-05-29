import { NextRequest, NextResponse } from 'next/server'

interface CreateProjectRequest {
  project_name: string
  project_description: string
  template_name?: string
  template_description?: string
}

interface ProjectData {
  id: string
  name: string
  description: string
  template_name?: string
  template_description?: string
  owner: string
  repo: string
  repo_type: string
  language: string
  submittedAt: number
}

// Generate a unique ID for the project
function generateProjectId(): string {
  return `proj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// Get backend URL from environment
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_HOST || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body: CreateProjectRequest = await request.json()
    
    // Validate required fields
    if (!body.project_name || !body.project_description) {
      return NextResponse.json(
        { error: 'Project name and description are required' },
        { status: 400 }
      )
    }

    // Prepare project data with both project and template information
    const projectData: ProjectData = {
      id: generateProjectId(),
      name: body.project_name.trim(),
      description: body.project_description.trim(),
      template_name: body.template_name || undefined,
      template_description: body.template_description || undefined,
      owner: 'user', // You might want to get this from authentication
      repo: body.project_name.toLowerCase().replace(/\s+/g, '-'),
      repo_type: body.template_name ? 'template' : 'manual',
      language: 'python', // Default or derive from template
      submittedAt: Date.now()
    }

    // Send to Python backend
    const backendResponse = await fetch(`${PYTHON_BACKEND_URL}/api/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add any authentication headers if needed
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
    console.log(`Project created successfully: ${createdProject.id}`, {
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