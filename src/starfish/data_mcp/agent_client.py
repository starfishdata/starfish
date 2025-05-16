import asyncio
import os
import shutil
import subprocess
import time
from typing import Any

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from agents.model_settings import ModelSettings


async def run_chat(mcp_server: MCPServer):
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to answer the questions.",
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(tool_choice="required"),
    )
    """Run an interactive chat loop"""
    print("\nMCP Client Started!")
    print("Type your queries or 'quit' to exit.")
    print("To include input data, use format: query ||| {'key': 'value'}")

    while True:
        try:
            user_input = input("\nQuery: ").strip()

            if user_input.lower() == "quit":
                break

            # Split query and input data if provided
            if "|||" in user_input:
                query, data_str = user_input.split("|||", 1)
                try:
                    input_data = eval(data_str.strip())
                except:
                    print("Invalid input data format. Use JSON-like format")
                    continue
            else:
                query = user_input
                input_data = None

            response = await Runner.run(starting_agent=agent, input=query)

            # Write response to markdown file
            os.makedirs("docs", exist_ok=True)
            with open("docs/response.md", "a") as f:
                f.write(f"# Query Response\n\n")
                f.write(f"**Query:** {query}\n\n")
                f.write(f"**Response:**\n\n{response}\n\n")
                f.write("---\n\n")

            print(response)

        except Exception as e:
            print(f"\nError: {str(e)}")


async def run(mcp_server: MCPServer):
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to answer the questions.",
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(tool_choice="required"),
    )
    # city_name = ["San Francisco", "New York", "Los Angeles"] * 5
    # region_code = ["DE", "IT", "US"] * 5
    # input_data = {"city_name": city_name, "region_code": region_code}

    # template_name = "community/topic_generator_success"
    # message = ' test the template   community/topic_generator_success ||| {"community_name": "AI Enthusiasts", "seed_topics": ["Machine Learning", "Deep Learning"], "num_topics": 1}'
    # template_name = "starfish/get_city_info_wf"

    # message = ' get multiple cities info using the template   starfish/get_city_info_wf ||| city_name=["San Francisco", "New York", "Los Angeles"],region_code=["DE", "IT", "US"]}'
    # message = "create markdown file based on the Jupyter files in examples folder so the project is friendly for vibe coding"
    message = "create a markdown file to record the project structure"
    print(f"\n\nRunning: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # message = f'get city info" ||| city_name={city_name}, region_code={region_code}'
    # print(f"\n\nRunning: {message}")
    # result = await Runner.run(starting_agent=agent, input=message)
    # print(result.final_output)


async def main():
    async with MCPServerStdio(
        name="Stdio Python Server",
        # params={"command": "python", "args": ["src/starfish/data_mcp/server.py"]},
        params={
            "command": "/Users/john/.local/bin/uv",
            "args": ["run", "--directory", "/Users/john/Documents/projects/aa/python/starfish/serena", "serena-mcp-server"],
        },
        # params={
        #     params={"command": "uvx", "args": ["mcp-server-git"]},
        #     "command": "python src/starfish/data_mcp/server.py",
        # },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="Stdio Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            # await run(server)
            await run_chat(server)


if __name__ == "__main__":
    # Let's make sure the user has uv installed
    if not shutil.which("uv"):
        raise RuntimeError("uv is not installed. Please install it: https://docs.astral.sh/uv/getting-started/installation/")

    try:
        print("Running example...\n\n")
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
