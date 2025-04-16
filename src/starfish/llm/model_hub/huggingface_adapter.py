"""HuggingFace service for interacting with the HuggingFace API.
This service focuses on model discovery, search, and downloading from HuggingFace.
"""

import asyncio
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from starfish.common.logger import get_logger

##TODO we will need to move the dependencies of ollma to a seperate file so we can support other model hosting providers like vllm. but for now it is fine
from starfish.llm.backend.ollama_adapter import delete_model as delete_ollama_model
from starfish.llm.backend.ollama_adapter import is_model_available

logger = get_logger(__name__)

HF_API_BASE = "https://huggingface.co/api"


#############################################
# HuggingFace Exception Types
#############################################
class HuggingFaceError(Exception):
    """Base exception for HuggingFace-related errors."""

    pass


class HuggingFaceAuthError(HuggingFaceError):
    """Error raised when authentication is required but missing."""

    pass


class HuggingFaceModelNotFoundError(HuggingFaceError):
    """Error raised when a model is not found."""

    pass


class HuggingFaceAPIError(HuggingFaceError):
    """Error raised for general API errors."""

    pass


#############################################
# Core HuggingFace API Functions
#############################################
def get_hf_token() -> Optional[str]:
    """Get HuggingFace API token from environment variable."""
    return os.environ.get("HUGGING_FACE_HUB_TOKEN")


async def _make_hf_request(url: str, params: Optional[Dict] = None, check_auth: bool = True) -> Tuple[bool, Any]:
    """Make a request to HuggingFace API with proper error handling.

    Args:
        url: API URL to request
        params: Optional query parameters
        check_auth: Whether to include auth token if available

    Returns:
        Tuple of (success, data/error_message)
    """
    headers = {}
    if check_auth:
        token = get_hf_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return True, await response.json()
                elif response.status in (401, 403):
                    return False, "Authentication required. Please set the {HUGGING_FACE_HUB_TOKEN} environment variable."
                else:
                    return False, f"Request failed with status {response.status}"
    except Exception as e:
        return False, f"Request error: {str(e)}"


