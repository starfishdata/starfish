import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from starfish.common.logger import get_logger

logger = get_logger(__name__)

from starfish.common.env_loader import load_env_file
from web.api.storage import setup_storage, close_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await setup_storage()
    yield
    # Shutdown (if needed)
    await close_storage()


# Import routers
from .routers import template, dataset, project

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.normpath(os.path.join(current_dir, "..", ".."))  # Go up two levels from web/api/
env_path = os.path.join(root_dir, ".env")
load_env_file(env_path=env_path)

# Initialize FastAPI app
app = FastAPI(title="Streaming API", lifespan=lifespan, description="API for streaming chat completions")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(template.router)
app.include_router(dataset.router)
app.include_router(project.router)


# Helper function to get adalflow root path
def get_adalflow_default_root_path():
    return os.path.expanduser(os.path.join("~", ".adalflow"))
