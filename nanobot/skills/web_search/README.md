# Enhanced Web Search Skill for nanobot

A secure, cost-efficient web search implementation using an orchestrator + sub-agent architecture.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "What's the current state of nuclear fusion energy research?"     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Kimi K2.5)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Decision: "Current state" = needs recent info                    │   │
│  │ Action: Spawn web search sub-agent                               │   │
│  │ Queries: ["nuclear fusion 2025 breakthroughs", "ITER progress"] │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ Spawns
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    WEB SEARCH SUB-AGENT (Gemini Flash)                  │
│  ┌──────────────────┐  ┌────────────────┐  ┌─────────────────────────┐ │
│  │ 1. Search        │  │ 2. Fetch       │  │ 3. Security Check       │ │
│  │ (Brave API)      │→ │ (Jina Reader)  │→ │ (Multi-layer analysis)  │ │
│  │ Top 5 results    │  │ Full content   │  │ Sanitize + warn         │ │
│  └──────────────────┘  └────────────────┘  └─────────────────────────┘ │
│                                                        │                │
│                    ┌───────────────────────────────────┘                │
│                    ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 4. Analyze Images (if needed)                                    │   │
│  │    - Chart/graph data extraction                                 │   │
│  │    - Diagram understanding                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ Returns sanitized results
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Kimi K2.5)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Synthesize: Combine findings into coherent response              │   │
│  │ (Or escalate to Claude Opus if complex analysis needed)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🔒 Security Features

Based on OWASP Top 10 for LLM Applications 2025 and research from Anthropic, OpenAI, and Lakera.

### Multi-Layer Defense

1. **URL Analysis**
   - Domain blocklist (paste sites, URL shorteners)
   - Suspicious pattern detection
   - IP address URL blocking

2. **Content Security**
   - 30+ prompt injection pattern detection
   - Structural analysis (hidden comments, base64)
   - Heuristic analysis (command density, API keys)

3. **Sanitization**
   - Clear data boundaries (helps LLM recognize untrusted content)
   - Dangerous pattern replacement
   - Zero-width character removal
   - Source attribution

4. **Threat Levels**
   | Level | Action |
   |-------|--------|
   | SAFE | Process normally |
   | LOW | Proceed with minor caution |
   | MEDIUM | Warn user, proceed |
   | HIGH | Require user approval |
   | CRITICAL | Block entirely |

### Terminal Execution Protection

**CRITICAL**: No commands from web content are executed without explicit user approval.

```
⚠️ Security Notice: This content contains command patterns.
   Do you want to execute? [y/N]
```

## 💰 Cost Optimization

| Model | Cost | Use Case |
|-------|------|----------|
| Kimi K2.5 | $0.50/$2.50 per 1M | Orchestration, final synthesis |
| Gemini Flash | $0.075/$0.30 per 1M | Search execution, content processing |
| Gemini Flash Vision | ~$0.0001 per image | Image analysis when needed |
| Claude Opus 4 | $15/$75 per 1M | Expert escalation (rare) |

**Estimated costs per query:**
- Simple search: ~$0.002-0.005
- With content fetch: ~$0.005-0.01
- With image analysis: +$0.0001 per image
- Expert escalation: +$0.05-0.10

## 📦 Installation

### 1. Dependencies

```bash
pip install requests trafilatura tiktoken
```

### 2. Environment Variables

```bash
# Required: At least one search provider
export BRAVE_API_KEY="your-brave-api-key"     # Recommended
export TAVILY_API_KEY="your-tavily-api-key"   # Fallback

# Required: For model calls
export OPENROUTER_API_KEY="your-openrouter-key"

# Optional: Higher rate limits for Jina
export JINA_API_KEY="your-jina-api-key"
```

### 3. Add to nanobot

Copy files to your nanobot skills directory:

```bash
cp web_search_skill.py ~/.nanobot/skills/web_search/
cp web_search_subagent.py ~/.nanobot/skills/web_search/
cp config.json ~/.nanobot/skills/web_search/
```

### 4. Register Tools

In your nanobot configuration or skill loader:

```python
from skills.web_search.web_search_subagent import (
    WebSearchOrchestrator,
    create_web_search_tool
)

# Initialize orchestrator
orchestrator = WebSearchOrchestrator()

# Register tool
tool = create_web_search_tool(orchestrator)
tool_registry.register(tool)
```

## 🔧 Usage

### Basic Usage (Skill Functions)

```python
from web_search_skill import search_web_skill, browse_page_skill, analyze_image_skill

# Search
results = search_web_skill("latest AI news 2025")
print(results)

# Browse specific page
content = browse_page_skill("https://example.com/article")
print(content)

# Analyze image
analysis = analyze_image_skill(
    "https://example.com/chart.png",
    question="What data does this chart show?"
)
print(analysis)
```

### Advanced Usage (Orchestrator)

