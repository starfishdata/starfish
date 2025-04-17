<p align="center">
  <img src="https://github.com/user-attachments/assets/3bec9453-0581-4d33-acbd-0f4e6954d8c8" alt="Starfish Logo" width="200"/>
</p>
<h1 align="center">Starfish</h1>
<h2 align="center" style="font-size: 20px; margin-bottom: 10px">Synthetic Data Generation Made Easy</h2>


## Overview

Starfish is a Python library that helps you build synthetic data your way. We adapt to your workflow—not the other way around. By combining structured LLM outputs with efficient parallel processing, Starfish lets you define exactly how your data should look and scale seamlessly from experiments to production.
   
⭐ Star us on GitHub if you find this project useful!

Key Features:
- **Structured Outputs**: First-class support for structured data through JSON schemas or Pydantic models.
- **Model Flexibility**: Use any LLM provider—local models, OpenAI, Anthropic, or your own implementation via LiteLLM.
- **Dynamic Prompts**: Dynamic prompts with built-in Jinja2 templates.
- **Easy Scaling**: Transform any function to run in parallel across thousands of inputs with a single decorator.
- **Resilient Pipeline**: Automatic retries, error handling, and job resumption—pause and continue your data generation anytime.
- **Complete Control**: Share state across your pipeline, extend functionality with custom hooks.

## Installation

```bash
pip install starfish-core
```

## Configuration

Starfish uses environment variables for configuration. We provide a `.env.template` file to help you get started quickly:

```bash
# Copy the template to .env
cp .env.template .env

# Edit with your API keys and configuration
nano .env  # or use your preferred editor
```

The template includes settings for API keys, model configurations, and other runtime parameters.

## Quick Start

### Structured LLM - Type-Safe Outputs from Any Model

```python
# 1. Define structured outputs with schema
from starfish import StructuredLLM
from pydantic import BaseModel

# Option A: Use Pydantic for type safety
class QnASchema(BaseModel):
    question: str
    answer: str

# Option B: Or use simple JSON schema
json_schema = [
    {'name': 'question', 'type': 'str'},
    {'name': 'answer', 'type': 'str'}, 
]

# 2. Create a structured LLM with your preferred output format
qna_llm = StructuredLLM(
    model_name="openai/gpt-4o-mini",
    prompt="Generate facts about {{city}}",
    output_schema=QnASchema  # or json_schema
)

# 3. Get structured responses
response = await qna_llm.run(city="San Francisco")

# Access typed data
print(response.data)
# [{'question': 'What is the iconic symbol of San Francisco?',
#   'answer': 'The Golden Gate Bridge is the iconic symbol of San Francisco, completed in 1937.'}]

# Access raw API response for complete flexibility
print(response.raw)  # Full API object with function calls, reasoning tokens, etc.
```

### Data Factory - Scale Any Workflow with One Decorator

```python
# Turn any function into a scalable data pipeline
from typing import Any
from starfish.data_factory.constants import (
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory.factory import data_factory
from starfish.data_factory.utils.state import MutableSharedState

def handle_error(data: Any, state: MutableSharedState):
    """Handle error cases during data processing.

    Args:
        data: The data that caused the error
        state: Shared state object for tracking progress

    Returns:
        str: STATUS_FAILED constant
    """
    return STATUS_FAILED


def handle_record_complete(data: Any, state: MutableSharedState):
    """Handle successful completion of a record.

    Args:
        data: The successfully processed data
        state: Shared state object for tracking progress

    Returns:
        str: STATUS_COMPLETED constant
    """
    # print(f"Record complete: {data}")

    state.set("completed_count", 1)
    state.update({"completed_count": 2})
    return STATUS_COMPLETED


def handle_duplicate_record(data: Any, state: MutableSharedState):
    """Handle duplicate record detection.

    Args:
        data: The duplicate data record
        state: Shared state object for tracking progress

    Returns:
        str: Either STATUS_COMPLETED or STATUS_DUPLICATE based on random chance
    """
    # any any key-value pair in the state.
    state.set("completed_count", 1)
    state.update({"completed_count": 2})
    return STATUS_DUPLICATE

# Works with any function - simple or complex workflows
@data_factory(
    storage=STORAGE_TYPE_LOCAL,
    max_concurrency=50,
    initial_state_values={},
    on_record_complete=[handle_record_complete, handle_duplicate_record],
    on_record_error=[handle_error],
    show_progress=True,
    task_runner_timeout=60,
)
async def parallel_qna_llm(city):
    # This could be any arbitrary complex workflow:
    # - Pre-processing
    # - Multiple LLM calls
    # - Post-processing
    # - Error handling
    response = await qna_llm.run(city=city)
    return response.data

# Process 100 cities with 50 concurrent workers - finishes in seconds
cities = ["San Francisco", "New York", "Tokyo", "Paris", "London"] * 20
results = parallel_qna_llm.run(city=cities)
# dry run to test the workflow and data
results = parallel_qna_llm.dry_run(
        ccity=cities
    )
# re-run job which pick up from where it left off.
results = parallel_qna_llm.re_run(master_job_id="8e07b4e8-4d4a-4355-82c3-04a5391ddbf5")
```

## Documentation

Comprehensive documentation is on the way!

## Contributing

We'd love your help making Starfish better! Whether you're fixing bugs, adding features, or improving documentation, your contributions are welcome.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Contribution guidelines coming soon!

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions or feedback, feel free to reach out to us at [founders@starfishdata.ai](mailto:founders@starfishdata.ai).

## Citation

If you use Starfish in your research, please consider citing us!

```
@software{starfish,
  author = {Wendao, John, Ayush},
  title = {{Starfish: A Tool for Synthetic Data Generation}},
  year = {2025},
  url = {https://github.com/starfishdata/starfish},
}
```

