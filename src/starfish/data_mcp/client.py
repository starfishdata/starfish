import asyncio
import httpx
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # pip install httpx==0.25.0 anthropic==0.20.0
        # self.anthropic = Anthropic()
        self.anthropic = Anthropic(http_client=httpx.Client())  # Explicitly pass a custom httpx client

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str, input_data: Optional[dict] = None):
        """Process a query using Claude and available tools
        Args:
            query: The user's query
            input_data: Optional input data to include in the context
        """
        messages = [{"role": "user", "content": query}]

        # Add input data to context if provided
        if input_data:
            messages.append({"role": "user", "content": f"Here is the input data: {input_data}"})

        response = await self.session.list_tools()
        available_tools = [{"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema} for tool in response.tools]

        # Add debug print to show available tools
        print("Available tools debug:", [tool["name"] for tool in available_tools])

        # Initial Claude API call
        response = self.anthropic.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=1000, messages=messages, tools=available_tools)

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                try:
                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_results.append({"call": tool_name, "result": result})
                    final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                except Exception as e:
                    print(f"Error calling tool for debug {tool_name}: {str(e)}")
                    raise  # Re-raise the exception after logging

                # Continue conversation with tool results
                if hasattr(content, "text") and content.text:
                    messages.append({"role": "assistant", "content": content.text})

                # Convert result to string safely
                result_str = str(result) if not isinstance(result, str) else result
                messages.append({"role": "user", "content": result_str})

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.content[0].text)
                return result_str  # Return the exact tool result directly

        # return "\n".join(final_text)
        # return "\n".join(tool_results)
        # return result_str

    async def chat_loop(self):
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

                response = await self.process_query(query.strip(), input_data)
                # print("\n" + response)
                print(response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
