# Project Structure

> This document provides stable architectural context that informs all feature specifications.
> Feature-specific details go in `.claude/specs/{feature}/` documents.

## Validation Checklist

- [x] Directory structure documented
- [x] Architecture pattern defined
- [x] Implementation boundaries set
- [x] Pattern references linked
- [x] Naming conventions documented
- [ ] No [NEEDS CLARIFICATION] markers

---

## Directory Layout

> Target structure. Built incrementally as steps progress.

```
arcllm/
├── pyproject.toml                 # Package config, dependencies, pytest config
├── .env.example                   # API key template (never real keys)
├── src/
│   └── arcllm/
│       ├── __init__.py            # Public API: load_model() + type exports
│       ├── types.py               # Core pydantic types (ContentBlock, Message, etc.)
│       ├── exceptions.py          # ArcLLMError, ArcLLMParseError, ArcLLMConfigError
│       ├── config.py              # TOML config loader (global + per-provider)
│       ├── registry.py            # Provider registry + load_model() logic
│       ├── config.toml            # Global defaults + module toggles
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── anthropic.toml     # Provider config + model metadata
│       │   ├── openai.toml
│       │   └── ollama.toml
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py            # LLMProvider abstract base class
│       │   ├── anthropic.py       # Anthropic API adapter
│       │   ├── openai.py          # OpenAI API adapter
│       │   └── ollama.py          # Ollama local adapter
│       └── modules/               # Opt-in functionality
│           ├── __init__.py
│           ├── telemetry.py       # Timing, token counts, cost per call
│           ├── audit.py           # Call logging, reasoning capture
│           ├── budget.py          # Spending limits, cost tracking
│           ├── routing.py         # Model selection rules
│           ├── fallback.py        # Provider chain on failure
│           ├── retry.py           # Retry with backoff
│           └── rate_limit.py      # Requests per minute throttling
├── tests/
│   ├── __init__.py
│   ├── test_types.py              # Type validation tests
│   ├── test_config.py             # Config loading tests
│   ├── test_anthropic.py          # Anthropic adapter tests
│   ├── test_openai.py             # OpenAI adapter tests
│   └── test_agentic_loop.py       # Full cycle integration test
└── .claude/
    └── steering/                  # This directory
        ├── product.md
        ├── tech.md
        ├── structure.md
        └── roadmap.md
```

---

## Architecture Pattern

### Overall Architecture: Layered Library

