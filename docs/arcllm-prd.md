# ArcLLM — Product Requirements Document

## Overview

ArcLLM is a unified LLM abstraction layer purpose-built for autonomous agent workflows. It provides a minimal, security-first core for sending messages to any LLM provider and receiving normalized responses — including tool calls — with optional modules for routing, telemetry, auditing, and budget management.

ArcLLM is not an SDK, framework, or proxy server. It is a library that agents import directly. It is designed to be embedded in thousands of concurrent autonomous agents operating in production federal environments.

---

## Principles

1. **Minimal core**: The core does ONE thing — normalize LLM communication for agentic tool-calling loops. Everything else is opt-in.
2. **Security first, control second, functionality third**: Every design decision is evaluated in this order.
3. **Agent-native**: Built for agents, not humans chatting. Every interface assumes it's inside an agentic loop doing tool calling.
4. **No state in the LLM layer**: The model object knows its configuration and capabilities. It holds zero conversation state. The agent manages its own message history.
5. **Provider quirks stay in adapters**: Core types are clean and universal. Provider-specific translation, role mapping, and format differences are handled entirely within adapter files.
6. **Config-driven**: Model metadata, provider settings, and module toggles live in TOML config files, not code.
7. **Opt-in complexity**: An agent using one provider with no telemetry loads only what it needs. An agent using routing, fallback, budget, and audit loads those modules explicitly.

---

## Target Interface

```python
from arcllm import load_model

# Load with provider defaults
model = load_model("anthropic")

# Load specific model
model = load_model("anthropic", "claude-sonnet-4-20250514")

# Load with optional modules
model = load_model("anthropic", telemetry=True, audit=True)

# Use in agentic loop — stateless per call
response = await model.invoke(messages, tools=my_tools)

# Sync wrapper available
response = model.invoke_sync(messages, tools=my_tools)
```

---

## Architecture

### Project Structure

```
arcllm/
├── pyproject.toml
├── .env.example
├── src/
│   └── arcllm/
│       ├── __init__.py          # Public API: load_model()
│       ├── types.py             # Core pydantic types
│       ├── exceptions.py        # ArcLLMParseError, ArcLLMConfigError
│       ├── config.py            # TOML config loader
│       ├── registry.py          # Provider registry + load_model logic
│       ├── config.toml          # Global defaults + module toggles
│       ├── providers/
│       │   ├── anthropic.toml
│       │   ├── openai.toml
│       │   └── ollama.toml
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py          # LLMProvider abstract base class
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── ollama.py
│       └── modules/             # Opt-in functionality
│           ├── __init__.py
│           ├── telemetry.py
│           ├── audit.py
│           ├── budget.py
│           ├── routing.py
│           ├── fallback.py
│           └── rate_limit.py
├── tests/
│   ├── test_types.py
│   ├── test_config.py
│   ├── test_anthropic.py
│   ├── test_openai.py
│   └── test_agentic_loop.py
```

### Config Structure

**Global config** (`config.toml`) — defaults and module toggles:

```toml
[defaults]
provider = "anthropic"
temperature = 0.7
max_tokens = 4096

[modules.routing]
enabled = false

[modules.telemetry]
enabled = false

[modules.audit]
enabled = false

[modules.budget]
enabled = false
monthly_limit_usd = 500.00

[modules.retry]
enabled = false
max_retries = 3
backoff_base_seconds = 1.0

[modules.fallback]
enabled = false
chain = ["anthropic", "openai"]

[modules.rate_limit]
enabled = false
requests_per_minute = 60
```

**Provider config** (e.g., `providers/anthropic.toml`) — connection + model metadata:

```toml
[provider]
api_format = "anthropic-messages"
base_url = "https://api.anthropic.com"
api_key_env = "ANTHROPIC_API_KEY"
default_model = "claude-sonnet-4-20250514"
default_temperature = 0.7

[models.claude-sonnet-4-20250514]
context_window = 200000
max_output_tokens = 8192
supports_tools = true
supports_vision = true
supports_thinking = true
input_modalities = ["text", "image"]
cost_input_per_1m = 3.00
cost_output_per_1m = 15.00
cost_cache_read_per_1m = 0.30
cost_cache_write_per_1m = 3.75

[models.claude-haiku-4-5-20251001]
context_window = 200000
max_output_tokens = 8192
supports_tools = true
supports_vision = true
supports_thinking = false
input_modalities = ["text", "image"]
cost_input_per_1m = 0.80
cost_output_per_1m = 4.00
cost_cache_read_per_1m = 0.08
cost_cache_write_per_1m = 1.00
```

