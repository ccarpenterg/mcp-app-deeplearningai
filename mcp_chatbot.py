from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio

load_dotenv()


class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict


class MCP_ChatBot:

    def __init__(self):
        self.sessions: List[ClientSession] = []
        self.available_tools: List[ToolDefinition] = []
        self.tool_to_session: Dict[str, ClientSession] = {}
        self.anthropic = Anthropic()
        self.exit_stack = AsyncExitStack()

    
    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server and register its tools"""
        try:
            server_params = StdioServerParameters(**server_config)

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            self.sessions.append(session)

            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                })
                self.tool_to_session[tool.name] = session

        except Exception as e:
            print(f"Error connecting to server {server_name}: {e}")

        



    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        try:
            with open('server_config.json') as file:
                data = json.load(file)

                servers = data.get('mcpServers', {})

                for server_name, server_config in servers.items():
                    await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise        

    async def process_query(self, query):
        messages = [{'role': 'user', 'content': query}]
        response = self.anthropic.messages.create(
            max_tokens=2024,
            model='claude-sonnet-4-6',
            tools=self.available_tools,
            messages=messages
        )

        process_query = True
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type == 'text':
                    print(content.text)
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query = False

                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role': 'assistant', 'content': assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name

                    print(f"Calling tool {tool_name} with args {tool_args}")

                    session = self.tool_to_session.get(tool_name)
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result.result,
                            }
                        ]
                    })

                    response = self.anthropic.messages.create(
                        max_tokens=2024,
                        model='claude-sonnet-4-6',
                        tools=self.available_tools,
                        messages=messages
                    )

                    if(len(response.content) == 1 and response.content[0].type == 'text'):
                        process_query = False

