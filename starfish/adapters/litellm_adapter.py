import litellm
import os
from typing import List, Dict, Optional, Any
from starfish.common.logger import get_logger

logger = get_logger(__name__)

def get_available_models() -> List[str]:
    """
    Returns a list of all available models from litellm.
    
    Returns:
        List[str]: A list of valid model names.
    """
    available_models = litellm.utils.get_valid_models()
    return available_models


def build_chat_messages(user_instruction: str, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Constructs a list of chat messages for the LLM.

    Args:
        user_input (str): The input message from the user.
        system_prompt (str, optional): An optional system prompt to guide the conversation.

    Returns:
        List[Dict[str, str]]: A list of message dictionaries formatted for the chat API.
    """
    messages: List[Dict[str, str]] = []
    if system_prompt:
        # Add the system prompt to the messages if provided
        messages.append({"role": "system", "content": system_prompt})
    # Add the user's message to the messages
    messages.append({"role": "user", "content": user_instruction})
    return messages

"""
Model router for directing requests to appropriate model backends
"""
from typing import Dict, Any, List, Optional
import shutil
import litellm
from starfish.common.logger import get_logger

logger = get_logger(__name__)

# Installation guides by platform
OLLAMA_INSTALLATION_GUIDE = """
Ollama is not installed. Please install it:

Mac:
curl -fsSL https://ollama.com/install.sh | sh

Linux:
curl -fsSL https://ollama.com/install.sh | sh

Windows:
Download the installer from https://ollama.com/download

After installation, restart your application.
"""


async def route_ollama_request(model_name: str, messages: List[Dict[str, str]], model_kwargs: Dict[str, Any]) -> Any:
    """
    Handle Ollama-specific model requests
    
    Args:
        model_name: The full model name (e.g., "ollama/llama3")
        messages: The messages to send to the model
        model_kwargs: Additional keyword arguments for the model
        
    Returns:
        The response from the Ollama model
    """
    from starfish.adapters.ollama_adapter import ensure_model_ready, OllamaError
    
    # Extract the actual model name
    ollama_model_name = model_name.split("/", 1)[1]
    
    try:
        # Check if Ollama is installed
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            logger.error("Ollama is not installed")
            raise OllamaError(f"Ollama is not installed.\n{OLLAMA_INSTALLATION_GUIDE}")
        
        # Ensure the Ollama model is ready before using
        logger.info(f"Ensuring Ollama model {ollama_model_name} is ready...")
        model_ready = await ensure_model_ready(ollama_model_name)
        
        if not model_ready:
            error_msg = f"Failed to provision Ollama model: {ollama_model_name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        # The model is ready, make the API call
        logger.info(f"Model {ollama_model_name} is ready, making API call...")
        return await litellm.acompletion(model=model_name, messages=messages, **model_kwargs)
        
    except OllamaError as e:
        error_msg = f"Ollama error: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error with Ollama model: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    

async def route_huggingface_request(model_name: str, messages: List[Dict[str, str]], model_kwargs: Dict[str, Any]) -> Any:
    """
    Handle HuggingFace model requests by importing into Ollama
    
    Args:
        model_name: The full model name (e.g., "hf/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
        messages: The messages to send to the model
        model_kwargs: Additional keyword arguments for the model
    """
    from starfish.services.huggingface_service import ensure_hf_model_ready
    
    # Extract the HuggingFace model ID (everything after "hf/")
    hf_model_id = model_name.split("/", 1)[1]
    
    try:
        # Ensure the HuggingFace model is ready in Ollama
        logger.info(f"Ensuring HuggingFace model {hf_model_id} is ready...")
        success, ollama_model_name = await ensure_hf_model_ready(hf_model_id)
        
        if not success:
            error_msg = f"Failed to provision HuggingFace model: {hf_model_id}. {ollama_model_name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        # The model is ready in Ollama, make the API call using the Ollama endpoint
        logger.info(f"Model {hf_model_id} is ready as Ollama model {ollama_model_name}, making API call...")
        return await litellm.acompletion(model=f"ollama/{ollama_model_name}", messages=messages, **model_kwargs)
        
    except Exception as e:
        error_msg = f"HuggingFace error: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    

async def route_hyperbolic_request(model_name: str, messages: List[Dict[str, str]], model_kwargs: Dict[str, Any]) -> Any:
    """
    Handle requests for Hyperbolic models.

    Args:
        model_name (str): The full model name (e.g., "hyperbolic/Qwen/QwQ-32B")
        messages (List[Dict[str, str]]): The messages to send to the model.
        model_kwargs (Dict[str, Any]): Additional model parameters.

    Returns:
        Any: The response from the Hyperbolic model.
    """
    HYPERBOLIC_API_KEY_ERROR = "HYPERBOLIC_API_KEY is not set. Please set it in the environment variables."
    HYPERBOLIC_API_BASE_ERROR = "HYPERBOLIC_API_BASE is not set. Please set it in the environment variables."

    # Ensure API key is set
    hyperbolic_api_key = os.getenv("HYPERBOLIC_API_KEY")
    if not hyperbolic_api_key:
        logger.error(HYPERBOLIC_API_KEY_ERROR)
        raise RuntimeError(HYPERBOLIC_API_KEY_ERROR)
    
    # Set up headers with the API key in Bearer format
    headers = {"Authorization": f"{hyperbolic_api_key}"}

    # Ensure API base is set
    hyperbolic_api_base = os.getenv("HYPERBOLIC_API_BASE")
    if not hyperbolic_api_base:
        logger.error(HYPERBOLIC_API_BASE_ERROR)
        raise RuntimeError(HYPERBOLIC_API_BASE_ERROR)

    # Extract the model name from the full name (remove the "hyperbolic/" prefix)
    model_id = model_name.split("/", 1)[1]  # e.g., "Qwen/QwQ-32B"
    
    # Use openai as the provider with the Hyperbolic API base    
    return await litellm.acompletion(
        model="openai/" + model_id,  # Use openai as the provider
        messages=messages,
        api_base = hyperbolic_api_base,   
        headers = headers,
        **model_kwargs
    ) 


async def call_chat_model(model_name: str, messages: List[Dict[str, str]], model_kwargs: Optional[Dict[str, Any]] = None) -> Any:
    """
    Routes the model request to the appropriate backend based on the model name prefix.
    
    Args:
        model_name: The name of the model (e.g., "ollama/llama3")
        messages: The messages to send to the model
        model_kwargs: Additional keyword arguments for the model
        
    Returns:
        The response from the model
    """
    model_kwargs = model_kwargs or {}
    
    try:
        # Route based on model prefix
        if model_name.startswith("ollama/"):
            # Direct Ollama model
            return await route_ollama_request(model_name, messages, model_kwargs)
            
        elif model_name.startswith("hf/"):
            # HuggingFace models are served through Ollama, but with a different prefix
            # This allows using HF models directly without downloading them first
            # These are not actually directly using HF API - they're served through Ollama
            return await route_huggingface_request(model_name, messages, model_kwargs)
        
        elif model_name.startswith("hyperbolic/"):
            return await route_hyperbolic_request(model_name, messages, model_kwargs)
    
        # Future providers can be added here with additional elif statements
        # elif model_name.startswith("vllm/"):
        #     return await route_vllm_request(model_name, messages, model_kwargs)
        else:
            # Default case - use litellm directly
            try:
                return await litellm.acompletion(model=model_name, messages=messages, **model_kwargs)
            except Exception as e:
                logger.error(f"LiteLLM error: {str(e)}")
                raise RuntimeError(f"Error executing model {model_name}: {str(e)}")
    except Exception as e:
        logger.exception(f"Error in execute_chat_completion for model {model_name}")
        raise RuntimeError(f"Error executing model {model_name}: {str(e)}")
        

async def build_and_call_chat_model(
    model_name: str,
    user_instruction: str,
    system_prompt: Optional[str] = None,
    model_kwargs: Optional[Dict[str, Any]] = None
) -> Any:
    """
    A convenience function that combines constructing chat messages and executing chat completion.
    
    Args:
        model_name (str): The name of the model to use for chat completion.
        user_instruction (str): The input message from the user.
        system_prompt (Optional[str], optional): An optional system prompt to guide the conversation. Defaults to None.
        model_kwargs (Optional[Dict[str, Any]], optional): Additional keyword arguments for the model. Defaults to None.
    
    Returns:
        Any: The response from the chat completion API.
    """
    # Construct the messages
    messages = build_chat_messages(user_instruction, system_prompt)
    
    # Execute the chat completion
    return await call_chat_model(model_name, messages, model_kwargs)