import asyncio
import math
from typing import Any, Dict, List, Optional, Union

from starfish import StructuredLLM


async def generate_topics(
    user_instruction: str,
    num_topics: int,
    model_name: str = "openai/gpt-4o-mini",
    model_kwargs: Optional[Dict[str, Any]] = None,
    existing_topics: Optional[List[str]] = None,
) -> List[str]:
    """Generate unique topics based on user instructions using a StructuredLLM model."""
    if model_kwargs is None:
        model_kwargs = {}
    if "temperature" not in model_kwargs:
        model_kwargs["temperature"] = 1
    existing_topics = existing_topics or []

    if num_topics <= 0:
        return []

    # Calculate batches needed (5 topics per batch)
    llm_batch_size = 5
    num_batches = math.ceil(num_topics / llm_batch_size)
    generated_topics = []

    for _ in range(num_batches):
        topic_generator = StructuredLLM(
            model_name=model_name,
            prompt="""Can you generate a list of topics about {{user_instruction}}
                  {% if existing_topics_str %}
                  Please do not generate topics that are already in the list: {{existing_topics_str}}
                  Make sure the topics are unique and vary from each other
                  {% endif %}
                """,
            output_schema=[{"name": "topic", "type": "str"}],
            model_kwargs=model_kwargs,
        )

        all_existing = existing_topics + generated_topics
        input_params = {"user_instruction": user_instruction, "num_records": min(llm_batch_size, num_topics - len(generated_topics))}

        if all_existing:
            input_params["existing_topics_str"] = ",".join(all_existing)

        topic_response = await topic_generator.run(**input_params)
        topic_data = [item.get("topic") for item in topic_response.data]
        generated_topics.extend(topic_data)

        if len(generated_topics) >= num_topics:
            break

    return generated_topics


