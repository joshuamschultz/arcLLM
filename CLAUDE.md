# ArcLLM — Project Instructions

## What This Is

ArcLLM is a minimal, security-first unified LLM abstraction layer for autonomous agent workflows. It is a **library** (not a framework, SDK, or proxy). Agents import it directly. It normalizes LLM communication for agentic tool-calling loops.

**Target**: Thousands of concurrent autonomous agents in federal production environments (BlackArc Systems, CTG Federal).

---

## Teaching Mode (CRITICAL)

This project follows a **guided building process**. The builder (Josh) learns by making every decision and writing every line.

### Rules

1. **Explain concepts FIRST** (what and why), then give build instructions
2. **Never dump code for Josh to paste** — give instructions to write code
3. **At EVERY design decision**: present 2-4 options with tradeoffs, relate to ArcLLM's context (agents, scale, security), reference prior art (LiteLLM, pi-ai), then **ASK and WAIT**
4. **Verify together** before moving to the next task
5. **Exception**: If Josh explicitly asks "just write it" or "show me the code", provide code

### If Unclear About Anything

**ASK**. Do not guess or assume. Present what you know, what you don't, and ask Josh to decide.

---

## State Tracking

**State file**: `.claude/arcllm-state.json`

### Session Flow

1. **Start**: Load state, announce position ("Step X, Task Y"), surface notes from last session
2. **During**: One task at a time, record decisions, ask when stuck
3. **End**: Update state (position, completed items, notes for next session)

---

## Locked Decisions (Do NOT Re-Ask)

These are settled. Reference them but never present as open questions.

| Decision | Choice |
|----------|--------|
| Language | Python 3.11+ (strict typing) |
| Types/Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio |
| Async | Async-first with sync wrapper |
| Config format | TOML (stdlib `tomllib`, zero dependency) |
| Config structure | Global `config.toml` + one TOML per provider in `providers/` |
| Model interface | `load_model()` returns stateless model object with `.complete()` |
| State | Model object holds config/metadata ONLY. No conversation state. Agent manages its own messages. |
| Provider adapters | One `.py` file per provider in `adapters/`, lazy loaded |
| API keys | Environment variables only. Never in config files. Vault integration later (Step 14). |
| HTTP client | httpx (async-native, lightweight) |
| Content model | `str \| list[ContentBlock]` — supports text, image, tool_use, tool_result from start |
| Message roles | Standard four internally (system, user, assistant, tool). Provider-specific roles mapped by adapter. |
| Tool parameters | `dict[str, Any]` (raw JSON Schema, loose/flexible) |
| Tool call parsing | Type-check first (dict pass-through), then `json.loads` if string. Raise `ArcLLMParseError` on failure. No elaborate fallback. |
| Dependencies | Core: pydantic >=2.0, httpx >=0.25. Dev: pytest, pytest-asyncio. Config: zero additional (tomllib is stdlib). |
| No provider SDKs | Direct HTTP via httpx. No anthropic/openai SDK dependency. |

---

## Architecture

### Design Principles (in priority order)

1. **Security first, control second, functionality third**
2. **Minimal core** — does ONE thing: normalize LLM communication for agentic tool-calling loops
3. **Agent-native** — built for agents in tool-calling loops, not humans chatting
4. **No state in the LLM layer** — model object knows its config, agent manages messages
5. **Provider quirks stay in adapters** — core types are clean and universal
6. **Config-driven** — model metadata, settings, module toggles in TOML, not code
7. **Opt-in complexity** — one provider + no modules loads only what's needed

### Layered Architecture

```
Agent Code (external consumer)
       |
Public API (__init__.py, registry.py)  -- load_model()
       |
Module Layer (optional, opt-in)        -- telemetry, audit, budget, routing
       |
Adapter Layer (adapters/*.py)          -- provider-specific translation
       |
Type Layer (types.py, exceptions.py)   -- pydantic models, the contract
       |
Config Layer (config.py, *.toml)       -- settings, metadata, toggles
```