```
┌─────────────────────────────────────────────────┐
│  Agent Code (external consumer)                  │
│  └─ from arcllm import load_model                │
│  └─ model = load_model("anthropic")              │
│  └─ response = await model.complete(messages)     │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│  Public API Layer (__init__.py, registry.py)      │
│  └─ load_model() → resolves provider, loads config│
│  └─ Returns typed Model object                    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│  Module Layer (optional, opt-in)                  │
│  └─ telemetry, audit, budget, routing, fallback   │
│  └─ Wraps or decorates the adapter                │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│  Adapter Layer (adapters/*.py)                    │
│  └─ Translates ArcLLM types ↔ provider API format │
│  └─ One file per provider, implements LLMProvider  │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│  Type Layer (types.py, exceptions.py)             │
│  └─ Pydantic models: Message, Tool, LLMResponse   │
│  └─ The contract everything builds on              │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│  Config Layer (config.py, *.toml)                 │
│  └─ Global config.toml + per-provider TOMLs        │
│  └─ Model metadata, defaults, module toggles       │
└─────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | Files |
|-------|---------------|-------|
| Public API | Entry point, model loading, exports | `__init__.py`, `registry.py` |
| Modules | Optional cross-cutting concerns | `modules/*.py` |
| Adapters | Provider-specific API translation | `adapters/*.py` |
| Types | Core data contracts | `types.py`, `exceptions.py` |
| Config | Settings, metadata, toggles | `config.py`, `*.toml` |

### Data Flow: Agentic Tool-Calling Loop

```
Agent builds messages (Message[])
       │
       ▼
model.complete(messages, tools)
       │
       ▼
Adapter translates Message[] + Tool[] → Provider API format
       │
       ▼
httpx sends request to provider API
       │
       ▼
Provider returns response
       │
       ▼
Adapter parses response → LLMResponse
  ├─ content: str (text response)
  ├─ tool_calls: list[ToolCall] (parsed arguments)
  ├─ usage: Usage (token counts)
  └─ stop_reason: "end_turn" | "tool_use" | "max_tokens"
       │
       ▼
Agent checks stop_reason
  ├─ "end_turn" → Done, use content
  └─ "tool_use" → Execute tools, pack ToolResultBlock, call complete() again
```

---

## Implementation Boundaries

### Must Preserve

| Item | Location | Why |
|------|----------|-----|
| Type contracts | `src/arcllm/types.py` | Every adapter and module depends on these |
| Exception hierarchy | `src/arcllm/exceptions.py` | Agent error handling relies on these |
| Public API surface | `src/arcllm/__init__.py` | External consumers import from here |
| Config format | `*.toml` files | Deployed configs must remain compatible |

### Can Modify

| Item | Location | Constraints |
|------|----------|-------------|
| Adapter internals | `src/arcllm/adapters/*.py` | Must still produce correct LLMResponse |
| Module internals | `src/arcllm/modules/*.py` | Must still conform to module interface |
| Config loader | `src/arcllm/config.py` | Must still read same TOML structure |
| Test fixtures | `tests/` | Keep tests passing |

### Must Not Touch

| Item | Location | Reason |
|------|----------|--------|
| Provider TOML schema | `providers/*.toml` | Deployed configs depend on this format |
| Core type fields | `types.py` field names | Breaking change for all consumers |
| Public API signature | `load_model()` | Breaking change |

---

## Module Organization

### Core Module (always loaded)

```
src/arcllm/
├── types.py          # Data contracts
├── exceptions.py     # Error types
├── config.py         # Config loading
└── registry.py       # Provider lookup + load_model()
```

### Provider Modules (loaded per-provider)

```
src/arcllm/adapters/{provider}.py     # One file per provider
src/arcllm/providers/{provider}.toml  # One config per provider
```

### Optional Modules (loaded when enabled)

```
src/arcllm/modules/{module}.py        # One file per module
```

Adding a provider = one `.py` adapter + one `.toml` config.
Adding a module = one `.py` file + config section in `config.toml`.

---

## Naming Conventions

### Files

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `rate_limit.py` |
| Adapters | Provider name, snake_case | `anthropic.py` |
| Config | Provider name, `.toml` | `anthropic.toml` |
| Tests | `test_` prefix + module name | `test_types.py` |

### Code

| Type | Convention | Example |
|------|------------|---------|
| Classes (Pydantic) | PascalCase | `LLMResponse`, `ToolCall` |
| Classes (ABC) | PascalCase | `LLMProvider` |
| Functions | snake_case | `load_model`, `validate_config` |
| Constants | SCREAMING_SNAKE | `DEFAULT_TEMPERATURE` |
| Type Aliases | PascalCase | `ContentBlock` |
| Exceptions | PascalCase with Error suffix | `ArcLLMParseError` |

### Config Keys

| Type | Convention | Example |
|------|------------|---------|
| TOML sections | snake_case in brackets | `[modules.rate_limit]` |
| TOML keys | snake_case | `max_retries`, `api_key_env` |
| Model names | Provider's naming | `claude-sonnet-4-20250514` |

---

## Key Directories Purpose

| Directory | Purpose | Owner |
|-----------|---------|-------|
| `src/arcllm/` | Library source code | Core development |
| `src/arcllm/adapters/` | One adapter per LLM provider | Per-provider |
| `src/arcllm/providers/` | One TOML config per provider (model metadata) | Ops/config |
| `src/arcllm/modules/` | Opt-in enterprise features | Feature teams |
| `tests/` | All test code | Everyone |
| `.claude/steering/` | AI agent context | AI/automation |

---

## Directory Map Template

> Use this format in SDD documents to show file changes.

```
src/arcllm/
├── adapters/
│   └── newprovider.py              # NEW: NewProvider adapter
├── providers/
│   └── newprovider.toml            # NEW: NewProvider config + model metadata
├── modules/
│   └── newmodule.py                # NEW: Optional module
tests/
└── test_newprovider.py             # NEW: Adapter tests
```

Legend:
- `# NEW:` - New file to create
- `# MODIFY:` - Existing file to change
- `# DELETE:` - File to remove (rare)

---

## Open Questions (Architecture)

None currently — architecture decisions are locked in the master prompt.

---

## References

- Master Prompt: `/Users/joshschultz/AI/arcllm/arcllm-master-prompt.md`
- PRD Architecture section: `/Users/joshschultz/AI/arcllm/arcllm-prd.md`
