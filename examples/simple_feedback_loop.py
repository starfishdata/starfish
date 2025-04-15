from datetime import datetime
from typing import Dict, Optional

from starfish import StructuredLLM, data_factory
from starfish.data_factory.constants import RECORD_STATUS
from starfish.data_factory.utils.enums import RecordStatus

# Create a StructuredLLM instance for city information generation
city_facts_llm = StructuredLLM(
    model_name="openai/gpt-4o-mini",
    prompt="""
    Generate comprehensive and interesting facts about {{city_name}}.
    Include historical information, famous landmarks, cultural significance, and notable events.

    {% if feedback %}
    Previous attempt received a score of {{score}}/10 with the following feedback:
    {{feedback}}

    Please address this feedback and improve your response.
    {% endif %}

    Make your response detailed, accurate, and engaging.
    """,
    output_schema=[
        {"name": "historical_info", "type": "str"},
        {"name": "landmarks", "type": "str"},
        {"name": "cultural_significance", "type": "str"},
        {"name": "notable_events", "type": "str"},
        {"name": "additional_info", "type": "str"},
    ],
    model_kwargs={"temperature": 0.7},
)

# Create a StructuredLLM instance for scoring and feedback
scoring_llm = StructuredLLM(
    model_name="openai/gpt-4o-mini",
    prompt="""
    Evaluate the following city information about {{city_name}}:

    Historical Information: {{historical_info}}
    Famous Landmarks: {{landmarks}}
    Cultural Significance: {{cultural_significance}}
    Notable Events: {{notable_events}}
    Additional Information: {{additional_info}}

    Score this information from 1 to 10 based on:
    1. Comprehensiveness (does it cover all important aspects?)
    2. Accuracy (is the information correct?)
    3. Engagement (is it interesting and well-written?)
    4. Uniqueness (does it provide insights not commonly known?)

    Provide a score and detailed feedback for improvement if the score is less than 10.
    """,
    output_schema=[{"name": "score", "type": "int"}, {"name": "feedback", "type": "str"}, {"name": "explanation", "type": "str"}],
    model_kwargs={"temperature": 0.3},
)


async def generate_city_facts(city_name: str, feedback: Optional[str] = None, score: Optional[int] = None) -> Dict:
    """Generate facts about a city."""
    try:
        response = await city_facts_llm.run(city_name=city_name, feedback=feedback, score=score)

        if not response.data:
            raise ValueError("No data returned from LLM")

        return response.data[0]
    except Exception as e:
        raise Exception(f"Error generating city facts: {str(e)}")


async def evaluate_city_facts(city_name: str, facts: Dict) -> Dict:
    """Evaluate the generated facts."""
    try:
        response = await scoring_llm.run(
            city_name=city_name,
            historical_info=facts.get("historical_info", ""),
            landmarks=facts.get("landmarks", ""),
            cultural_significance=facts.get("cultural_significance", ""),
            notable_events=facts.get("notable_events", ""),
            additional_info=facts.get("additional_info", ""),
        )

        if not response.data:
            raise ValueError("No data returned from LLM")

        return response.data[0]
    except Exception as e:
        raise Exception(f"Error evaluating city facts: {str(e)}")


@data_factory(max_concurrency=5)
async def process_city_facts(city_name: str, max_attempts: int = 5):
    """Process city facts with feedback loop."""
    print(f"\nProcessing facts for {city_name}...")

    facts = None
    score = 0
    feedback = None
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        print(f"\nAttempt {attempts}/{max_attempts}")

        try:
            # Generate facts
            facts = await generate_city_facts(city_name, feedback, score)
            print("\nGenerated Facts:")
            for key, value in facts.items():
                print(f"{key}: {value}")

            # Evaluate facts
            evaluation = await evaluate_city_facts(city_name, facts)
            score = evaluation.get("score", 0)
            feedback = evaluation.get("feedback", "")
            explanation = evaluation.get("explanation", "")

            print("\nEvaluation:")
            print(f"Score: {score}/10")
            print(f"Feedback: {feedback}")
            print(f"Explanation: {explanation}")

            # If we got a perfect score, we're done
            if score > 8:
                print("\nReally good score!")
                break

        except Exception as e:
            print(f"Error: {str(e)}")
            return {RECORD_STATUS: RecordStatus.FAILED, "error": str(e)}

    if not facts:
        return {RECORD_STATUS: RecordStatus.FAILED, "error": "Failed to generate city facts"}

    return {RECORD_STATUS: RecordStatus.COMPLETED, "output_ref": facts, "final_score": score, "attempts": attempts}


# Test the function
if __name__ == "__main__":
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Starting simple feedback loop test")

    # List of cities to process
    cities = ["San Francisco", "New York", "Tokyo", "Paris", "Sydney"]

    results = process_city_facts.run(city_name=cities)

    # Print results for each city
    for city, result in zip(cities, results):
        print(f"\nResults for {city}:")
        print(f"Status: {result.get('status')}")
        if result.get("status") == RecordStatus.COMPLETED:
            print("\nCity Facts:")
            for key, value in result["output_ref"].items():
                print(f"{key}: {value}")
            print(f"\nFinal Score: {result.get('final_score')}")
            print(f"Attempts: {result.get('attempts')}")
        else:
            print(f"Error: {result.get('error')}")

    print(f"\n{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Finished simple feedback loop test")
