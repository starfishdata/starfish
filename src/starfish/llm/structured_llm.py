from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel

from starfish.llm.parser import JSONParser, PydanticParser
from starfish.llm.prompt import PromptManager, get_partial_prompt
from starfish.llm.proxy.litellm_adapter import call_chat_model
from starfish.llm.utils import to_sync

T = TypeVar("T")


class LLMResponse(Generic[T]):
    """Container for LLM response with both raw response and parsed data."""

    def __init__(self, raw_response: Any, parsed_data: Optional[T] = None):
        self.raw = raw_response
        self.data = parsed_data

    def __repr__(self) -> str:
        return f"LLMResponse(raw={type(self.raw)}, data={type(self.data) if self.data else None})"


class StructuredLLM:
    """A builder for LLM-powered functions that can be called with custom parameters.

    This class creates a callable object that handles:
    - Jinja template rendering with dynamic parameters
    - LLM API calls
    - Response parsing according to provided schema

    Provides async (`run`, `__call__`) and sync (`run_sync`) execution methods.
    Use `process_list_input=True` in run methods to process a list argument.

    Note: The prompt parameter accepts both Jinja2 templates and Python f-string-like
    syntax with single braces {variable}. Single braces are automatically converted
    to proper Jinja2 syntax with double braces {{ variable }}. This feature simplifies
    template writing for users familiar with Python's f-string syntax.
    """

    def __init__(
        self,
        model_name: str,
        prompt: str,
        model_kwargs: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Union[List[Dict[str, Any]], Dict[str, Any], type]] = None,
        prompt_template: Optional[str] = None,
        strict_parsing: bool = False,
        type_check: bool = False,
    ):
        """Initialize the LLM builder.

        Args:
            model_name: Name of the LLM model to use (e.g., 'openai/gpt-4o-mini')
            prompt: Template string in either Jinja2 format or Python-style single-brace format.
                   Single-brace format like "Hello {name}" will be automatically converted to
                   Jinja2 format "Hello {{ name }}". Existing Jinja2 templates are preserved.
            model_kwargs: Additional arguments to pass to the LLM
            output_schema: Schema for response parsing (JSON list/dict or Pydantic model)
            prompt_template: Optional name of partial prompt template to wrap around the prompt
            strict_parsing: If True, raise errors on parsing failures. If False, return None for data
            type_check: If True, check field types against schema. If False, skip type validation.
        """
        # Model settings
        self.model_name = model_name
        self.model_kwargs = model_kwargs or {}

        # Initialize prompt manager
        if prompt_template:
            self.prompt_manager = get_partial_prompt(prompt_name=prompt_template, template_str=prompt)
        else:
            self.prompt_manager = PromptManager(prompt)

        # Extract template variables
        self.prompt_variables = self.prompt_manager.get_all_variables()
        self.required_prompt_variables = self.prompt_manager.get_required_variables()
        self.optional_prompt_variables = self.prompt_manager.get_optional_variables()
        self.prompt = self.prompt_manager.get_prompt()

        # Schema processing
        self.output_schema = output_schema
        self.strict_parsing = strict_parsing
        self.type_check = type_check
        self.is_pydantic = isinstance(output_schema, type) and issubclass(output_schema, BaseModel)

        if self.output_schema:
            if self.is_pydantic:
                self.json_schema = PydanticParser.to_json_schema(output_schema)
            else:
                self.json_schema = JSONParser.convert_to_schema(output_schema)

    def _get_schema_instructions(self) -> Optional[str]:
        """Get formatted schema instructions if schema is provided."""
        if not self.output_schema:
            return None

        if self.is_pydantic:
            return PydanticParser.get_format_instructions(self.output_schema)
        return JSONParser.get_format_instructions(self.json_schema)

    async def __call__(self, **kwargs) -> LLMResponse:
        """A convenience wrapper around the run() method."""
        return await self.run(**kwargs)

    def _prepare_prompt_inputs(self, **kwargs) -> Dict[str, Any]:
        """Prepare the prompt input for the LLM."""
        # Filter keys that are in prompt_variables
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in self.prompt_variables}

        # Add schema instructions if available
        schema_str = self._get_schema_instructions()
        if schema_str:
            filtered_kwargs["schema_instruction"] = schema_str

        return filtered_kwargs

    def render_prompt(self, **kwargs) -> str:
        # Add schema instructions if needed
        prompt_inputs = self._prepare_prompt_inputs(**kwargs)
        # Render the prompt template
        try:
            messages = self.prompt_manager.construct_messages(prompt_inputs)
        except ValueError as e:
            raise ValueError(f"Error rendering prompt template: {str(e)}")
        return messages

    def render_prompt_printable(self, **kwargs) -> str:
        """Print the prompt template with the provided parameters."""
        messages = self.render_prompt(**kwargs)
        return self.prompt_manager.get_printable_messages(messages)

    async def run(self, **kwargs) -> LLMResponse:
        """Main async method to run the LLM with the provided parameters."""
        # Render the prompt template
        messages = self.render_prompt(**kwargs)

        # Call the LLM
        raw_response = await call_chat_model(model_name=self.model_name, messages=messages, model_kwargs=self.model_kwargs)

        # Parse the response
        response_text = raw_response.choices[0].message.content
        if not self.output_schema:
            return LLMResponse(raw_response, response_text)

        parsed_data = JSONParser.parse_llm_output(response_text, schema=self.json_schema, strict=self.strict_parsing, type_check=self.type_check)

        return LLMResponse(raw_response, parsed_data)

    @to_sync
    async def run_sync(self, **kwargs) -> LLMResponse:
        """Synchronously call the LLM with the provided parameters.

        When used in Jupyter notebooks, make sure to apply nest_asyncio.
        """
        return await self.run(**kwargs)
