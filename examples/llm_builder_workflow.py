from typing import Any, Dict, List

from starfish import data_factory, llm_builder
from starfish.utils import merge_structured_outputs

# llm_builder
# is a support function that can help to generate structure data super easily.
# it has three component:
# 1. model_name: online model it support all the model litellm support and we also support all openai format compatible model and support Hyperbolic out of box. For local model, we support all model that can be hosted through ollama. if user specific model that start with ollama it will download from ollama and host by ollama, and if user specify model that with huggingface it will download from ollama and host through ollama. all being down automatically.
# 2. prompt: jinja prompt managment support highly flexible prompt, if else and more advanced prompt.
# 3. output_schema: support simple name, type, description, required format and also pydantic format.

# Workflow
# we can easily chain multiple llm_builder together, please note you can link pretty much arbitray workflow and here are just using the convient llm_builder to generate structure output more effectively

#  Data factory
#  We have this DataFactory decorator that will turn this workflow to parallize to run to generate 1000 of data points and essentially the job of datafactory is to help to manage how to distribute the work and also provide the storage option.
# We've also provide a lot of call backs for flexibility.
# By adding the dectorator you now have a fully paralleization of the data factory that will produce 1000 of these data in very effeicent manner


@data_factory(storage="local", batch_size=5)
def generate_city_info(cities: List[str], num_facts: int) -> List[Dict[str, Any]]:
    """LLM-powered city fact generation pipeline with validation"""
    results = []

    for city in cities:
        try:
            # First LLM: Fact Generation
            fact_llm = llm_builder(
                model_name="openai/gpt-4",
                prompt="Generate {{num_facts}} authentic facts about {{city}}",
                output_schema=[{"name": "fact_id", "type": "int"}, {"name": "content", "type": "str"}, {"name": "category", "type": "str"}],
                temperature=0.7,
            )

            facts = fact_llm.run(city=city, num_facts=num_facts).data

            # Second LLM: Fact Validation
            validation_llm = llm_builder(
                model_name="anthropic/claude-3",
                prompt="""Analyze these city facts and provide:
                1. Accuracy score (0-10)
                2. Potential sources for verification
                3. Confidence level (0-1)
                Facts: {{data}}""",
                output_schema=[{"name": "accuracy_score", "type": "float"}, {"name": "sources", "type": "List[str]"}, {"name": "confidence", "type": "float"}],
                max_tokens=500,
            )

            validation = validation_llm.run(data=facts).data

            # Merge structured outputs
            merged_data = merge_structured_outputs(facts, validation)

            # Add city context
            for item in merged_data:
                item["city"] = city
                item["num_facts_requested"] = num_facts

            results.extend(merged_data)

        except Exception as e:
            # Error handling with context preservation
            error_data = {
                "city": city,
                "error": str(e),
                "error_phase": "generation" if not locals().get("validation") else "validation",
                "partial_data": locals().get("facts", None),
            }
            results.append(error_data)
            continue

    return results


# Add performance monitoring callback
def monitor_batch(metrics: Dict):
    print(f"Batch processed - Cities: {metrics['city_count']} | Facts: {metrics['total_facts']}")


generate_city_info.add_callback("on_batch_complete", monitor_batch)

# Example execution
if __name__ == "__main__":
    dataset = generate_city_info(cities=["Paris", "Tokyo", "San Francisco", "Dubai", "Sydney"], num_facts=5)
