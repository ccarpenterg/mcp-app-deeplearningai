from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
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
        return types.Tool(functionDeclarations=tools)

    async def process_query(self, query):
        tools = self._convert_tools_for_gemini()
        config = genai_types.GenerateContentConfig(tools=tools)

        history = [
            genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
        ]

        # Generate initial response with tools enabled
        response = await self.gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=config
        )

        # Create chat session with history
        #chat = self.gemini_client.chats.create(model="gemini-2.0-flash", config=config)
        
        # Generate initial response with tools enabled
        #response = chat.send_message(query)
      
        process_query = True
        while process_query:
            print("\nGemini Response:")
            for part in response.parts:
                if part.text:
                    print(part.text)
                    history.append(response.candidates[0].content)
                    if(len(response.parts) == 1):
                        process_query = False

                elif part.function_call:
                    history.append(genai_types.Content(
                        role="assistant",
                        parts=[part]
                    ))

                    print(f"Calling: {part.function_call.name}")
                    print(f"Arguments: {part.function_call.args}")

                    tool_name = part.function_call.name
                    tool_args = part.function_call.args

                    session = self.tool_to_session.get(tool_name)
                    result = await session.call_tool(tool_name, argumetns=tool_args)

                    tool_content = genai_types.Content(
                        role="tool",
                        parts=[
                            genai_types.Part(
                                function_reponse=genai_types.FunctionResponse(
                                    name=tool_name,
                                    response={"result": result.content}
                                )
                            )
                        ])
                    
                    history.append(tool_content)
                    
                    response = await self.gemini_client.aio.models.generate_content(
                        model="gemini-2.5-flash",
                        history=history,
                        config=config
                    )

            
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
