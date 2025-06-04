import ast
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Type
from pydantic import BaseModel

from starfish.common.logger import get_logger
from starfish import data_gen_template

logger = get_logger(__name__)

router = APIRouter(prefix="/template", tags=["template"])


class TemplateRegister(BaseModel):
    name: str = "starfish/generate_by_topic"
    input_schema: Type[BaseModel] = None
    output_schema: Optional[Type[BaseModel]] = None
    description: str = """Generates diverse synthetic data across multiple topics based on user instructions.
                   Automatically creates relevant topics if not provided and handles deduplication across generated content.
                """
    author: str = "Wendao Liu"
    starfish_version: str = "0.1.3"
    dependencies: List[str] = []
    input_example: str


class TemplateRunRequest(BaseModel):
    templateName: str
    inputs: dict


@router.get("/list")
async def get_template_list():
    """
    Get available model providers and their models.

    This endpoint returns the configuration of available model providers and their
    respective models that can be used throughout the application.

    Returns:
        List[TemplateRegister]: A list of template configurations
    """
    try:
        logger.info("Fetching model configurations")
        templates = data_gen_template.list(is_detail=True)
        for template in templates:
            try:
                input_example_str = template["input_example"]
                if isinstance(input_example_str, str):
                    # Remove any leading/trailing whitespace and quotes
                    input_example_str = input_example_str.strip()
                    # If it starts and ends with triple quotes, remove them
                    if input_example_str.startswith('"""') and input_example_str.endswith('"""'):
                        input_example_str = input_example_str[3:-3].strip()

                    # Try ast.literal_eval first (safest)
                    try:
                        template["input_example"] = ast.literal_eval(input_example_str)
                    except (ValueError, SyntaxError):
                        # If that fails, try eval with restricted globals (less safe but sometimes necessary)
                        logger.warning("Using eval() for complex expression - this should be avoided in production")
                        # Create a restricted environment for eval
                        safe_dict = {"__builtins__": {}}
                        template["input_example"] = eval(input_example_str, safe_dict)

                elif isinstance(input_example_str, dict):
                    # Already a dict, no conversion needed
                    pass
            except Exception as err:
                logger.error(f"Failed to parse input_example for template: {err}")
                logger.error(f"Problematic string (first 500 chars): {str(input_example_str)[:500]}")
                # Keep the original string if parsing fails
                template["input_example"] = input_example_str
        return templates

    except Exception as e:
        logger.error(f"Error creating model configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching templates: {str(e)}")


@router.post("/run")
async def run_template(request: TemplateRunRequest):
    """
    Run a template with the given inputs.

    This endpoint runs a template with the given inputs and returns the output.

    Returns:
        The result of running the template
    """
    try:
        logger.info(f"Running template: {request.templateName}")

        data_gen_template.list()
        template = data_gen_template.get(request.templateName)
        result = await template.run(**request.inputs)
        # data_factory.run(result)
        for i in range(len(result)):
            result[i]["id"] = i
        return result

    except Exception as e:
        logger.error(f"Error running template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running template: {str(e)}")
