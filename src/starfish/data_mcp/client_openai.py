import asyncio
import os
import shutil
from typing import Any

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from agents.model_settings import ModelSettings


async def run_chat(mcp_server: MCPServer):
    """
    Run an interactive chat loop with the MCP server.

    Args:
        mcp_server (MCPServer): The MCP server instance to communicate with

    The chat loop allows users to:
    - Enter queries directly
    - Include input data using the format: query ||| {'key': 'value'}
    - Type 'quit' to exit
    Responses are logged to a markdown file in the docs/ directory.
    """
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

    # Initialize conversation history
    conversation_history = []
    response_id = None
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

            # Run the query
            result = await Runner.run(
                starting_agent=agent, input=query, context={"conversation_history": conversation_history}, previous_response_id=response_id
            )
            response = result.final_output
            response_id = result.last_response_id

            # Update conversation history
            conversation_history.append(f"User: {query}")
            # conversation_history.append(f"Assistant: {response} (ID: {response_id})")

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
    """
    Execute a predefined task using the MCP server.

    Args:
        mcp_server (MCPServer): The MCP server instance to communicate with

    This function demonstrates a single task execution with the MCP server.
    Currently configured to create a markdown file documenting the project structure.
    """
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to answer the questions.",
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(tool_choice="required"),
    )
    # city_name = ["San Francisco", "New York", "Los Angeles"] * 5
    # region_code = ["DE", "IT", "US"] * 5
    # input_data = {"city_name": city_name, "region_code": region_code}

    message = ' run the template   community/topic_generator_success ||| {"community_name": "AI Enthusiasts", "seed_topics": ["Machine Learning", "Deep Learning"], "num_topics": 1}'
    # message = ' get multiple cities info using the template   starfish/get_city_info_wf ||| city_name=["San Francisco", "New York", "Los Angeles"],region_code=["DE", "IT", "US"]}'
    print(f"\n\nRunning: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # message = f'get city info" ||| city_name={city_name}, region_code={region_code}'
    # print(f"\n\nRunning: {message}")
    # result = await Runner.run(starting_agent=agent, input=message)
    # print(result.final_output)


async def main():
    """
    Main entry point for the MCP client application.

    Initializes the MCP server connection and runs either the chat interface
    or a predefined task. Also handles trace logging for debugging purposes.
    """
    async with MCPServerStdio(
        name="Stdio Python Server",
        params={"command": "python", "args": ["src/starfish/data_mcp/server.py"]},
        # params={
        #     "command": "/Users/john/.local/bin/uv",
        #     "args": ["run", "--directory", "/Users/john/Documents/projects/aa/python/starfish/serena", "serena-mcp-server"],
        # },
        # params={
        #     params={"command": "uvx", "args": ["mcp-server-git"]},
        #     "command": "python src/starfish/data_mcp/server.py",
        # },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="Stdio Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            await run(server)
            # await run_chat(server)


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
