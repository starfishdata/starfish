# Complete prompts that need no additional template text
COMPLETE_PROMPTS = {
    "data_gen": """
You are a data generation expert. Your primary objective is to create
high-quality synthetic data that strictly adheres to the provided guidelines.

The user has provided specific instructions for data generation.
    - Carefully analyze the given instructions.
    - Ensure the generated data aligns with the specified requirements.
    - Maintain accuracy, coherence, and logical consistency.
user_instruction: {{user_instruction}}

{% if good_examples %}
The user has provided high-quality reference examples.
    - Identify patterns, structures, and key characteristics from these examples.
    - Generate data that maintains a similar style, quality, and relevance.
    - Ensure variations while preserving meaningful consistency.
    good_examples: {{good_examples}}
{% endif %}

{% if bad_examples %}
The following examples represent poor-quality data.
    - Avoid replicating errors, inconsistencies, or undesirable patterns.
    - Ensure generated data is free from the flaws present in these examples.
    bad_examples: {{bad_examples}}
{% endif %}

{% if duplicate_examples %}
The user has specified examples that should not be duplicated.
    - Ensure the generated data remains unique and does not replicate these examples.
    - Introduce meaningful variations while maintaining quality and consistency.
    duplicate_examples: {{duplicate_examples}}
{% endif %}

{% if topic %}
The generated data should be contextually relevant to the given topic: '{{topic}}'.
    - Maintain thematic consistency.
    - Ensure factual accuracy where applicable.
{% endif %}

Generate unique and high-quality data points.
- Ensure diversity in the dataset while maintaining coherence.
- Avoid redundant or repetitive entries.
""",
}

# Partial prompts that need to be combined with user-provided content
PARTIAL_PROMPTS = {
    "data_gen": {
        "header": """You are a data generation expert. Your primary objective is to create
high-quality synthetic data that strictly adheres to the provided guidelines.""",
        "footer": """
       Generate unique and high-quality data points.
        - Ensure diversity in the dataset while maintaining coherence.
        - Avoid redundant or repetitive entries.
        """,
    },
}

# QA pair generation prompt
qa_generation = """
    Create {num_pairs} question-answer pairs from this text for LLM training.
    
    Rules:
    1. Questions must be about important facts in the text
    2. Answers must be directly supported by the text
    3. Return JSON format only:
    
    [
      {{
        "question": "Question 1?",
        "answer": "Answer 1."
      }},
      {{
        "question": "Question 2?",
        "answer": "Answer 2."
      }}
    ]
    
    Text:
    {text}

"""
