# MCP Apps Demo (Gemini + Python)

This repository demonstrates a practical implementation of MCP (Model Context Protocol) in Python, based on the DeepLearning.AI short course:

- "MCP: Build Rich-Context AI Apps with Anthropic"

Since Anthropic API keys are unavailable in this environment, this implementation uses Google Gemini (`genai`) with a custom MCP adapter.

---

## ✅ Project Goals

- Demonstrate MCP tool discovery, registration, and tool invocation flow
- Show how to adapt MCP-style tools to a function-calling LLM architecture
- Provide an exercise platform for MCP clients and local tooling
- Build a working alternative using Gemini instead of Anthropic

## 📦 Repository Contents


- `mcp_chatbot_gemini.py` - Gemini-based MCP client; interacts with local tools via MCP session and function calls
- `mcp_chatbot.py` - baseline MCP approach (Anthropic-style fallback path)
- `research_server.py` - example MCP tool server (research / utility endpoints)
- `server_config.json` - MCP server definitions and connection settings
- `pyproject.toml` - Python project metadata and dependencies


---

## 🚀 Quick Start

1. Clone repository
2. Install dependencies with `uv`

```bash
uv sync
```

3. Create `.env` file with Gemini credentials

```env
GOOGLE_API_KEY=your-gemini-api-key
```

4. Configure MCP servers in `server_config.json` (example inside file)
5. Run Gemini MCP chatbot

```bash
uv run python mcp_chatbot_gemini.py
```

6. Type messages, observe tool calls, and type `quit` to exit

---

## 🧠 How It Works (Gemini MCP Loop)

In `mcp_chatbot_gemini.py`:

1. `connect_to_servers()` loads server definitions from `server_config.json`
2. Each MCP tool is registered with name/description/schema
3. `_convert_tools_for_gemini()` maps MCP tools into Gemini function declarations
4. `process_query()` sends user query as `genai_types.Content` to Gemini
5. Gemini may respond with direct text or function call
6. On function call:
   - call MCP tool using `session.call_tool(tool_name, arguments)`
   - append tool response as role `tool` into conversation history
   - loop until assistant(s) returns final text response

---

## 🔧 Config Tips

- Ensure `server_config.json` points to valid MCP server endpoints and tool definitions
- For local testing, `research_server.py` can provide endpoint examples
- For production, the same architecture can plug in Anthropic MCP tooling by replacing Gemini adapter

---

## 🧩 What You Can Extend

- Add new MCP tools (via `server_config.json` and server-side handler)
- Improve function/schema mapping for Gemini/Anthropic
- Add tool result logging, retries, batching
- Add context sanitization and agent-level prompts for more advanced reasoning

---

## 📝 Notes

- No Anthropic tokens required for this repo; Gemini adapter is used as alternative
- This is educational/demo code, not hardened production deployment
- Validate any provider credentials before use and control costs in managed API usage

---

## 🏷️ License

MIT (or your chosen permissive license; add `LICENSE` file as needed)
