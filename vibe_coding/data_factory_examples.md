# Data Factory Examples

## Google Colab Version

[Open this notebook in Google Colab](https://colab.research.google.com/github/starfishdata/starfish/blob/main/examples/data_factory.ipynb)

## Dependencies

Make sure to install the necessary dependencies.

```python
%pip install starfish-core
```

## Enabling Async Execution

A workaround for enabling async code execution in Jupyter notebooks. Not for production use.

```python
import nest_asyncio
nest_asyncio.apply()
```

## Environment Setup

Load environment variables from `.env` file.

```python
from starfish.common.env_loader import load_env_file
load_env_file()
```

## Example 1: Your First Data Factory: Simple Scaling

The `@data_factory` decorator allows transforming an async function into a scalable data pipeline.

### Create a StructuredLLM instance

```python
json_llm = StructuredLLM(
    model_name = "openai/gpt-4o-mini",
    prompt = "Funny facts about city {{city_name}}.",
    output_schema = [{'name': 'fact', 'type': 'str'}],
    model_kwargs = {"temperature": 0.7},
)
json_llm_response = await json_llm.run(city_name='New York')
json_llm_response.data
```

### Scale with Data Factory

```python
from datetime import datetime
@data_factory(max_concurrency=10)
async def process_json_llm(city_name: str):
    print(f"Processing {city_name} at {datetime.now()}")
    json_llm_response = await json_llm.run(city_name=city_name)
    return json_llm_response.data
process_json_llm.run(city_name=["New York", "London", "Tokyo", "Paris", "Sydney"])
```

## Example 2: Works with any Async Function

Data Factory works with any async function. Here is a chained example:

```python
@data_factory(max_concurrency=10)
async def complex_process_cities(topic: str):
    generator_llm = StructuredLLM(
        model_name="openai/gpt-4o-mini",
        prompt="Generate question/answer pairs about {{topic}}.",
        output_schema=[
            {"name": "question", "type": "str"},
            {"name": "answer", "type": "str"}
        ],
    )

    rater_llm = StructuredLLM(
        model_name="openai/gpt-4o-mini",
        prompt='''Rate the following Q&A pairs based on accuracy and clarity (1-10).\n
        Pairs: {{generated_pairs}}''',
        output_schema=[
            {"name": "accuracy_rating", "type": "int"},
            {"name": "clarity_rating", "type": "int"}
        ],
        model_kwargs={"temperature": 0.5}
    )

    generation_response = await generator_llm.run(topic=topic, num_records=5)
    rating_response = await rater_llm.run(generated_pairs=generation_response.data)
    return merge_structured_outputs(generation_response.data, rating_response.data)

complex_process_cities_data = complex_process_cities.run(topic=['Science', 'History', 'Technology'])
```

## Example 3: Working with Different Input Formats

Data Factory supports various input formats, enhancing flexibility.

```python
@data_factory(max_concurrency=100)
async def input_format_mock_llm(city_name: str, num_records_per_city: int):
    return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.01)

# Example with different input formats.
input_format_data = input_format_mock_llm.run(city_name=["New York", "London"], num_records_per_city=1)
```

## Example 4: Resilient Error Retry

Data Factory handles errors gracefully with retry mechanisms.

```python
async def high_error_rate_mock_llm(city_name: str, num_records_per_city: int):
    return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.3)

cities = ["New York", "London", "Tokyo"] * 5
high_error_rate_mock_llm_data = high_error_rate_mock_llm.run(city_name=cities, num_records_per_city=1)
```

## Advanced Usage

Data Factory offers hooks for customizations and coordination between tasks.

#### Resume
#### 5. Resume

This is essential for long-running jobs with thousands of tasks.

If a job is interrupted, you can pick up where you left off using one of two resume methods:


1. **Same Session Resume**: If you're still in the same session where the job was interrupted, simply call - Same instance with .resume()

2. **Cross-Session Resume**: If you've closed your notebook or lost your session, you can resume using the job ID:
   ```python
   from starfish import DataFactory
   # Resume using the master job ID from a previous run
   data_factory = DataFactory.resume_from_checkpoint(job_id="your_job_id")
   ```

The key difference:
- `resume()` uses the same DataFactory instance you defined
- `resume_from_checkpoint()` reconstructs your DataFactory from persistent storage where tasks and progress are saved

> **Note**: Google Colab users may experience issues with `resume_from_checkpoint()` due to how Colab works

We're simulating an interruption here. In a real scenario, this might happen if your notebook errors out, is manually interrupted with a keyboard command, encounters API rate limits, or experiences any other issues that halt execution.

```python
@data_factory(max_concurrency=10)
async def re_run_mock_llm(city_name: str, num_records_per_city: int):
    return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.3)

cities = ["New York", "London", "Tokyo", "Paris", "Sydney"] * 20  # 100 cities
re_run_mock_llm_data_1 = re_run_mock_llm.run(city_name=cities, num_records_per_city=1)

print("When a job is interrupted, you'll see a message like:")
print("[RESUME INFO] 🚨 Job stopped unexpectedly. You can resume the job by calling .resume()")

print("\nTo resume an interrupted job, simply call:")
print("interrupted_job_mock_llm.resume()")
print('')
print(f"For this example we have {len(re_run_mock_llm_data_1)}/{len(cities)} data generated and not finished yet!")

re_run_mock_llm_data_2 = re_run_mock_llm.resume()

```

#### Dry Run

Before running a large job, you can do a "dry run" to test your pipeline. This only processes a single item and doesn't save state to the database.

```python
@data_factory(max_concurrency=10)
async def dry_run_mock_llm(city_name: str, num_records_per_city: int):
    return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.3)

dry_run_mock_llm_data = dry_run_mock_llm.dry_run(city_name=["New York", "London", "Tokyo", "Paris", "Sydney"]*20, num_records_per_city=1)
```
