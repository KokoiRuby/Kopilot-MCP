from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from loguru import logger
import asyncio
import json
from dataclasses import dataclass, field
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam, ChatCompletionSystemMessageParam
from typing import Any, cast
from config.config import config
import sys


logger.configure(
    handlers=[{"sink": sys.stderr, "level": config["mcp"]["log_level"]}])

llm_config = config["client"]["llm"]

# Initialize OpenAI client
openai_client = AsyncOpenAI(
    api_key=llm_config["api_key"],
    base_url=llm_config["base_url"],
)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="/usr/local/bin/python3",  # Executable
    args=["./mcp_server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)


@dataclass
class Chat:
    messages: list = field(default_factory=list)

    # https://platform.openai.com/docs/guides/text?api-mode=chat#message-roles-and-instruction-following
    system_prompt = ChatCompletionSystemMessageParam(
        role="system",
        content="""You are a Kubernetes expert.
        Your job is to use the tools at your disposal to perform CRUD operations on Kubernetes resources based on user's query.
        Always use plural form of resource name incase user provides singular form or shortnames.""",
    )

    # TODO: Singleton?
    async def get_tools(self, session: ClientSession) -> list[ChatCompletionToolParam]:
        """Set up tools from MCP server."""
        response = await session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                }
            }
            for tool in response.tools
        ]

    async def process_query(self, session: ClientSession, query: str) -> None:
        # Get available tools from MCP server
        available_tools = await self.get_tools(session)

        self.messages.append(
            {
                "role": "user",
                "content": query,
            }
        )

        # Initial OpenAI API call
        response = await openai_client.chat.completions.create(
            model=llm_config["model"] or "gpt-4o-mini",
            messages=self.messages,
            tools=available_tools,
            tool_choice="auto",
            temperature=llm_config["temperature"],
        )

        # Process the response
        assistant_message = response.choices[0].message
        logger.debug(assistant_message)

        if assistant_message.tool_calls:
            self.messages.append(assistant_message)

            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                logger.debug(f"Executing tool: {function_name}")

                # Validate function arguments
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    logger.debug(
                        f"Function arguments: {function_args}, type: {type(function_args)}")
                    if not isinstance(function_args, dict):
                        logger.error(
                            f"Invalid function arguments format: expected dict, got {type(function_args).__name__}")
                        function_args = {}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse function arguments: {e}")
                    function_args = {}

                # Execute tool call
                if function_name == "update_resource":
                    logger.debug(
                        f"Value of patch field: {function_args['patch']}")
                    logger.debug(
                        f"Type of patch fields: {type(function_args['patch'])}")
                result = await session.call_tool(function_name, cast(dict[str, Any], function_args))
                logger.debug(f"Tool result: {result}")
                tool_result = getattr(result.content[0], "text", "")

                # Add the tool result to the conversation history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            # Get the next response from OpenAI with the tool results
            response = await openai_client.chat.completions.create(
                model=llm_config["model"] or "gpt-4o-mini",
                messages=self.messages,
                tools=available_tools,
                tool_choice="auto",
                temperature=llm_config["temperature"],
            )

            # Process the final response
            final_message = response.choices[0].message
            self.messages.append({
                "role": "assistant",
                "content": final_message.content
            })
            print(final_message.content or "")

        else:
            # If no tool calls, just add the response to the conversation history
            self.messages.append({
                "role": "assistant",
                "content": assistant_message.content
            })

    async def chat_loop(self, session: ClientSession):
        """Run the chat loop."""
        try:
            while True:
                self.messages = [self.system_prompt]
                query = input(
                    "\nQuery (Type `exit`, `quit`, `q` to quit): ").strip()
                if query.lower() in ['exit', 'quit', 'q']:
                    print("\nGoodbye!")
                    break
                await self.process_query(session, query)
                # TODO: Simply clear the messages to isolate each query.
                self.messages.clear()
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt. Exiting...")
        except Exception as e:
            print(f"\nAn error occurred: {e}")
        finally:
            print("Chat session ended.")

    async def run(self):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                await self.chat_loop(session)
                # # List available tools
                # response = await session.list_tools()
                # for tool in response.tools:
                #     print(f'[Tool name]:')
                #     print(f' {tool.name}\n')
                #     print(f'[Tool description]:')
                #     print(f' {tool.description}\n')
                #     print(f'[Tool inputSchema]:')
                #     print(json.dumps(tool.inputSchema, indent=2))
                #     print('-------------------------------')


chat = Chat()

if __name__ == "__main__":
    asyncio.run(chat.run())
