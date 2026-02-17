# Nanobot

Ultra-lightweight personal AI assistant framework (~3,668 lines core). Modular agent with LLM provider abstraction, multi-channel chat, persistent memory, and skills system.

**Package**: `nanobot-ai` (PyPI) | **CLI**: `nanobot` | **Python**: 3.13+ | **License**: MIT

## Quick Reference

```bash
# Development
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run
nanobot onboard                     # first-time setup
nanobot agent                       # interactive chat
nanobot agent -m "Hello!"           # single message
nanobot gateway                     # start channel gateway

# Quality
ruff check nanobot/                 # lint
ruff format nanobot/                # format
ty check                            # type check
pytest -q                           # test
```

## VPS Access (puma-vps)

Claude has SSH access to `puma-vps` where nanobot runs in Docker.

- ✅ **Safe to run directly**: logs, status checks, `docker ps`, `cat`, `grep`
- ⚠️ **Ask user first**: deploy, restart, `docker-compose down`, git operations, clear data

```bash
ssh puma-vps "cd /home/nanobot/nanobot && docker-compose logs --tail=50"
```

## Architecture

```
Inbound → MessageBus → AgentLoop → ContextBuilder → LLM (LiteLLM) → Tools → Outbound
```

See @docs/architecture.md for detailed module breakdown.

## Key Paths

| Location | Purpose |
|----------|---------|
| `nanobot/agent/` | Core engine (loop, context, memory, skills, tools) |
| `nanobot/channels/` | Chat integrations (Telegram, Discord, Slack, etc.) |
| `nanobot/providers/` | LLM abstraction (registry.py is source of truth) |
| `nanobot/config/` | Pydantic v2 config (schema.py, loader.py) |
| `~/.nanobot/` | Runtime config, memory, sessions |

## Code Style

- **ruff**: lint + format, line-length 100, Python 3.13
- **ty**: strict type checking via `[tool.ty.rules]` in pyproject.toml
- **uv**: package management (not pip/poetry)
- **pytest-asyncio**: `asyncio_mode = "auto"`

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Pure upstream mirror (auto-syncs daily) |
| `my-modifications` | Custom changes (rebased onto main) |
| `stable` | Deployable (updates on successful rebase) |

## Documentation

- @docs/architecture.md — detailed system internals
- @docs/operations.md — runbook for common tasks
- @docs/todo.md — current tasks and backlog
