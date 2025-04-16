# starfish/adapters/litellm_adapter_ext.py

import os
from typing import Any, Dict, List

import litellm

from starfish.common.logger import get_logger

logger = get_logger(__name__)

# --- Configuration ---
# Convention:
# Keys = LiteLLM parameter names.
# Values:
#  - "$ENV_VAR_NAME" -> Fetches value DIRECTLY from os.getenv("ENV_VAR_NAME").
#                      The env var MUST contain the final desired value (e.g., "Bearer sk-...").
#  - Other           -> Literal static value (int, bool, string not starting with $).

OPENAI_COMPATIBLE_PROVIDERS_CONFIG: Dict[str, Dict[str, Any]] = {
    "hyperbolic": {
        "api_base": "$HYPERBOLIC_API_BASE",  # Env var HYPERBOLIC_API_BASE holds the URL
        "headers": {
            # Env var HYPERBOLIC_API_KEY MUST be set to "Bearer sk-..."
            "Authorization": "$HYPERBOLIC_API_KEY"
        },
    },
    # Add more providers following this ultra-simple convention
}


def _resolve_config_value(value: Any, description: str) -> Any:
    """Resolves a configuration value based on the '$' convention.
    '$VAR_NAME' -> os.getenv('VAR_NAME')
    Other -> literal value.
    """
    if isinstance(value, str) and value.startswith("$"):
        # Environment Variable lookup: $VAR_NAME
        env_var_name = value[1:]
        if not env_var_name:  # Handle edge case of just "$"
            raise ValueError(f"Invalid environment variable specification '$' ({description}).")

        env_var_value = os.getenv(env_var_name)
        if env_var_value is None:
            # Keep the description for helpful error messages
            error_msg = f"Required environment variable '{env_var_name}' not set ({description})."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        return env_var_value  # Return the exact value from env var
    else:
        # It's a literal static value (int, bool, string not starting with $)
        return value


async def route_openai_compatible_request(
    provider_prefix: str,
    provider_config: Dict[str, Any],  # Assumes config dict is valid
    model_name: str,
    messages: List[Dict[str, str]],
    model_kwargs: Dict[str, Any],
) -> Any:
    """Handles requests for configured OpenAI-compatible providers using the
    simple '$' convention for environment variable lookup.
    """
    litellm_call_kwargs = {}
    resolved_headers = {}

    # Iterate directly through configured LiteLLM parameters
    for param_name, config_value in provider_config.items():
        param_desc = f"provider '{provider_prefix}', param '{param_name}'"
        try:
            if param_name == "headers":
                if not isinstance(config_value, dict):
                    logger.warning(f"Headers config is not a dictionary {param_desc}. Skipping.")
                    continue
                # Resolve each header value using the simple convention
                for header_key, header_config_value in config_value.items():
                    header_desc = f"provider '{provider_prefix}', header '{header_key}'"
                    resolved_headers[header_key] = _resolve_config_value(header_config_value, header_desc)
            else:
                # Resolve other parameter values using the simple convention
                litellm_call_kwargs[param_name] = _resolve_config_value(config_value, param_desc)
        except (RuntimeError, ValueError):  # Catch env var missing or invalid '$'
            raise  # Propagate critical errors immediately
        except Exception as e:
            # Catch any unexpected errors during resolution
            logger.error(f"Unexpected error resolving value {param_desc}: {e}", exc_info=True)
            raise RuntimeError(f"Error resolving value {param_desc}") from e

    if resolved_headers:
        litellm_call_kwargs["headers"] = resolved_headers  # Add resolved headers if any

    # --- Parameter construction is complete ---

    model_id = model_name.split("/", 1)[1]

    # Merge function kwargs, overriding config/resolved values
    final_kwargs = {**litellm_call_kwargs, **model_kwargs}

    return await litellm.acompletion(model="openai/" + model_id, messages=messages, **final_kwargs)
