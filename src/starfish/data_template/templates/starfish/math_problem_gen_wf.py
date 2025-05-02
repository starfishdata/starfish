from pydantic import BaseModel
from starfish import data_factory
from starfish.data_template.template_gen import data_gen_template

# import nest_asyncio
from starfish import data_factory, StructuredLLM
import os
from agents import Agent, Runner, function_tool
from agents.agent_output import AgentOutputSchema
from pydantic import BaseModel

# nest_asyncio.apply()

model_name_used = "openai/gpt-4.1-mini"
CONCURRENCY = 50
TASK_RUNNER_TIMEOUT = 500


# Define input schema
class TopicGeneratorInput(BaseModel):
    community_name: str
    seed_topics: list[str]
    num_topics: int
    language: str = "en"


# Define output schema
class TopicGeneratorOutput(BaseModel):
    generated_topics: list[str]
    success: bool
    message: str


@data_gen_template.register(
    name="starfish/math_problem_gen_wf",
    input_schema=TopicGeneratorInput,
    # optional
    output_schema=TopicGeneratorOutput,
    description="Generates relevant math problem-solutions using AI models",
    author="Your Name",
    starfish_version="0.1.0",
    dependencies=["posthog>=3.11.0"],
)
def math_problem_gen_wf():
    @data_factory(max_concurrency=CONCURRENCY)
    async def generate_topic(num_records):
        prompt = """
        List unique math topics that are commonly tested on AIME (American Invitational Mathematics Examination) problems.
        Focus on areas that appear frequently in recent years, especially 2020–2025.
        Include both core topics and more niche subtopics.
        """
        model = StructuredLLM(model_name=model_name_used, prompt=prompt, output_schema=[{"name": "topic", "type": "str", "required": True}])
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
            output_schema=[{"name": "problem", "type": "str", "required": True}, {"name": "topic", "type": "str", "required": True}],
        )
        return (await model.run(topic=topic)).data

    # Step 1: Define your desired structured output
    class CoTSchema(BaseModel):
        cot: str
        problem: str
        topic: str
        answer: str

    @data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
    async def answer_long_cot(problem, topic):
        prompt = f"Solve the following problem using detailed, step-by-step reasoning. Conclude with Final Answer: <answer>. Problem: {problem}"

        my_agent = Agent(name="Problem solver with detailed CoT", output_type=CoTSchema)

        sample_run = await Runner.run(my_agent, input=prompt)

        output = sample_run.final_output.model_dump()
        output["cot_type"] = "long"
        output["topic"] = topic
        return [output]

    @data_factory(max_concurrency=CONCURRENCY)
    async def generate_short_cot(problem):
        prompt = f"Solve this problem using concise step-by-step reasoning. End with: Final Answer: <answer>. Problem: {problem}"
        my_agent = Agent(name="Problem solver with concise CoT", output_type=CoTSchema)

        sample_run = await Runner.run(my_agent, input=prompt)

        output = sample_run.final_output.model_dump()
        return [output]

    # Step 1: Define your desired structured output
    class CodeExecutorSchema(BaseModel):
        verified: str
        correct_answer: int
        topic: str
        problem: str
        cot: str

    @function_tool
    def execute_python_code(code: str):
        local_vars = {}
        exec(code, {}, local_vars)
        verified = local_vars.get("verified", None)
        correct_solution = local_vars.get("correct_solution", None)
        return {"verified": bool(verified), "correct_solution": correct_solution}

    @data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
    async def data_factory_execute_cot_as_code(cot, answer, topic, problem, cot_type):
        return await execute_cot_as_code(cot, answer, topic, problem, cot_type)

    async def execute_cot_as_code(cot, answer, topic, problem, cot_type):
        prompt = f"""
        Convert the following AIME-style math problem into precise, correct, and executable Python code.

        Instructions:
        - Implement a complete solution that rigorously follows all mathematical constraints.
        - Use Python libraries such as `itertools`, `math`, or `collections` when appropriate.
        - If the problem involves enumeration, number theory, or digit-based logic, handle all edge cases carefully and thoroughly.
        - Avoid floating-point operations when integer accuracy is required.
        - Assign the final result to a variable named `correct_solution`.
        - Compare `correct_solution` against the expected value `{answer}` and set `verified = True` if they match, otherwise `False`.

        After writing the code, call the tool to execute it.

        Problem:
        {problem}
        """

        my_agent = Agent(
            name="Tool caller",
            output_type=CodeExecutorSchema,
            tools=[execute_python_code],
        )

        sample_run = await Runner.run(my_agent, input=prompt)

        output = sample_run.final_output.model_dump()
        output["problem"] = problem
        output["cot"] = cot
        output["cot_type"] = cot_type
        output["topic"] = topic

        return [output]

    # Step 1: Define your desired structured output
    class FeedbackAndRewriteSchema(BaseModel):
        revised_cot: str
        cot: str
        topic: str
        problem: str

    @data_factory(max_concurrency=CONCURRENCY, task_runner_timeout=TASK_RUNNER_TIMEOUT)
    async def feedback_and_rewrite(topic, problem, cot, verified, correct_answer, cot_type):
        prompt = f"""
        Review the problem and the current solution attempt below.

        First, evaluate whether the reasoning in the solution leads to the correct answer. If it does not, identify any mistakes or incorrect steps. Then, rewrite the solution so that the logic is accurate and clearly leads to the correct, verified answer.

        Your rewritten solution should maintain a step-by-step explanation and ensure the final result matches the Correct Answer.

        Make sure that this revised and rewriteen chain of through is is returned in the variable `revised_cot`

        Problem: {problem}
        Current Solution: {cot}
        Verified Correct Answer: {correct_answer}
        """
        my_agent = Agent(name="Feedback and Rewrite", output_type=FeedbackAndRewriteSchema)

        sample_run = await Runner.run(my_agent, input=prompt)

        output = sample_run.final_output.model_dump()

        feedbacked_output = await execute_cot_as_code(cot=output["revised_cot"], topic=topic, problem=problem, answer=correct_answer, cot_type=cot_type)
        return feedbacked_output

    topics = generate_topic.run(num_records=10)
    problem = generate_problem.run(topics)
    long_cot = answer_long_cot.run(problem)
    cot_as_code = data_factory_execute_cot_as_code.run(long_cot)
    all_re_written_cots = []

    # Start with only unverified entries (string comparison)
    unverified_entries = [entry for entry in cot_as_code if entry.get("verified") == "False"]

    verified_entries = [entry for entry in cot_as_code if entry.get("verified") == "True"]

    print("VERIFIED ENTRIES: " + str(len(verified_entries)))

    print("UNVERIFIED ENTRIES: " + str(len(unverified_entries)))

    while unverified_entries:
        # Run feedback and rewrite on the current batch of unverified entries
        rewritten_batch = feedback_and_rewrite.run(unverified_entries)

        # Collect verified rewrites
        verified_batch = [rewritten for rewritten in rewritten_batch if rewritten.get("verified") == "True"]
        all_re_written_cots.extend(verified_batch)

        # Remove verified entries from the current unverified list
        unverified_entries = [rewritten for rewritten in rewritten_batch if rewritten.get("verified") == "False"]
        print("ALL REWRITTEN ENTRIES: " + str(len(all_re_written_cots)))

    verified_entries = verified_entries + all_re_written_cots
    print(verified_entries)


# math_problem_gen_wf()
