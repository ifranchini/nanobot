# Architecture

## Infrastructure

**VPS**: puma-vps (SSH access configured)
**Deploy**: Docker Compose at `/home/nanobot/nanobot/`
**Config**: `/home/nanobot/.nanobot/config.json`
**Workspace**: `/home/nanobot/.nanobot/workspace/`

## Core Flow

```
Inbound message → MessageBus → AgentLoop → ContextBuilder → LLM (via LiteLLM) → Tool execution → Outbound message
```

## Module Breakdown

### `nanobot/agent/` — Core Engine

| File | Purpose |
|------|---------|
| `loop.py` | Main agent loop: receive → build context → call LLM → execute tools → respond |
| `context.py` | Prompt builder (injects skills, memory, history) |
| `memory.py` | Two-layer: `MEMORY.md` (long-term facts) + `HISTORY.md` (activity log) |
| `skills.py` | Loads skills from workspace then built-in fallbacks |
| `subagent.py` | Background task execution (spawn/cron) |

### `nanobot/agent/tools/` — Tool System

| File | Purpose |
|------|---------|
| `registry.py` | Tool registration and discovery |
| `base.py` | Abstract tool interface |
| `filesystem.py` | File operations |
| `shell.py` | Command execution |
| `web.py` | Web search (Brave + Tavily + Jina Reader) |
| `mcp.py` | MCP server integration |
| `spawn.py` | Subagent spawning |
| `cron.py` | Scheduled tasks and reminders |
| `message.py` | Cross-channel messaging |

### `nanobot/channels/` — Chat Integrations

| File | Purpose |
|------|---------|
| `manager.py` | Channel lifecycle and message routing |
| `base.py` | Abstract channel interface |
| `telegram.py` | Telegram bot |
| `discord.py` | Discord bot |
| `slack.py` | Slack app |
| `whatsapp.py` | WhatsApp via Node.js bridge |

### `nanobot/providers/` — LLM Abstraction

| File | Purpose |
|------|---------|
| `registry.py` | **Source of truth** for all provider metadata (`ProviderSpec`) |
| `litellm_provider.py` | LiteLLM wrapper supporting 20+ providers |

Adding a new provider = add `ProviderSpec` in registry.py + field in `schema.py`

### Other Modules

| Module | Purpose |
|--------|---------|
| `nanobot/bus/` | Async message bus (`InboundMessage`/`OutboundMessage`) |
| `nanobot/session/` | Conversation history in JSONL format |
| `nanobot/config/` | Pydantic v2 config (`schema.py`, `loader.py`) |
| `nanobot/cli/` | Typer CLI commands |

## Design Patterns

### Provider Registry
All LLM provider metadata derives from `ProviderSpec` in `providers/registry.py`. Env vars, prefixing, detection, display are automatic.

### Tool Registry
Tools register with `ToolRegistry` and are auto-available to the agent.

### Two-Layer Memory
- `MEMORY.md`: persistent facts, injected into every context
- `HISTORY.md`: grep-searchable activity log

### Message Bus
Decoupled routing between channels and agent via async events.

## Git Setup

**Remotes**:
- `origin`: git@github.com:ifranchini/nanobot.git (fork)
- `upstream`: https://github.com/HKUDS/nanobot.git (source)

**Branches**:
- `main`: pure upstream mirror
- `my-modifications`: custom changes
- `stable`: deployable version

**Auto-sync**: GitHub Action runs daily, rebases modifications onto upstream.

## Environment Variables

Set in `.env` file (gitignored):
- `ANTHROPIC_API_KEY`
- `BRAVE_API_KEY`
- `TAVILY_API_KEY`
- Provider-specific keys as needed

## Custom Tools

### Web Search Enhancement
`nanobot/agent/tools/web.py` — Multi-source search:
1. Brave Search for web results
2. Tavily for AI-optimized search
3. Jina Reader for content extraction
4. Security scanning for URLs
5. ImageAnalyzeTool for vision tasks

### Reminder System
Uses `at` command for one-time reminders, direct message delivery (not agent-processed).
