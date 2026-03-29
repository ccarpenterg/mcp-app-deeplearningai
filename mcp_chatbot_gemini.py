from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio
import os

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
        self.gemini_client = genai.Client()
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

    def _convert_tools_for_gemini(self) -> List[dict]:
        """Convert MCP tool definitions to Gemini function declarations"""
        tools = []
        for tool in self.available_tools:
            tool_def = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
            tools.append(tool_def)
        return [{"function_declarations": tools}]

    async def process_query(self, query):
        gemini_tools = self._convert_tools_for_gemini()
        
        # Create chat session with history
        chat = self.gemini_client.chats.create(model="gemini-2.0-flash")
        
        # Generate initial response with tools enabled
        response = chat.send_message(
            query,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
            ),
            tools=gemini_tools,
        )

        process_query = True
        while process_query:
            # Check if the response contains function calls
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    # Check for function call
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_name = part.function_call.name
                        tool_args = dict(part.function_call.args)
                        
                        print(f"Calling tool {tool_name} with args {tool_args}")
                        
                        session = self.tool_to_session.get(tool_name)
                        if session:
                            result = await session.call_tool(tool_name, arguments=tool_args)
                            result_str = json.dumps(result.result) if not isinstance(result.result, str) else result.result
                            
                            # Send the tool result back to Gemini
                            response = chat.send_message(
                                genai.protos.Content(
                                    role="function",
                                    parts=[genai.protos.Part(
                                        function_response=genai.protos.FunctionResponse(
                                            name=tool_name,
                                            response={"result": result_str}
                                        )
                                    )]
                                ),
                                generation_config=genai.types.GenerationConfig(
                                    max_output_tokens=2048,
                                ),
                                tools=gemini_tools,
                            )
                        else:
                            print(f"Tool {tool_name} not found")
                            response = chat.send_message(
                                f"Error: Tool {tool_name} not available",
                                generation_config=genai.types.GenerationConfig(
                                    max_output_tokens=2048,
                                ),
                                tools=gemini_tools,
                            )
                        break
                    elif hasattr(part, 'text') and part.text:
                        print(part.text)
                        if len(response.candidates[0].content.parts) == 1:
                            process_query = False
            else:
                process_query = False


    async def chat_loop(self):
        """Run an interactive chat loop."""
        print("\nMCP ChatBot Started")
        print("Type your queries or 'quit' to exit.\n")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                await self.process_query(query)
                print("\n")

            except Exception as e:
                print(f"Error processing query: {str(e)}")

    async def cleanup(self):
        """Cleanly close all resources using AsyncExitStack."""
        await self.exit_stack.aclose()

async def main():
    chatbot = MCP_ChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