---

## Core Types

### ContentBlock (discriminated union)

Four variants, discriminated on `type` field:

| Variant | Fields |
|---------|--------|
| **TextBlock** | type="text", text: str |
| **ImageBlock** | type="image", source: str (base64 or URL), media_type: str |
| **ToolUseBlock** | type="tool_use", id: str, name: str, arguments: dict[str, Any] |
| **ToolResultBlock** | type="tool_result", tool_use_id: str, content: str \| list[ContentBlock] |

### Message

| Field | Type | Notes |
|-------|------|-------|
| role | Literal["system", "user", "assistant", "tool"] | Standard four. Provider-specific roles (e.g., "developer") mapped by adapter. |
| content | str \| list[ContentBlock] | String for simple text, list for multimodal/tool content |

### Tool

| Field | Type | Notes |
|-------|------|-------|
| name | str | Tool identifier |
| description | str | What the tool does (sent to LLM) |
| parameters | dict[str, Any] | JSON Schema, loose/flexible |

### ToolCall

| Field | Type | Notes |
|-------|------|-------|
| id | str | For correlating tool results back |
| name | str | Which tool to call |
| arguments | dict[str, Any] | Always parsed by adapter. Type-check first (dict pass-through), then json.loads if string. Raise ArcLLMParseError on failure. |

### Usage

| Field | Type | Notes |
|-------|------|-------|
| input_tokens | int | Required |
| output_tokens | int | Required |
| total_tokens | int | Required |
| cache_read_tokens | int \| None | Optional, for prompt caching |
| cache_write_tokens | int \| None | Optional, for prompt caching |
| reasoning_tokens | int \| None | Optional, for thinking/reasoning models |

### LLMResponse

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| content | str \| None | None | Text response, null if pure tool calls |
| tool_calls | list[ToolCall] | [] | Empty if no tool calls |
| usage | Usage | required | Token counts |
| model | str | required | Which model actually responded |
| stop_reason | str | required | "end_turn", "tool_use", "max_tokens" |
| thinking | str \| None | None | Reasoning/thinking content if available |
| raw | Any | None | Original provider response for debugging |

### LLMProvider (abstract base class)

| Member | Type | Notes |
|--------|------|-------|
| name | str | Provider identifier |
| invoke() | async method → LLMResponse | Send messages, get normalized response |
| validate_config() | method → bool | Check config validity (API key exists, URL reachable, etc.) |

### Exceptions

| Exception | Fields | Notes |
|-----------|--------|-------|
| ArcLLMParseError | raw_string: str, original_error: Exception | Raised when tool call arguments can't be parsed |
| ArcLLMConfigError | message: str | Raised on config validation failure |

---

## Design Decisions Log

### Provider vs Session Object

**Decision**: Stateless model object (pi-ai pattern).

**Context**: LiteLLM uses stateless function calls with model string routing. pi-ai returns a typed model object from a registry. Neither uses session state.

**Rationale**: Model object gives us a handle that carries config + metadata without holding conversation state. Agent keeps its own message history. Cleaner than passing model strings every call, simpler than managing sessions.

### Tool Call Argument Parsing

**Decision**: Type-check + parse, raise on failure (pi-ai pattern).

**Context**: LiteLLM always-parses but has been plagued by double-serialization bugs across providers. pi-ai type-checks first (is it already a dict? use it. Is it a string? parse it.) and fixed edge cases as bugs.

**Rationale**: Simplest correct approach. If the provider returns a dict, pass it through. If it returns a string, json.loads it. If that fails, raise ArcLLMParseError with the raw string attached. Agent loop handles errors — that's its job. No elaborate fallback dicts or sanitization in core.

### Config Format

**Decision**: TOML, split into global + per-provider files.

