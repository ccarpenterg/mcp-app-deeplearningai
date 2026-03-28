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

