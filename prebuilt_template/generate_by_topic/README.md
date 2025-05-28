
## Overview
The `generate_by_topic` template is designed to create diverse synthetic data across multiple topics based on user instructions. It can automatically generate relevant topics if not provided and handles deduplication across generated content.

## Key Features
- Automatic topic generation based on user instructions
- Customizable number of records and records per topic
- Built-in deduplication mechanism
- Flexible output schema configuration
- Parallel data generation with configurable concurrency

## Input Schema
```python
class GenerateByTopicInput(BaseModel):
    user_instruction: Optional[str] = None
    num_records: Optional[int] = 10
    records_per_topic: int = 10
    topics: Optional[List[Union[str, Dict[str, int]]]] = None
    topic_model_name: str = "openai/gpt-4o-mini"
    topic_model_kwargs: Optional[Dict[str, Any]] = None
    generation_model_name: str = "openai/gpt-4o-mini"
    generation_model_kwargs: Optional[Dict[str, Any]] = None
    output_schema: Optional[Union[List[Dict[str, Any]], Dict[str, Any], type]] = [
        {"name": "question", "type": "str"},
        {"name": "answer", "type": "str"}
    ]
    data_factory_config: Optional[Dict[str, Any]] = {}
```

## Parameters
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `user_instruction` | str | Instruction for data generation | None |
| `num_records` | int | Total number of records to generate | 10 |
| `records_per_topic` | int | Number of records per topic | 10 |
| `topics` | List[Union[str, Dict[str, int]]] | List of topics or topic with specific record count | None |
| `topic_model_name` | str | Model name for topic generation | "openai/gpt-4o-mini" |
| `topic_model_kwargs` | Dict[str, Any] | Additional parameters for topic model | None |
| `generation_model_name` | str | Model name for data generation | "openai/gpt-4o-mini" |
| `generation_model_kwargs` | Dict[str, Any] | Additional parameters for generation model | None |
| `output_schema` | Union[List[Dict[str, Any]], Dict[str, Any], type] | Schema for generated data | [{"name": "question", "type": "str"}, {"name": "answer", "type": "str"}] |
| `data_factory_config` | Dict[str, Any] | Configuration for data generation process | {} |

## Example Usage
```python
{
    "user_instruction": "Generate Q&A pairs about machine learning concepts",
    "num_records": 100,
    "records_per_topic": 5,
    "topics": [
        "supervised learning",
        "unsupervised learning",
        {"reinforcement learning": 3},
        "neural networks",
    ],
    "topic_model_name": "openai/gpt-4",
    "topic_model_kwargs": {"temperature": 0.7},
    "generation_model_name": "openai/gpt-4",
    "generation_model_kwargs": {"temperature": 0.8, "max_tokens": 200},
    "output_schema": [
        {"name": "question", "type": "str"},
        {"name": "answer", "type": "str"},
        {"name": "difficulty", "type": "str"},
    ],
    "data_factory_config": {"max_concurrency": 4, "task_runner_timeout": 60 * 2},
}
```

## Workflow
1. Topic Preparation:
   - If topics are not provided, generates relevant topics based on user instruction
   - Shuffles topics for better distribution and deduplication

2. Data Generation:
   - Generates data for each topic using the specified model
   - Implements deduplication by tracking previously generated examples
   - Adds topic information to each generated record

## Output
The generated data will include:
- Fields specified in the output schema
- An additional `topic` field indicating the topic of each record

## Dependencies
- `starfish` framework
- `pydantic` for input validation


## Sample Run

Check out [`sample_run.ipynb`](./sample_run.ipynb) for a complete example you can run right away.

## Source Implementation

The actual template code is located at:
```
src/starfish/data_gen_template/templates/starfish/generate_by_topic/
```

---

**Try it out!** If you have any questions, let us know - we'd be happy to help. If you like this template, consider starring the repo and building your own! We welcome community contributions and are always happy to chat about new ideas. ⭐ 