"""Model management service for listing, downloading, and deleting models.
This service provides unified functionality for both Ollama and HuggingFace models.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from starfish.adapters.huggingface_adapter import (
    HuggingFaceAuthError,
    HuggingFaceError,
    HuggingFaceModelNotFoundError,
)
from starfish.adapters.huggingface_adapter import (
    list_hf_models as list_huggingface_models,
)
from starfish.adapters.huggingface_adapter import prepare_hf_model_for_ollama
from starfish.adapters.ollama_adapter import (
    OllamaConnectionError,
    OllamaNotInstalledError,
)
from starfish.adapters.ollama_adapter import delete_model as delete_ollama_model
from starfish.adapters.ollama_adapter import is_ollama_running
from starfish.adapters.ollama_adapter import list_models as list_ollama_models
from starfish.adapters.ollama_adapter import start_ollama_server
from starfish.common.exceptions import (
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
)
from starfish.common.logger import get_logger

logger = get_logger(__name__)


class ModelInfo(BaseModel):
    """Model information schema"""

    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None
    description: Optional[str] = None
    model_type: str
    status: str
    tags: List[str] = []


async def list_local_models() -> List[Dict[str, Any]]:
    """List all locally available models

    Returns:
        List of model information dictionaries

    Raises:
        InternalServerError: If the Ollama server fails to start
    """
    # Ensure Ollama is running
    if not await is_ollama_running():
        success = await start_ollama_server()
        if not success:
            logger.error("Failed to start Ollama server")
            raise InternalServerError("Failed to start Ollama server")

    # Get models from Ollama
    ollama_models = await list_ollama_models()

    # Format model information
    models = []
    for model in ollama_models:
        model_type = "huggingface" if model.get("name", "").startswith("hf-") else "ollama"

        # Extract model details safely
        details = model.get("details", {}) or {}
        if not isinstance(details, dict):
            details = {}

        # Convert to dict and ensure all values are properly serializable
        model_info = {
            "name": model.get("name", ""),
            "size": model.get("size", 0),
            "modified_at": model.get("modified_at", ""),
            "description": details.get("description", ""),
            "model_type": model_type,
            "status": "downloaded",
            "tags": details.get("tags", []) if isinstance(details.get("tags"), list) else [],
        }
        models.append(model_info)

    return models


async def delete_local_model(model_name: str) -> str:
    """Delete a local model

    Args:
        model_name: Name of the model to delete

    Returns:
        Success message

    Raises:
        InternalServerError: If the Ollama server fails to start or delete fails
        NotFoundError: If the model does not exist
    """
    # Ensure Ollama is running
    if not await is_ollama_running():
        success = await start_ollama_server()
        if not success:
            raise InternalServerError("Failed to start Ollama server")

    # Check if model exists
    models = await list_local_models()
    model_exists = any(model["name"] == model_name for model in models)

    if not model_exists:
        raise NotFoundError(f"Model {model_name} not found in local models")

    # Delete model
    success = await delete_ollama_model(model_name)
    if success:
        return f"Model {model_name} deleted successfully"
    else:
        raise InternalServerError(f"Failed to delete model {model_name}")


async def search_huggingface_models(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Search for models on HuggingFace

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of model information dictionaries
    """
    # Get models from HuggingFace
    models = await list_huggingface_models(query, limit)

    # Format model information
    formatted_models = []
    for model in models:
        formatted_models.append(
            {
                "name": model.get("name", ""),
                "id": model.get("id", ""),
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "tags": model.get("tags", []),
                "requires_auth": model.get("requires_auth", False),
                "model_type": "huggingface",
                "status": "remote",
            }
        )

    return formatted_models


async def download_huggingface_model(model_id: str) -> str:
    """Download a HuggingFace model and import it to Ollama

    Args:
        model_id: HuggingFace model ID

    Returns:
        Success message

    Raises:
        InternalServerError: If the Ollama server fails to start or download fails
        NotFoundError: If the model is not found
        UnauthorizedError: If authentication is required but not provided
    """
    # Ensure Ollama is running
    if not await is_ollama_running():
        try:
            success = await start_ollama_server()
            if not success:
                raise InternalServerError("Failed to start Ollama server")
        except OllamaNotInstalledError as e:
            logger.error(f"Ollama not installed: {e}")
            raise InternalServerError("Ollama is not installed") from e
        except OllamaConnectionError as e:
            logger.error(f"Could not connect to Ollama: {e}")
            raise InternalServerError("Could not connect to Ollama server") from e

    try:
        # Download and import model
        success, ollama_name = await prepare_hf_model_for_ollama(model_id)
        return f"Model {model_id} downloaded and imported as {ollama_name}"

    except HuggingFaceModelNotFoundError as e:
        # Convert HuggingFace exception to Starfish exception
        logger.error(f"Model not found: {model_id}")
        raise NotFoundError(str(e)) from e

    except HuggingFaceAuthError as e:
        logger.error(f"Authentication error for model {model_id}")
        raise UnauthorizedError(str(e)) from e

    except HuggingFaceError as e:
        logger.error(f"HuggingFace error for model {model_id}")
        raise InternalServerError(f"Error with HuggingFace: {str(e)}") from e

    except (NotFoundError, UnauthorizedError):
        # Re-raise these exceptions directly
        raise

    except Exception as e:
        # For unexpected exceptions, translate with exception chaining
        logger.exception(f"Unexpected error when downloading model {model_id}")
        raise InternalServerError(f"Failed to download model {model_id}: {str(e)}") from e
