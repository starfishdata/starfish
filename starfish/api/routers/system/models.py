"""
Model management API routes
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
import logging

from starfish.services.model_management_service import (
    list_local_models as service_list_models, 
    delete_local_model as service_delete_model,
    search_huggingface_models,
    download_huggingface_model
)

logger = logging.getLogger(__name__)

router = APIRouter()

class DeleteModelResponse(BaseModel):
    """Response model for model deletion"""
    success: bool
    message: str

class ModelListResponse(BaseModel):
    """Response model for model listing"""
    models: List[Dict[str, Any]]

class DownloadModelRequest(BaseModel):
    """Request model for model download"""
    model_id: str

class DownloadModelResponse(BaseModel):
    """Response model for model download"""
    success: bool
    message: str


@router.get("/list", response_model=ModelListResponse, tags=["Local Model"])
async def get_local_models(request: Request):
    """List all locally available models"""
    models = await service_list_models()
    return {"models": models}


@router.delete("/{model_name}", response_model=DeleteModelResponse, tags=["Local Model"])
async def remove_local_model(model_name: str, request: Request):
    """Delete a local model"""
    logger.info(f"Deleting model: {model_name}")
    message = await service_delete_model(model_name)
    return {"success": True, "message": message}


@router.get("/search_hf_models", response_model=ModelListResponse, tags=["Local Model"])
async def search_hf_models(
    request: Request,
    query: str = Query("", description="Search query"),
    limit: int = Query(20, description="Maximum number of results")
):
    """Search for models on HuggingFace"""
    models = await search_huggingface_models(query, limit)
    return {"models": models}


@router.post("/download_hf_model", response_model=DownloadModelResponse, tags=["Local Model"])
async def download_model(request: DownloadModelRequest, req: Request):
    """Download a HuggingFace model and import it to Ollama"""
    logger.info(f"Downloading model: {request.model_id}")
    message = await download_huggingface_model(request.model_id)
    return {"success": True, "message": message}