async def list_hf_models(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """List/search models on HuggingFace.

    Args:
        query: Optional search query
        limit: Maximum number of results

    Returns:
        List of model info dictionaries
    """
    params = {"limit": limit}
    if query:
        params["search"] = query

    success, result = await _make_hf_request(f"{HF_API_BASE}/models", params)

    if success:
        # Filter to only include models that are likely to work with Ollama
        # (supporting language models that might have GGUF variants)
        return [
            {
                "id": model.get("id", ""),
                "name": model.get("modelId", model.get("id", "")),
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "tags": model.get("tags", []),
                "requires_auth": "gated" in model.get("tags", []) or model.get("private", False),
            }
            for model in result
            if "text-generation" in model.get("pipeline_tag", "") or any(tag in model.get("tags", []) for tag in ["llm", "gguf", "quantized"])
        ]
    else:
        logger.error(f"Failed to list models: {result}")
        return []


async def get_imported_hf_models() -> List[str]:
    """Get list of HuggingFace models that have been imported to Ollama.

    Returns:
        List of model names in Ollama that originated from HuggingFace
    """
    from starfish.llm.backend.ollama_adapter import list_models

    models = await list_models()
    return [model.get("name", "") for model in models if model.get("name", "").startswith("hf-")]


async def check_model_exists(model_id: str) -> bool:
    """Check if a model exists on HuggingFace.

    Args:
        model_id: HuggingFace model ID (e.g., "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")

    Returns:
        bool: True if model exists, False otherwise
    """
    success, _ = await _make_hf_request(f"{HF_API_BASE}/models/{model_id}")
    return success


async def find_gguf_files(model_id: str) -> List[Dict[str, Any]]:
    """Find GGUF files available for a HuggingFace model.

    Args:
        model_id: HuggingFace model ID

    Returns:
        List of file objects containing GGUF files
    """
    # First try to check the main branch
    success, data = await _make_hf_request(f"{HF_API_BASE}/models/{model_id}/tree/main")

    if not success:
        # Try checking the master branch as fallback
        success, data = await _make_hf_request(f"{HF_API_BASE}/models/{model_id}/tree/master")
        if not success:
            return []

    if not isinstance(data, list):
        logger.error(f"Unexpected data format from HuggingFace API: {type(data)}")
        return []

    # First look for GGUF files
    gguf_files = [file for file in data if isinstance(file, dict) and file.get("path", "").lower().endswith(".gguf")]

    # If we found GGUF files, return them
    if gguf_files:
        logger.info(f"Found {len(gguf_files)} GGUF files for model {model_id}")
        return gguf_files

    # Otherwise, look for GGUF files in subdirectories
    for item in data:
        if isinstance(item, dict) and item.get("type") == "directory":
            dir_path = item.get("path")
            if dir_path:
                # Common directories where GGUF files are stored
                if any(keyword in dir_path.lower() for keyword in ["gguf", "quant", "quantized", "weights", "models"]):
                    success, subdir_data = await _make_hf_request(f"{HF_API_BASE}/models/{model_id}/tree/main/{dir_path}")
                    if success and isinstance(subdir_data, list):
                        subdir_gguf_files = [file for file in subdir_data if isinstance(file, dict) and file.get("path", "").lower().endswith(".gguf")]
                        if subdir_gguf_files:
                            logger.info(f"Found {len(subdir_gguf_files)} GGUF files in subdirectory {dir_path}")
                            gguf_files.extend(subdir_gguf_files)

    return gguf_files


async def download_gguf_file(model_id: str, file_path: str, target_path: str) -> bool:
    """Download a GGUF file from HuggingFace.

    Args:
        model_id: HuggingFace model ID
        file_path: Path to the file within the repository
        target_path: Local path to save the file

    Returns:
        bool: True if download was successful, False otherwise
    """
    url = f"https://huggingface.co/{model_id}/resolve/main/{file_path}"

    try:
        logger.info(f"Downloading {url} to {target_path}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        headers = {}
        token = get_hf_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    if response.status in (401, 403):
                        return False  # Auth error handled by caller
                    logger.error(f"Error downloading GGUF file: {response.status}")
                    return False

                # Download with progress reporting
                total_size = int(response.headers.get("Content-Length", 0))
                chunk_size = 1024 * 1024  # 1MB chunks
                downloaded = 0

                # Track last time progress was reported
                import time

                last_progress_time = 0
                last_percentage = -1

                # Always log the start
                logger.info("Download started: 0.0%")

                with open(target_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size:
                            current_time = time.time()
                            progress = downloaded / total_size * 100
                            current_percentage = int(progress)

                            # Log progress if 5+ seconds have passed or if we've hit a new percentage multiple of 25
                            if current_time - last_progress_time >= 5 or (current_percentage % 25 == 0 and current_percentage != last_percentage):
                                logger.info(f"Download progress: {progress:.1f}%")
                                last_progress_time = current_time
                                last_percentage = current_percentage

                # Always log the completion
                logger.info(f"Download completed: {target_path}")
                return True

    except Exception as e:
        logger.error(f"Error downloading GGUF file: {e}")
        return False


async def import_model_to_ollama(local_file_path: str, model_name: str) -> bool:
    """Import a GGUF file into Ollama.

    Args:
        local_file_path: Path to the downloaded GGUF file
        model_name: Name to give the model in Ollama

    Returns:
        bool: True if import was successful, False otherwise
    """
    try:
        # Ensure Ollama bin exists
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            logger.error("Ollama binary not found")
            return False

        # Create a temporary Modelfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            modelfile_path = f.name
            f.write(f"FROM {os.path.abspath(local_file_path)}\n")
            f.write('TEMPLATE "{.System}\\n\\n{.Prompt}"')

        logger.info(f"Created temporary Modelfile at {modelfile_path}")

        # Import the model using Ollama
        logger.info(f"Importing model into Ollama as {model_name}")
        process = await asyncio.create_subprocess_exec(
            ollama_bin, "create", model_name, "-f", modelfile_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # Capture output
        stdout, stderr = await process.communicate()

        # Clean up temporary file
        os.unlink(modelfile_path)

        if process.returncode == 0:
            logger.info(f"Successfully imported model as {model_name}")
            return True
        else:
            logger.error(f"Failed to import model: {stderr.decode()}")
            return False

    except Exception as e:
        logger.error(f"Error importing model to Ollama: {e}")
        return False


async def get_best_gguf_file(gguf_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Select the best GGUF file from a list of files.
    Prioritizes:
    1. Smaller quantization (q4_K > q5_K > q8_0)
    2. File size (prefers smaller files for same quantization level)
    3. Avoid huge files unless necessary.

    Args:
        gguf_files: List of GGUF file objects

    Returns:
        The best GGUF file object or None if list is empty
    """
    if not gguf_files:
        return None

    # Quantization priority (lower is better for typical use cases)
    # Prioritize middle-range quantization for balance of quality and size
    quant_priority = {
        "q4_k": 1,  # Best balance for most use cases
        "q5_k": 2,  # Good balance of quality and size
        "q4_0": 3,  # Good for typical use
        "q4_1": 4,  # Good for typical use
        "q3_k": 5,  # More compression, less quality
        "q5_0": 6,
        "q5_1": 7,
        "q6_k": 8,
        "q2_k": 9,  # Lowest quality but smallest
        "q8_0": 10,  # High quality but larger
        "f16": 20,  # Full precision, very large
        "f32": 30,  # Full precision, extremely large
    }

    # Add a size penalty for very large files
    MAX_PREFERRED_SIZE = 4 * 1024 * 1024 * 1024  # 4GB

    # Extract quantization information
    for file in gguf_files:
        path = file.get("path", "").lower()
        size = file.get("size", 0)

        # Determine quantization level
        quant_score = 100  # Default high value
        for quant, priority in quant_priority.items():
            if quant in path:
                quant_score = priority
                break

        # Store the score and size in the file object for sorting
        file["_quant_score"] = quant_score
        file["_size"] = size

    # First try to find models under the preferred size with good quantization
    preferred_files = [f for f in gguf_files if f.get("_size", 0) <= MAX_PREFERRED_SIZE]

    if preferred_files:
        # Sort by quantization score (lower is better)
        sorted_files = sorted(preferred_files, key=lambda x: x.get("_quant_score", 100))
    else:
        # If all files are large, sort by quantization score
        sorted_files = sorted(gguf_files, key=lambda x: x.get("_quant_score", 100))

    if sorted_files:
        selected = sorted_files[0]
        size_mb = selected.get("_size", 0) / (1024 * 1024)
        logger.info(f"Selected GGUF file: {selected.get('path')} ({size_mb:.1f} MB)")
        return selected

    return None


async def download_best_gguf_for_model(model_id: str) -> Tuple[bool, str, Optional[str]]:
    """Download the best GGUF file for a HuggingFace model.
    This is a pure HuggingFace operation that doesn't directly depend on Ollama.

    Args:
        model_id: HuggingFace model ID

    Returns:
        Tuple of (success, message, local_file_path)
        Where local_file_path is the path to the downloaded file if successful, None otherwise

    Raises:
        HuggingFaceModelNotFoundError: If the model doesn't exist on HuggingFace
        HuggingFaceAuthError: If authentication is required but not provided
        HuggingFaceError: For other HuggingFace-related errors
    """
    # Check if model exists
    if not await check_model_exists(model_id):
        error_msg = f"Model {model_id} not found on HuggingFace"
        logger.error(error_msg)
        raise HuggingFaceModelNotFoundError(error_msg)

    # Find GGUF files
    gguf_files = await find_gguf_files(model_id)
    if not gguf_files:
        error_msg = f"No GGUF files found for model {model_id}"
        logger.error(error_msg)
        raise HuggingFaceError(error_msg)

    # Select best GGUF file
    best_file = await get_best_gguf_file(gguf_files)
    if not best_file:
        error_msg = f"Could not select a suitable GGUF file for model {model_id}"
        logger.error(error_msg)
        raise HuggingFaceError(error_msg)

    # Create a temporary directory for download
    temp_dir = tempfile.mkdtemp()
    try:
        file_path = best_file.get("path")
        file_name = os.path.basename(file_path)
        local_file_path = os.path.join(temp_dir, file_name)

        # Download the GGUF file
        if not await download_gguf_file(model_id, file_path, local_file_path):
            # Check if it's an auth error
            token = get_hf_token()
            if not token:
                error_msg = f"Authentication required for model {model_id}. Please set the HUGGING_FACE_HUB_TOKEN environment variable."
                logger.error(error_msg)
                raise HuggingFaceAuthError(error_msg)
            else:
                error_msg = f"Failed to download GGUF file for model {model_id}"
                logger.error(error_msg)
                raise HuggingFaceError(error_msg)

        logger.info(f"Successfully downloaded GGUF file to {local_file_path}")
        return True, f"Successfully downloaded model {model_id}", local_file_path

    except Exception as e:
        # Clean up temp directory in case of error
        shutil.rmtree(temp_dir, ignore_errors=True)

        # Re-raise HuggingFace exceptions directly
        if isinstance(e, (HuggingFaceModelNotFoundError, HuggingFaceAuthError, HuggingFaceError)):
            raise

        # For other exceptions, wrap in HuggingFaceError
        logger.exception(f"Unexpected error downloading model {model_id}")
        raise HuggingFaceError(f"Unexpected error: {str(e)}")


async def prepare_hf_model_for_ollama(model_id: str) -> Tuple[bool, str]:
    """Prepare a HuggingFace model for use with Ollama.
    This function bridges HuggingFace and Ollama services.

    Args:
        model_id: HuggingFace model ID

    Returns:
        Tuple of (success, message_or_ollama_name)

    Raises:
        HuggingFaceModelNotFoundError: If the model doesn't exist on HuggingFace
        HuggingFaceAuthError: If authentication is required but not provided
        HuggingFaceError: For other HuggingFace-related errors
    """
    # Create a sanitized model name for Ollama
    ollama_name = f"hf-{model_id.replace('/', '-').lower()}"

    try:
        # Check if model is already imported in Ollama
        if await is_model_available(ollama_name):
            logger.info(f"Model {ollama_name} is already available in Ollama")
            return True, ollama_name

        # Download the best GGUF file
        success, message, local_file_path = await download_best_gguf_for_model(model_id)
        if not success or not local_file_path:
            # Re-raise the specific error based on the message
            if "not found" in message.lower():
                raise HuggingFaceModelNotFoundError(message)
            elif "authentication" in message.lower():
                raise HuggingFaceAuthError(message)
            else:
                raise HuggingFaceError(message)

        try:
            # Import to Ollama
            if not await import_model_to_ollama(local_file_path, ollama_name):
                raise HuggingFaceError(f"Failed to import model {model_id} to Ollama")

            logger.info(f"Successfully prepared HuggingFace model {model_id} as Ollama model {ollama_name}")
            return True, ollama_name
        finally:
            # Clean up the temp directory containing the downloaded file
            temp_dir = os.path.dirname(local_file_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

    except (HuggingFaceModelNotFoundError, HuggingFaceAuthError, HuggingFaceError):
        # Let specific exceptions propagate up
        raise
    except Exception as e:
        logger.exception(f"Error preparing model {model_id} for Ollama")
        raise HuggingFaceError(f"Error preparing model: {str(e)}")


async def ensure_hf_model_ready(model_id: str) -> Tuple[bool, str]:
    """Ensure a HuggingFace model is ready for use with Ollama.
    This function bridges HuggingFace and Ollama services.

    Args:
        model_id: HuggingFace model ID

    Returns:
        Tuple of (success, ollama_model_name)

    Raises:
        HuggingFaceModelNotFoundError: If the model doesn't exist on HuggingFace
        HuggingFaceAuthError: If authentication is required but not provided
        HuggingFaceError: For other HuggingFace-related errors
    """
    from starfish.llm.backend.ollama_adapter import (
        OllamaConnectionError,
        ensure_model_ready,
    )

    # First ensure Ollama is running
    try:
        if not await ensure_model_ready(""):  # Just make sure Ollama is running
            raise HuggingFaceError("Failed to start Ollama server")

        # Prepare the HuggingFace model for Ollama
        return await prepare_hf_model_for_ollama(model_id)
    except OllamaConnectionError as e:
        # Convert Ollama errors to HuggingFace errors for consistent error handling
        logger.error(f"Ollama connection error: {e}")
        raise HuggingFaceError(f"Ollama server error: {str(e)}")


async def delete_hf_model(model_id: str) -> bool:
    """Delete a HuggingFace model from Ollama.
    This function bridges HuggingFace and Ollama services.

    Args:
        model_id: Either the HuggingFace model ID or the Ollama model name

    Returns:
        bool: True if deletion was successful
    """
    # If this looks like a HF model ID, convert to Ollama name format
    if "/" in model_id and not model_id.startswith("hf-"):
        ollama_name = f"hf-{model_id.replace('/', '-').lower()}"
    else:
        ollama_name = model_id

    return await delete_ollama_model(ollama_name)