```python
from web_search_subagent import WebSearchOrchestrator

orchestrator = WebSearchOrchestrator()

# Check if search is needed
decision = orchestrator.should_search("What is Bitcoin's current price?")
# {'needs_search': True, 'reasoning': 'Contains time-sensitive keywords', ...}

# Execute search
results = orchestrator.execute_search(
    user_message="Latest developments in quantum computing",
    fetch_content=True,
    analyze_images=True
)

# Check for security approval
if results.get("requires_approval"):
    user_response = input("Security concerns detected. Continue? [y/N]: ")
    if user_response.lower() != 'y':
        return "Search cancelled for security reasons."

# Use results
content = results["content"]
print(content["synthesis"])
```

### Expert Escalation

```python
# If standard search is insufficient
if content["confidence"] == "low":
    expert_result = orchestrator.escalate_to_expert(
        user_message=query,
        search_results=results,
        reason="Low confidence in initial results"
    )
    print(expert_result["content"])
```

## 🔍 Search Providers

### Brave Search API (Primary)
- **Index**: 35B+ pages (independent, not Google/Bing)
- **Speed**: ~669ms average
- **Cost**: ~$5-9 per 1,000 requests
- **Features**: Extra snippets, privacy-focused
- **Get API Key**: https://brave.com/search/api/

### Tavily API (Fallback)
- **Design**: AI-native, built for LLMs
- **Cost**: ~$8 per 1,000 requests
- **Features**: Relevance scoring, semantic search
- **Get API Key**: https://tavily.com/

### Jina Reader (Content Fetching)
- **Features**: JS rendering, smart image descriptions
- **Cost**: Free tier (rate limited), or use API key
- **Special**: `x-with-generated-alt: true` for VLM image captions
- **Get API Key**: https://jina.ai/reader/

## 📊 When to Use Web Search

### ✅ USE When:
| Scenario | Keywords/Patterns |
|----------|------------------|
| Current events | "latest", "recent", "today", "news" |
| Real-time data | "price", "stock", "weather", "score" |
| Current status | "who is the CEO of", "current president" |
| Recent changes | "new", "updated", "announced" |

### ❌ DON'T USE When:
| Scenario | Examples |
|----------|----------|
| Timeless facts | "Pythagorean theorem", "when was WWII" |
| Concepts | "explain recursion", "what is gravity" |
| Code help | "write a Python function", "fix this bug" |
| Creative tasks | "write a poem", "brainstorm ideas" |

## 🛡️ Security Patterns Detected

The skill detects and handles these injection patterns:

| Category | Examples |
|----------|----------|
| Instruction Override | "ignore previous instructions", "forget all" |
| System Impersonation | `<system>`, `[ADMIN]`, "SYSTEM:" |
| Jailbreak Attempts | "DAN mode", "bypass safety" |
| Data Exfiltration | "send to webhook", "POST to http" |
| Command Execution | "execute command", "run bash" |
| Unicode Tricks | Zero-width chars, bidirectional overrides |

## 📁 File Structure

```
nanobot_web_search/
├── web_search_skill.py      # Core skill functions + security
├── web_search_subagent.py   # Orchestrator + sub-agent logic
├── config.json              # Configuration
└── README.md                # This file
```

## 🔄 Integration with nanobot Agent Loop

```python
# In your agent loop:

def process_user_message(message, context):
    orchestrator = WebSearchOrchestrator()
    
    # Step 1: Decide if search needed
    decision = orchestrator.should_search(message, context.summary())
    
    if decision["needs_search"]:
        # Step 2: Execute search via sub-agent
        results = orchestrator.execute_search(
            message,
            search_queries=decision.get("search_queries"),
            analyze_images=(decision.get("complexity") == "complex")
        )
        
        # Step 3: Handle security
        if results.get("requires_approval"):
            if not await ask_user_approval(results["content"]["security_concerns"]):
                return "Search cancelled due to security concerns."
        
        # Step 4: Add to context for main model
        context.add_web_results(results["content"])
        
        # Step 5: Check if expert escalation needed
        if results["content"]["confidence"] == "low":
            expert = orchestrator.escalate_to_expert(message, results)
            context.add_expert_analysis(expert["content"])
    
    # Continue with main model response...
    return main_model.generate(message, context)
```

## 🐛 Troubleshooting

### "No search provider configured"
Ensure at least one API key is set:
```bash
export BRAVE_API_KEY="BSA-xxx"
# or
export TAVILY_API_KEY="tvly-xxx"
```

### "Content blocked for security"
The URL or content triggered security rules. Check:
- Is the domain blocklisted?
- Does content contain injection patterns?

### "Image too small"
Images under 1KB are likely tracking pixels and are skipped.

### Slow response times
- Jina with `x-with-generated-alt` adds ~5-10s for image captioning
- Consider disabling for speed: `analyze_images=False`

## 📚 References

- [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/)
- [Anthropic: Mitigating prompt injections in browser use](https://www.anthropic.com/research/prompt-injection-defenses)
- [OpenAI: Hardening Atlas against prompt injection](https://openai.com/index/hardening-atlas-against-prompt-injection/)
- [Lakera: Indirect Prompt Injection](https://www.lakera.ai/blog/indirect-prompt-injection)
- [Jina Reader API](https://github.com/jina-ai/reader)
- [Brave Search API](https://brave.com/search/api/)

## 📄 License

MIT License - See LICENSE file
