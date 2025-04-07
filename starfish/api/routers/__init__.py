"""API Router initialization module
This module initializes all routers for the API application.
"""

from fastapi import APIRouter

from starfish.api.routers.system.health import router as health_router
from starfish.api.routers.system.models import router as models_router

# Main router that includes all other routers
api_router = APIRouter()

# Include all routers with appropriate prefixes and tags
api_router.include_router(models_router, prefix="/local_model", tags=["Local Model"])
api_router.include_router(health_router, prefix="/system", tags=["Health"])
