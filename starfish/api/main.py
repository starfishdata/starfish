# Load environment variables from .env file
from starfish.common.env_loader import load_env_file
load_env_file()

from starfish.common.logger import get_logger
logger = get_logger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from starfish.adapters.ollama_adapter import stop_ollama_server

# Get the pre-initialized configuration
from starfish.common.exceptions import setup_exception_handlers

# Import our centralized router
from starfish.api.routers import api_router

# Import health check management
from starfish.api.routers.system.health import start_heartbeat, stop_heartbeat

#Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown tasks.
    """
    # Code that should run on startup
    logger.info("Starting Starfish API...")
    
    # Start the heartbeat monitoring
    start_heartbeat()
    logger.info("API server started with health monitoring")
    
    yield
    
    # Clean shutdown of health monitoring
    logger.info("Stopping health monitoring...")
    stop_heartbeat()
    
    # Code that should run on shutdown
    logger.info("Shutting down Ollama server as part of application shutdown...")
    await stop_ollama_server()


def create_application() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    Separating this from the main block makes testing easier.
    """
    # Create FastAPI app
    app = FastAPI(
        title="Starfish API",
        description="API for data generation using LLMs",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include our centralized router with /api prefix
    app.include_router(api_router, prefix="/api")

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "status": "ok", 
            "message": "Starfish API is running",
            "docs": "/api/docs"
        }
    
    return app


# Create the application instance
app = create_application()