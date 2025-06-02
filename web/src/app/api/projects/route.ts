import { NextRequest } from 'next/server';
import { proxyToBackend, createCORSResponse } from '../utils/proxy';

// This should match the expected structure from your Python backend
interface ApiProcessedProject {
  id: string;
  owner: string;
  repo: string;
  name: string;
  repo_type: string;
  submittedAt: number;
  language: string;
}

// Ensure this matches your Python backend configuration
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_HOST || 'http://localhost:8000';
const PROJECTS_API_ENDPOINT = `${PYTHON_BACKEND_URL}/api/processed_projects`;

export async function GET(req: NextRequest) {
  return proxyToBackend(req, '/projects');
}

export async function POST(req: NextRequest) {
  return proxyToBackend(req, '/projects');
}

export async function OPTIONS() {
  return createCORSResponse();
} 