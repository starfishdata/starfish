# Google Colab Version
[Open this notebook in Google Colab](https://colab.research.google.com/github/starfishdata/starfish/blob/main/examples/usecases/math_data_gen.ipynb)

# Strategy

#### Step 0: Topic Generation
**What:** Generate focused math topics (e.g., modular arithmetic, binomial coefficients).  
**Why:** Ensures diverse domain coverage across AIME-style questions.

#### Step 1: Problem Generation
**What:** Generate an AIME-style math problem for each topic.  
**Why:** Keeps problem structure realistic and solvable in 3–6 steps.

#### Step 3: Long CoT Generation
**What:** Use a large reasoning model to generate detailed reasoning.  
**Why:** Captures rich logical steps for use in training or Mix Distillation.

#### Step 4: Python Code Generation + Verification + Execution
**What:** Convert CoT + problem to Python code, verify the Python code and generate feedback on it; regenerate and execute it, and compare result to final answer.  
**Why:** Ensures strict correctness without relying on model judgment.

#### Step 5: Feedback and Rewrite (if failed for each)
**What:** If CoT fails verification, generate a revised version using feedback.  
**Why:** Improves clarity and correctness while preserving reasoning structure.

**Note:** We'll be generating 4 short CoT for every Long CoT to ensure mixed distillation as per [this paper](https://arxiv.org/pdf/2502.12143). These steps will be added later as this pipeline is still a work in progress.

# Implementation

## Starfish pull from pip

```python
pip install starfish-core
```

## Other packages

```python
pip install openai-agents
```

```python
!pip install datasets
```

## Main

```python
import nest_asyncio
from starfish import data_factory, StructuredLLM
import os
from agents import Agent, Runner, function_tool, ModelSettings
from agents.agent_output import AgentOutputSchema
from pydantic import BaseModel

nest_asyncio.apply()
```

```python
model_name_used = 'openai/gpt-4.1-mini'
reasoning_model = 'o4-mini'
CONCURRENCY = 50
TASK_RUNNER_TIMEOUT = 500

class CoTSchema(BaseModel):
    problem: str
    topic: str
    answer: str
    reasoning: str

class CodeExecutorSchema(BaseModel):
    verified: str
    correct_answer: str
    topic: str
    problem: str
    code: str
    reasoning: str

class CodeGeneratorSchema(BaseModel):
    generated_code: str
    explanation: str

class CodeCritiqueSchema(BaseModel):
    critique: str
    alignment_issues: list[str]
    edge_cases_missing: list[str]
    complexity_assessment: str

class CodeRegeneratorSchema(BaseModel):
    improved_code: str
    improvements_made: list[str]

class FeedbackAndRewriteSchema(BaseModel):
    topic: str
    problem: str
    reasoning: str

@data_factory(max_concurrency=CONCURRENCY)
async def generate_topic(num_records):
    prompt = """
    List unique math topics that are commonly tested on AIME (American Invitational Mathematics Examination) problems.
    Focus on areas that appear frequently in recent years, especially 2020–2025.
    Include both core topics and more niche subtopics.
    """
    model = StructuredLLM(
        model_name=model_name_used,
        prompt=prompt,
        output_schema=[{"name": "topic", "type": "str", "required": True}]
    )
    return (await model.run(num_records=num_records)).data

@data_factory(max_concurrency=CONCURRENCY)
async def generate_problem(topic):
    prompt = """
Create a AIME-style math competition problem in the topic of {{topic}}.

Requirements:

1. The problem should be original and adhere to AIME difficulty (appropriate for high school students aiming for USAMO qualification).
2. It must be solvable in 3 to 6 logical steps, without requiring computational brute force.
3. Emphasize creativity, clean setup, and an elegant path to the solution.
4. Use clear and concise language. No extraneous details.
5. Do not include the answer or any solution steps.
6. Return only the problem text.
    """
    model = StructuredLLM(
        model_name=model_name_used,
        prompt=prompt,
        output_schema=[{"name": "problem", "type": "str", "required": True}, {"name": "topic", "type": "str", "required": True}]
    )
    return (await model.run(topic=topic)).data

@data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
async def answer_long_cot(problem, topic):
    prompt = f"""Solve the following problem using a detailed, step-by-step chain of thought.
    Carefully explain each step of your reasoning, include any necessary formulas or theorems,
    and conclude clearly with your final result.

    Problem: {problem}

    Final Answer:"""

    my_agent = Agent(
      name="Problem solver",
      output_type=CoTSchema,
      model=reasoning_model,
      # model_settings=ModelSettings(reasoning={"summary": "detailed"}),
    )

    sample_run = await Runner.run(
      my_agent,
      input=prompt
    )

    print(sample_run)

    output = sample_run.final_output.model_dump()
    output["cot_type"] = "long"
    output["topic"] = topic
    return [output]


@function_tool
def execute_python_code(code: str):
    local_vars = {}
    exec(code, {}, local_vars)
    verified = local_vars.get("verified", None)
    correct_solution = local_vars.get("correct_solution", None)
    return {"verified": bool(verified), "correct_solution": correct_solution}

@data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
async def data_factory_execute_cot_as_code(answer, topic, problem, cot_type, reasoning):
  return await execute_cot_as_code(answer, topic, problem, cot_type, reasoning)

async def execute_cot_as_code(answer, topic, problem, cot_type, reasoning):
    # Step 1: Generate initial code from problem and CoT
    initial_code_prompt = f"""
    You are an expert Python developer tasked with converting an AIME-style math problem and its solution reasoning into executable Python code.

    Problem:
    {problem}

    Chain of Thought Solution:
    {reasoning}

    Write complete, correct Python code that implements this solution. The code should:
    - Follow the exact reasoning steps shown in the Chain of Thought
    - Use appropriate Python libraries (math, itertools, etc.) if needed
    - Include comments explaining key steps
    - Be mathematically rigorous without shortcuts
    """

    code_generator = Agent(
        name="Code Generator",
        output_type=CodeGeneratorSchema,
        model=reasoning_model
    )

    initial_code_run = await Runner.run(
        code_generator,
        input=initial_code_prompt
    )
    initial_code = initial_code_run.final_output.generated_code

    critique_prompt = f"""
    Analyze the following Python code that solves an AIME math problem.
    Evaluate it for:
    1. Alignment with the original chain of thought reasoning
    2. Mathematical rigor and absence of shortcuts
    3. Missing edge cases or assumptions
    4. Appropriate complexity level for an AIME problem

    Problem:
    {problem}

    Original Chain of Thought:
    {reasoning}

    Generated Code:
    {initial_code}
    """

    code_critic = Agent(
        name="Code Critic",
        output_type=CodeCritiqueSchema,
        model=reasoning_model
    )

    critique_run = await Runner.run(
        code_critic,
        input=critique_prompt
    )
    critique = critique_run.final_output

    # Step 3: Regenerate improved code based on critique
    regenerate_prompt = f"""
    Improve the following Python code based on the provided critique.
    Generate a new version that addresses all identified issues while maintaining mathematical rigor.

    Original Problem:
    {problem}

    Original Chain of Thought:
    {reasoning}

    Original Code:
    {initial_code}

    Critique:
    {critique.critique}

    Missing Edge Cases:
    {critique.edge_cases_missing}

    Alignment Issues:
    {critique.alignment_issues}

    Generate improved code that:
    1. Addresses all critique points
    2. Maintains alignment with the chain of thought
    3. Handles identified edge cases
    4. Maintains appropriate mathematical rigor
    """

    code_regenerator = Agent(
        name="Code Regenerator",
        output_type=CodeRegeneratorSchema,
        model=reasoning_model
    )

    regenerate_run = await Runner.run(
        code_regenerator,
        input=regenerate_prompt
    )
    final_code = regenerate_run.final_output.improved_code

    execute_prompt = f"""
    You are an expert Python developer tasked with converting AIME-style math problems into complete, correct, and executable Python code.

    Requirements:
    - Use the provided improved code implementation
    - Ensure the final result is assigned to `correct_solution`
    - Compare `correct_solution` to the expected value `{answer}` and set `verified = True` if they match, else `False`

    Problem:
    {problem}

    Improved Implementation:
    {final_code}
    """

    my_agent = Agent(
        name="Tool caller",
        output_type=CodeExecutorSchema,
        tools=[execute_python_code],
        model=reasoning_model,
        model_settings=ModelSettings(tool_choice="required"),
    )

    sample_run = await Runner.run(
        my_agent,
        input=execute_prompt
    )

    output = sample_run.final_output.model_dump()
    output['problem'] = problem
    output['cot_type'] = cot_type
    output["topic"] = topic
    output["reasoning"] = reasoning
    return [output]

@data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
async def feedback_and_rewrite(topic, problem, reasoning, verified, correct_answer, cot_type, code):
    prompt = f"""
    Review the problem and the current solution attempt below.

    First, evaluate whether the reasoning in the solution leads to the correct answer. If it does not, identify any mistakes or incorrect steps. Then, rewrite the solution so that the logic is accurate and clearly leads to the correct, verified answer.

    Your rewritten solution should maintain a step-by-step explanation and ensure the final result matches the Correct Answer.

    Problem: {problem}
    Current Reasoning: {reasoning}
    Verified Correct Answer: {correct_answer}
    """
    my_agent = Agent(
      name="Feedback and Rewrite",
      output_type=FeedbackAndRewriteSchema,
      model=reasoning_model,
    )

    sample_run = await Runner.run(
      my_agent,
      input=prompt
    )

    output = sample_run.final_output.model_dump()

    feedbacked_output = await execute_cot_as_code(
        topic=topic,
        problem=problem,
        answer=correct_answer,
        cot_type=cot_type,
        reasoning=output["reasoning"],
    )
    return feedbacked_output
```

# Playground

```python
topics = generate_topic.run(num_records=110)
```

```python
problems = generate_problem.run(topics)
```

```python
reasoning = answer_long_cot.run(problems)
```

```python
code_execution = data_factory_execute_cot_as_code.run(reasoning)
```

```python
all_re_written_cots = []

unverified_entries = [entry for entry in code_execution if entry.get("verified") == "False"]

verified_entries = [entry for entry in code_execution if entry.get("verified") == "True"]

if unverified_entries:
    # Run feedback and rewrite on the current batch of unverified entries
    rewritten_batch = feedback_and_rewrite.run(unverified_entries)

    # Collect verified rewrites
    verified_batch = [rewritten for rewritten in rewritten_batch if rewritten.get("verified") == "True"]
    all_re_written_cots.extend(verified_batch)

    # Remove verified entries from the current unverified list
    unverified_entries = [rewritten for rewritten in rewritten_batch if rewritten.get("verified") == "False"]

verified_entries = verified_entries + all_re_written_cots
print(verified_entries)
```



### Step 0: Topic Generation
- **Description:** Generate focused math topics.
- **Code:**
```python
@data_factory(max_concurrency=CONCURRENCY)
async def generate_topic(num_records):
    prompt = """
    List unique math topics that are commonly tested on AIME (American Invitational Mathematics Examination) problems.
    Focus on areas that appear frequently in recent years, especially 2020–2025.
    Include both core topics and more niche subtopics.
    """
    model = StructuredLLM(
        model_name=model_name_used,
        prompt=prompt,
        output_schema=[{"name": "topic", "type": "str", "required": True}]
    )
    return (await model.run(num_records=num_records)).data
```

### Step 1: Problem Generation
- **Description:** Generate an AIME-style math problem.
- **Code:**
```python
@data_factory(max_concurrency=CONCURRENCY)
async def generate_problem(topic):
    prompt = """
    Create a AIME-style math competition problem in the topic of {{topic}}.
    """
    model = StructuredLLM(
        model_name=model_name_used,
        prompt=prompt,
        output_schema=[{"name": "problem", "type": "str", "required": True}, {"name": "topic", "type": "str", "required": True}]
    )
    return (await model.run(topic=topic)).data
```

### Step 3: Long CoT Generation
- **Description:** Generate detailed reasoning using a reasoning model.
- **Code:**
```python
@data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
async def answer_long_cot(problem, topic):
    prompt = f"""Solve the following problem using a detailed, step-by-step chain of thought.
    """
    my_agent = Agent(
    name="Problem solver",
    output_type=CoTSchema,
    model=reasoning_model,
    )
    sample_run = await Runner.run(
    my_agent,
    input=prompt
    )
    output = sample_run.final_output.model_dump()
    output["cot_type"] = "long"
    output["topic"] = topic
    return [output]
```

### Step 4: Python Code Generation, Verification, Execution
- **Description:** Convert CoT + problem to Python code, verify, and execute.
- **Code:**
```python
async def execute_cot_as_code(answer, topic, problem, cot_type, reasoning):
    initial_code_prompt = f"""
    You are an expert Python developer tasked with converting an AIME-style math problem and its solution reasoning into executable Python code.
    """
    code_generator = Agent(
        name="Code Generator",
        output_type=CodeGeneratorSchema,
        model=reasoning_model
    )
    initial_code_run = await Runner.run(
        code_generator,
        input=initial_code_prompt
    )
    final_code = regenerate_run.final_output.improved_code
    execute_prompt = f"""
    You are an expert Python developer tasked with converting AIME-style math problems into complete, correct, and executable Python code.
    """
    my_agent = Agent(
        name="Tool caller",
        output_type=CodeExecutorSchema,
        tools=[execute_python_code],
        model=reasoning_model,
    )
    sample_run = await Runner.run(
        my_agent,
        input=execute_prompt
    )
    output = sample_run.final_output.model_dump()
    output['problem'] = problem
    output['cot_type'] = cot_type
    output["topic"] = topic
    output["reasoning"] = reasoning
    return [output]
```

### Step 5: Feedback and Rewrite
- **Description:** Generate a revised version if CoT fails verification.
- **Code:**
```python
@data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
async def feedback_and_rewrite(topic, problem, reasoning, verified, correct_answer, cot_type, code):
    prompt = f"""
    Review the problem and the current solution attempt below.
    """
    my_agent = Agent(
    name="Feedback and Rewrite",
    output_type=FeedbackAndRewriteSchema,
    model=reasoning_model,
    )
    sample_run = await Runner.run(
    my_agent,
    input=prompt
    )
    output = sample_run.final_output.model_dump()
    feedbacked_output = await execute_cot_as_code(
        topic=topic,
        problem=problem,
        answer=correct_answer,
        cot_type=cot_type,
        reasoning=output["reasoning"],
    )
    return feedbacked_output
```