async def prepare_topic(
    topics: Optional[List[Union[str, Dict[str, int]]]] = None,
    num_records: Optional[int] = None,
    records_per_topic: int = 20,
    user_instruction: Optional[str] = None,
    model_name: str = "openai/gpt-4o-mini",
    model_kwargs: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Split records into topics, generating topics if none are provided or if needed.

    Supported input formats:
    1. String list: ['topic1', 'topic2'] - Topics with equal or calculated distribution
    2. Dict list: [{'topic1': 20}, {'topic2': 30}] - Topics with specific counts
    3. Mixed: ['topic1', {'topic2': 30}] - Combination of both formats
    4. None: No topics provided, will generate based on user_instruction

    Args:
        topics: Optional list of topics, either strings or {topic: count} dicts
        num_records: Total number of records to split (required for dict topics or None topics)
        records_per_topic: Number of records per topic (default: 20)
        user_instruction: Topic generation instructions (required if topics is None)
        model_name: Model name for topic generation
        model_kwargs: Model kwargs for topic generation

    Returns:
        List of {'topic': topic_name} dictionaries, with one entry per record
    """
    if model_kwargs is None:
        model_kwargs = {}
    if "temperature" not in model_kwargs:
        model_kwargs["temperature"] = 1
    # --- STEP 1: Input validation and normalization ---
    if topics is None:
        # Must have num_records and user_instruction if no topics provided
        if not num_records or num_records <= 0:
            raise ValueError("num_records must be positive when topics are not provided")
        if not user_instruction:
            raise ValueError("user_instruction required when topics are not provided")
        topic_assignments = []
    else:
        # Validate topics is a non-empty list
        if not isinstance(topics, list) or not topics:
            raise ValueError("topics must be a non-empty list")

        # Convert all topic inputs to a standardized [(topic_name, count)] list
        # For string topics: count will be None (to be calculated later)
        # For dict topics: use the specified count
        topic_assignments = []
        seen_topics = set()

        for topic in topics:
            if isinstance(topic, str):
                if topic not in seen_topics:
                    topic_assignments.append((topic, None))
                    seen_topics.add(topic)
            elif isinstance(topic, dict) and len(topic) == 1:
                topic_name = next(iter(topic))
                count = topic[topic_name]

                if not isinstance(count, int) or count < 0:
                    raise ValueError(f"Topic '{topic_name}' has invalid count {count}")

                if topic_name not in seen_topics:
                    topic_assignments.append((topic_name, count))
                    seen_topics.add(topic_name)
            else:
                raise ValueError("Topics must be strings or single-key dictionaries")

    # --- STEP 2: Calculate or validate counts for provided topics ---
    result = []
    assigned_count = 0
    topic_names = []  # Track all assigned topic names

    if topic_assignments:
        # Handle string topics with no count (None) - assign counts based on input
        string_topics = [(name, count) for name, count in topic_assignments if count is None]
        dict_topics = [(name, count) for name, count in topic_assignments if count is not None]

        # Case: String topics with no num_records - assign records_per_topic to each
        if string_topics and num_records is None:
            for name, _ in string_topics:
                result.append({name: records_per_topic})
                topic_names.append(name)
                assigned_count += records_per_topic

        # Case: String topics with num_records - distribute evenly
        elif string_topics and num_records is not None:
            remaining = num_records - sum(count for _, count in dict_topics if count is not None)
            if remaining < 0:
                raise ValueError("Dict topic counts exceed num_records")

            # Distribute remaining records among string topics
            if string_topics and remaining > 0:
                base = remaining // len(string_topics)
                extra = remaining % len(string_topics)

                for i, (name, _) in enumerate(string_topics):
                    count = base + (1 if i < extra else 0)
                    if count > 0:
                        result.append({name: count})
                        topic_names.append(name)
                        assigned_count += count

        # Add dictionary topics with predefined counts
        for name, count in dict_topics:
            if count > 0:
                result.append({name: count})
                topic_names.append(name)
                assigned_count += count

        # Validate total count for dictionary topics
        if dict_topics and num_records is None:
            raise ValueError("num_records required when using dictionary topics")

        if num_records is not None and assigned_count > num_records:
            raise ValueError(f"Total assigned count ({assigned_count}) exceeds num_records ({num_records})")

    # --- STEP 3: Generate topics for remaining records if needed ---
    remaining_records = 0 if num_records is None else num_records - assigned_count

    if remaining_records > 0:
        if records_per_topic <= 0:
            raise ValueError("records_per_topic must be positive when generating topics")

        # Generate topics with LLM if instructions provided
        if user_instruction:
            topics_needed = math.ceil(remaining_records / records_per_topic)

            generated = await generate_topics(
                user_instruction=user_instruction, num_topics=topics_needed, model_name=model_name, model_kwargs=model_kwargs, existing_topics=topic_names
            )

            # Assign counts to generated topics
            for topic in generated:
                if topic in topic_names:  # Skip if duplicate (shouldn't happen with proper LLM)
                    print(f"Skipping duplicate generated topic: {topic}")
                    continue

                count = min(records_per_topic, remaining_records)
                if count <= 0:
                    break

                result.append({topic: count})
                topic_names.append(topic)
                remaining_records -= count
                assigned_count += count

        # Generate auto-topics for any still-remaining records
        auto_index = 1
        while remaining_records > 0:
            # Find next available auto_topic name
            auto_name = f"auto_topic{auto_index}"
            while auto_name in topic_names:
                auto_index += 1
                auto_name = f"auto_topic{auto_index}"

            count = min(records_per_topic, remaining_records)
            result.append({auto_name: count})
            topic_names.append(auto_name)
            remaining_records -= count
            assigned_count += count
            auto_index += 1

    # Final validation
    if num_records is not None and assigned_count != num_records:
        print(f"Warning: Assigned {assigned_count} records, expected {num_records}")

    flatten_topic_list = []
    for item in result:
        for key, count in item.items():
            flatten_topic_list.extend([{"topic": key}] * count)

    return flatten_topic_list


if __name__ == "__main__":
    print("--- Running Examples ---")

    # Example 1: Dictionary topics with additional generation
    print("\nExample 1: Dictionary topics + generation")
    topics1 = [{"topic1": 20}, {"topic2": 30}]
    result1 = asyncio.run(prepare_topic(topics=topics1, num_records=100, records_per_topic=25, user_instruction="some context"))
    print(f"Result: {result1}")
    print(f"Total: {len(result1)}")

    # Example 2: String topics with even distribution
    print("\nExample 2: String topics with distribution")
    topics2 = ["topicA", "topicB", "topicC"]
    result2 = asyncio.run(prepare_topic(topics=topics2, num_records=10))
    print(f"Result: {result2}")
    print(f"Total: {len(result2)}")

    # Example 3: Mixed string and dict topics
    print("\nExample 3: Mixed string/dict topics")
    topics3 = ["topicX", {"topicY": 10}]
    result3 = asyncio.run(prepare_topic(topics=topics3, num_records=30, user_instruction="mixed topics"))
    print(f"Result: {result3}")
    print(f"Total: {len(result3)}")

    # Example 4: String topics with fixed count
    print("\nExample 4: String topics with fixed count")
    topics4 = ["apple", "banana", "cherry"]
    result4 = asyncio.run(prepare_topic(topics=topics4, records_per_topic=15))
    print(f"Result: {result4}")
    print(f"Total: {len(result4)}")

    # Example 5: No topics, generate all
    print("\nExample 5: No topics, generate all")

    async def run_example5():
        result = await prepare_topic(topics=None, num_records=10, records_per_topic=5, user_instruction="cloud computing")
        print(f"Result: {result}")
        print(f"Total: {len(result)}")

    asyncio.run(run_example5())

    print("\n--- Examples Finished ---")