**Context**: YAML needs pyyaml dependency. JSON has no comments. TOML is stdlib in Python 3.11+ via tomllib, supports comments, less error-prone than YAML's indentation.

**Rationale**: Zero dependency for config parsing. Per-provider files keep each config short and focused. Adding a provider = dropping in one .toml file. Teams can own their provider configs independently.

### Message Roles

**Decision**: Standard four (system, user, assistant, tool) in core types. Provider-specific roles mapped by adapters.

**Context**: OpenAI uses "developer" in some contexts instead of "system". Other providers may introduce their own role names.

**Rationale**: Core stays clean. Agent code always uses "system". If OpenAI needs "developer", the OpenAI adapter swaps it during translation. Provider quirks don't leak into agent code.

### Content Model

**Decision**: Union type from the start — str | list[ContentBlock] with all four block types (text, image, tool_use, tool_result).

**Context**: Simple string covers 90% of text-only agent loops. But tool-calling agents need structured content blocks for the full cycle (send messages → get tool calls → send tool results → get response).

**Rationale**: Building for agentic tool-calling loops. All four block types are needed for the core use case. Adding them later would require refactoring every adapter.

### Pydantic vs Dataclasses

**Decision**: Pydantic v2.

**Context**: Pydantic adds ~5MB but provides validation, serialization, JSON schema generation. It's already a transitive dependency of both Anthropic and OpenAI Python SDKs.

**Rationale**: Minimizes code in core — pydantic handles validation that we'd otherwise write manually. Already present in the dependency tree of target environments.

---

## Modules (opt-in)

All modules are disabled by default. Enabled via config or at load time.

| Module | Purpose | Config Section |
|--------|---------|---------------|
| **Telemetry** | Timing, token counts, cost per call | `[modules.telemetry]` |
| **Audit** | Call logging, reasoning capture, traceable trail | `[modules.audit]` |
| **Budget** | Spending limits, alerts, cost tracking | `[modules.budget]` |
| **Routing** | Model selection rules, dynamic routing | `[modules.routing]` |
| **Fallback** | Provider chain on failure | `[modules.fallback]` |
| **Retry** | Retry with backoff on transient errors | `[modules.retry]` |
| **Rate Limit** | Requests per minute throttling | `[modules.rate_limit]` |
| **Observability** | OpenTelemetry export | `[modules.observability]` |
| **Security** | API key vault integration, request signing, PII redaction | `[modules.security]` |

---

## Build Order

| Step | What | Why |
|------|------|-----|
| 1 | Project setup + pydantic types | Foundation — the contract everything builds on |
| 2 | Config loading (global + provider TOMLs) | Types need config to be useful |
| 3 | Single provider adapter (Anthropic) + tool support | Prove the core works end-to-end |
| 4 | Test harness — agentic loop test | Verify the full cycle: messages → tool calls → tool results → response |
| 5 | Second provider (OpenAI) | Force the abstraction — if it works for two, it works for N |
| 6 | Provider registry + load_model() | The public API |
| 7 | Fallback + retry | First module — validates the module pattern |
| 8 | Rate limiter | Second module — validates module composability |
| 9 | Router | Model selection and routing rules |
| 10 | Telemetry | Timing, tokens, cost tracking |
| 11 | Audit trail | Call logging, reasoning capture |
| 12 | Budget manager | Spending controls |
| 13 | Observability | OpenTelemetry export |
| 14 | Security layer | Vault, signing, PII redaction |
| 15 | Local/open-source providers | Ollama, vLLM |
| 16 | Integration test | Full agentic loop with all modules |

---

## Target Environment

- **Organizations**: BlackArc Systems, CTG Federal
- **Scale**: Thousands of concurrent autonomous agents
- **Compliance**: Federal production environments, FedRAMP pathway
- **Security**: Auditable, traceable, no API keys in config files
- **Performance**: Abstraction adds <1ms overhead on calls that take 500-5000ms

## Dependencies

### Core (required)
- pydantic >= 2.0
- httpx >= 0.25

### Dev
- pytest
- pytest-asyncio

### Runtime (zero additional for config)
- tomllib (stdlib, Python 3.11+)