### Data Flow: Agentic Tool-Calling Loop

```
Agent builds messages -> model.complete(messages, tools)
-> Adapter translates to provider API format
-> httpx sends request
-> Provider responds
-> Adapter parses to LLMResponse (content, tool_calls, usage, stop_reason)
-> Agent checks stop_reason:
   "end_turn" -> done, use content
   "tool_use" -> execute tools, pack ToolResultBlock, call complete() again
```

---

## Project Structure

```
arcllm/
├── pyproject.toml
├── .env.example
├── src/
│   └── arcllm/
│       ├── __init__.py          # Public API: load_model() + type exports
│       ├── types.py             # Core pydantic types
│       ├── exceptions.py        # ArcLLMError hierarchy
│       ├── config.py            # TOML config loader
│       ├── registry.py          # Provider registry + load_model()
│       ├── config.toml          # Global defaults + module toggles
│       ├── providers/
│       │   ├── anthropic.toml   # Provider config + model metadata
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
│           ├── retry.py
│           └── rate_limit.py
├── tests/
│   ├── test_types.py
│   ├── test_config.py
│   ├── test_anthropic.py
│   ├── test_openai.py
│   └── test_agentic_loop.py
```

---

## Core Types

| Type | Purpose |
|------|---------|
| `ContentBlock` | Discriminated union: TextBlock, ImageBlock, ToolUseBlock, ToolResultBlock |
| `Message` | role (Literal 4 roles) + content (str \| list[ContentBlock]) |
| `Tool` | name, description, parameters (dict) |
| `ToolCall` | id, name, arguments (dict, always parsed) |
| `Usage` | input/output/total tokens + optional cache/reasoning tokens |
| `LLMResponse` | content, tool_calls, usage, model, stop_reason, thinking, raw |
| `LLMProvider` | Abstract base: name, complete(), validate_config() |

### Exception Hierarchy

```
ArcLLMError (base)
├── ArcLLMParseError (raw_string, original_error)
└── ArcLLMConfigError (message)
```

### Error Philosophy

- **Fail fast, fail loud** — raise immediately, don't sanitize or fallback
- **Attach raw data** — every error includes the raw input that caused it
- **No silent failures** — unexpected provider format = raise, not guess

---

## Build Order (16 Steps, 4 Phases)

### Phase 1: Core Foundation (Steps 1-6) — CURRENT

| Step | What | Status |
|------|------|--------|
| 1 | Project setup + pydantic types | Planned (plan exists) |
| 2 | Config loading (global + provider TOMLs) | Not started |
| 3 | Anthropic adapter + tool support | Not started |
| 4 | Test harness — agentic loop | Not started |
| 5 | OpenAI adapter | Not started |
| 6 | Provider registry + load_model() | Not started |

### Phase 2: Module System (Steps 7-9)

| Step | What |
|------|------|
| 7 | Fallback + retry |
| 8 | Rate limiter |
| 9 | Router |

### Phase 3: Observability (Steps 10-13)

| Step | What |
|------|------|
| 10 | Telemetry |
| 11 | Audit trail |
| 12 | Budget manager |
| 13 | OpenTelemetry export |

### Phase 4: Enterprise (Steps 14-16)

| Step | What |
|------|------|
| 14 | Security layer (vault, signing, PII redaction) |
| 15 | Local providers (Ollama, vLLM) |
| 16 | Full integration test |

### Step Plans

- Step 1 plan exists: `arcllm-step-01-plan.md`
- Steps 2-16: plan together with Josh when reached

---

## Step Execution Protocol

### For Steps With Existing Plans

1. Load the plan file (`arcllm-step-{NN}-*.md`)
2. Don't re-discuss decisions already settled in the plan
3. Walk through tasks in order, explaining WHY each piece exists
4. Only ask new decisions that arise during implementation
5. Use the plan's acceptance criteria as verification checklist

### For Steps Without Plans

1. Discuss conceptually — what it does, why it matters
2. Present design decisions with tradeoffs
3. Build the plan together before implementing
4. Then walk through implementation

### Deviation Protocol

If implementation cannot follow plan exactly:

1. Document the deviation and reason
2. Discuss with Josh before proceeding
3. Update plan if deviation is an improvement
4. Record decision in `arcllm-state.json`

---

## Testing

### Approach: TDD

```
For each task:
1. Understand the concept
2. Write tests first
3. Implement to pass tests
4. Verify acceptance criteria
```

### Test Pyramid

- **Unit (50%)**: Types, config, parsing, exceptions
- **Adapter (30%)**: Per-provider translation correctness
- **Integration (20%)**: Full agentic loop with mock provider

### Test Conventions

| Test Type | File | Naming |
|-----------|------|--------|
| Unit (types) | `tests/test_types.py` | `test_{type}_{scenario}` |
| Unit (config) | `tests/test_config.py` | `test_{loader}_{scenario}` |
| Adapter | `tests/test_{provider}.py` | `test_{provider}_{operation}` |
| Integration | `tests/test_agentic_loop.py` | `test_{scenario}_loop` |

### Quality Thresholds

| Metric | Threshold |
|--------|-----------|
| Line Coverage | >=80% |
| Branch Coverage | >=75% |
| Core types.py | 100% |
| Adapters | >=90% |
| Type Errors | 0 |
| Complexity | <=10 per function |

---

## Security Requirements

- API keys from environment variables ONLY (`os.environ`)
- Provider TOML specifies `api_key_env` (variable name), never the key itself
- No PII in core types or logs by default
- TLS enforced (httpx default)
- `raw` field on LLMResponse for debugging only, not logged
- Usage tracking (tokens, cache, reasoning) in every response

---

## Performance Constraints

| Metric | Target |
|--------|--------|
| Abstraction overhead | <1ms per call (calls take 500-5000ms) |
| Import time | <100ms |
| Memory per model object | Minimal (stateless) |

---

## Implementation Boundaries

### Must Preserve

- Type contracts in `types.py`
- Exception hierarchy in `exceptions.py`
- Public API surface in `__init__.py`
- Config format in `*.toml` files

### Must Not Touch

- Provider TOML schema (deployed configs depend on format)
- Core type field names (breaking change for consumers)
- `load_model()` signature (breaking change)

---

## Competitive Context

| Competitor | ArcLLM Differentiator |
|------------|----------------------|
| LiteLLM | Modular (not monolithic), clean tool call handling (no double-serialization bugs), opt-in complexity |
| pi-ai | Python-native, config-driven model metadata, enterprise modules (audit, budget, security) |
| Direct SDKs | Provider-agnostic, normalized types, single interface |
| LangChain | Library not framework, minimal core, agent-native |

ArcLLM takes pi-ai's model-object pattern + config-driven approach + LiteLLM's module concepts (routing, fallback, budget) as opt-in imports, not baked into core.

---

## Commands

```bash
pip install -e ".[dev]"              # Install in dev mode
pytest -v                            # Run all tests
pytest --cov=arcllm                  # Run with coverage
python -c "from arcllm import load_model"  # Verify imports
```

---

## Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| PRD | `docs/arcllm-prd.md` | Full product requirements, architecture, types, modules |
| Master Prompt | `docs/arcllm-master-prompt.md` | Locked decisions, build order, teaching method |
| Step Plans | `arcllm-step-{NN}-*.md` | Per-step build instructions |
| State | `.claude/arcllm-state.json` | Current position, decisions, notes |
| Steering | `.claude/steering/` | Product, tech, structure, roadmap context |
| Specs | `.claude/specs/` | Formalized spec documents |
| Builder Skill | `~/.claude/skills/arcllm-builder/SKILL.md` | Teaching interaction patterns |
