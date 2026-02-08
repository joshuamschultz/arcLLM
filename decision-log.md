# ArcLLM — Decision Log

> Every architectural and design decision made during the ArcLLM design process.
> Each entry captures what was decided, what alternatives were considered, why we chose what we chose, and what influenced the decision.

---

## D-001: Project Name

**Decision**: ArcLLM

**Alternatives considered**:
- "Forge" (placeholder used during initial design)
- Naming later

**Rationale**: Selected by builder. Short, distinct, no namespace collisions.

---

## D-002: Language

**Decision**: Python

**Alternatives considered**:
- TypeScript — most LLM tooling lives here, easy to embed in Node-based agents
- Python — most agent frameworks are Python, builder's primary agent runtime
- Both — core in one, bindings for the other later

**Rationale**: Builder's agent runtime is Python-based. Python is the dominant language for AI/ML systems and the target deployment environments (federal production). TypeScript was considered because of pi-ai's ecosystem but Python won for alignment with existing agent infrastructure.

---

## D-003: Type System / Validation

**Decision**: Pydantic v2

**Alternatives considered**:
- `dataclasses` + manual validation — zero dependencies, more code
- `pydantic` as optional dependency — core types as dataclasses, pydantic layer on top if installed
- Pydantic v2 full — ~5MB, but validation/serialization/JSON schema built-in

**Rationale**: Minimizes code in core — pydantic handles validation that we'd otherwise write manually. Already a transitive dependency of both Anthropic and OpenAI Python SDKs, so it's already in the target environment. The "heavy dependency" concern is moot when the agent environments already include it.

**Influence**: Builder asked about controlling pydantic weight. Research confirmed it's already present in target dependency trees.

---

## D-004: Testing Framework

**Decision**: pytest + pytest-asyncio

**Alternatives considered**: None seriously — pytest is the Python standard.

**Rationale**: Industry standard. pytest-asyncio needed because core is async-first.

---

## D-005: Async Strategy

**Decision**: Async-first with sync wrapper

**Alternatives considered**:
- Async-only — simpler, but blocks agents not in async context
- Sync-first — simpler to start but wrong for I/O-bound LLM calls
- Async-first with sync wrapper — best of both

**Rationale**: Agent loops are I/O bound (waiting on LLM API calls). Async is the right default. Sync wrapper is trivial (~5 lines: `asyncio.run()`) and ensures agents that aren't async yet still work.

**Influence**: Confirmed pi-ai is fully async (TypeScript async/await on `stream()`). Both Anthropic and OpenAI Python SDKs support async clients.

---

## D-006: Config Format

**Decision**: TOML (stdlib `tomllib`)

**Alternatives considered**:
- YAML — most readable, supports comments, needs `pyyaml` dependency
- JSON — zero dependency, no comments, noisier syntax
- TOML — good readability, supports comments, stdlib in Python 3.11+ (`tomllib`)

**Rationale**: Zero dependency for config parsing (stdlib). Supports comments (unlike JSON). Less error-prone than YAML's indentation sensitivity. Python itself uses TOML (`pyproject.toml`). Aligns with "simplicity and reliability" goal.

**Tradeoff accepted**: TOML is slightly less common in LLM tooling (LiteLLM uses YAML) but the zero-dependency advantage and Python ecosystem alignment won.

---

## D-007: Config Structure

**Decision**: Global `config.toml` + one TOML per provider in `providers/` directory

**Alternatives considered**:
- One giant TOML — one file to find, one to deploy. Gets long with 50+ models.
- Global + per-provider files — clean separation, each file is short and focused
- Per-model files — maximum granularity, massive overkill (50 models = 50 files)

**Rationale**: Per-provider files keep each config short and focused. Adding a provider = adding one file. Teams can own their provider configs independently. Easy to gitignore a local provider (like ollama) while committing cloud providers. When debugging at 2am, open one file — not scroll through a 500-line monolith.

**Influence**: pi-ai separates built-in model catalog from user-override config. LiteLLM uses a single config.yaml.

---

## D-008: Config File Location

**Decision**: Inside the project, in the `arcllm/providers/` directory alongside the adapter `.py` files

**Alternatives considered**:
- Explicit path required at load time
- Convention-based search (current dir → home dir → /etc)
- Root of project

**Rationale**: Builder wanted it clean and colocated with provider code, not in project root. Config lives next to the adapters that consume it.

---

## D-009: Model Interface Pattern

**Decision**: Model object from registry, stateless calls (pi-ai pattern)

**Alternatives considered**:
- **LiteLLM style — pure function, model string routing**: `response = await arcllm.complete("anthropic/claude-sonnet-4-20250514", messages)`. Simplest. No object. But agent passes full model string every call, can't attach metadata.
- **pi-ai style — model object from registry**: `model = load_model("anthropic")`, then `response = await model.complete(messages)`. Model object carries config + metadata but no conversation state.
- **Session object**: Wrapper with state management. More complex, not needed for stateless agent loops.

**Rationale**: Both LiteLLM and pi-ai are stateless per-call. Neither uses session state. Model object gives us a typed handle that carries config and metadata (context window, pricing, capabilities) without holding conversation state. Agent manages its own message history. Cleaner than passing model strings every call.

**Influence**: Studied LiteLLM (stateless function calls) and pi-ai (typed model object). Neither uses sessions. Both are stateless — context/conversation state is the caller's responsibility.

---

## D-010: Load Model Interface Design

**Decision**: `load_model(provider)` or `load_model(provider, model)` — config loaded into provider `.py` files, not at LLM construction time

**Alternatives considered**:
- `ArcLLM.from_config("arcllm.yaml")` — load all config at construction
- `load_model("anthropic")` — config loaded by the provider adapter itself

**Rationale**: Builder wanted config as source of truth for each provider, loaded by the provider adapter, not centrally. The definition is just `load_model(provider)` or `load_model(provider, model)` or `load_model(provider, model, telemetry=True)`. Each provider `.py` file owns loading and building from its own TOML config.

---

## D-011: Content Model

**Decision**: Union type from the start — `str | list[ContentBlock]` with all four block types (text, image, tool_use, tool_result)

**Alternatives considered**:
- Simple: `content: str` — covers 90% of agent use, no multimodal
- Union: `content: str | list[ContentBlock]` — supports text + images + tool content
- String now, extend later — start simple, add escape hatch

**Rationale**: Building for agentic tool-calling loops. Agents need structured content blocks for the full cycle: send messages → get tool calls → send tool results → get response. All four block types needed for the core use case. Adding them later would require refactoring every adapter. Image support included because vision-capable models are increasingly used in agent workflows.

---

## D-012: Message Roles

**Decision**: Standard four internally — `system`, `user`, `assistant`, `tool`. Provider-specific roles handled by adapter translation.

**Alternatives considered**:
- Standard four only, reject anything else
- Standard four + extensibility for provider-specific roles
- All five (including "developer") in core types

**Rationale**: OpenAI uses "developer" in some contexts instead of "system". Rather than polluting core types with provider-specific roles, the adapter handles the swap. Agent code always sends "system". If OpenAI needs "developer", the OpenAI adapter swaps it during translation. Provider quirks stay in adapters where they belong.

---

## D-013: Tool Parameter Schema

**Decision**: Loose/flexible — `dict[str, Any]` (raw JSON schema dicts)

**Alternatives considered**:
- `dict[str, Any]` — loose, flexible, pass raw JSON schema
- Pydantic models that generate JSON schema automatically — tighter, more complex

**Rationale**: For the core, loose is better. Adapters need to serialize tool parameters to each provider's format. Raw JSON schema dicts are universally serializable. Tighter typing would add complexity to core and constrain how agents define their tools.

---

## D-014: Tool Call Argument Parsing

**Decision**: Type-check + parse, raise `ArcLLMParseError` on failure (pi-ai pattern)

**Alternatives considered**:
- **Always parse, raise on failure** (pi-ai style): Type-check first — if dict, use it. If string, `json.loads()`. If fails, raise error with raw string attached. Simple, clean, agent loop handles errors.
- **Sanitize + retry + fallback dict**: Strip control characters, retry parse, if still fails return `{"_raw": "...", "_parse_error": "..."}`. More defensive but adds weird dict shapes agents must know about.
- **Hybrid**: Type-check + parse + one sanitization pass before raising.

**Rationale**: Simplest correct approach. Agent loops are designed to handle errors — that's what stop reasons and error handling are for. Adding elaborate fallback logic in the LLM layer solves a problem that belongs to the agent layer.

**Influence**: Studied LiteLLM's approach — always-parse with transformation layers that have been plagued by double-serialization bugs (Anthropic arguments double-serialized via `json.dumps()`, MCP responses triple-nested, Bedrock raw control characters in JSON). Studied pi-ai — type-check + parse, fixed edge cases as bugs, no elaborate fallback. pi-ai's simpler approach has fewer issues.

Key findings from research:
- LiteLLM: Anthropic returns native Python dict but LiteLLM ran `json.dumps()` on it, breaking downstream (issue #12554)
- LiteLLM: MCP tool responses double-serialized creating triple-nested JSON (Google ADK issue #3676)
- LiteLLM: Invalid JSON in tool arguments breaks session with Anthropic models (OpenAI Agents issue #2061)
- LiteLLM: Bedrock Claude outputs raw control characters in JSON string values (Goose issue #2892)
- pi-ai: Fixed crash when models send malformed tool arguments — objects instead of strings (release notes)

---

## D-015: Usage Tracking Fields

**Decision**: Grab everything available as optional fields — `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens` alongside required `input_tokens`, `output_tokens`, `total_tokens`

**Alternatives considered**:
- Minimal (just input/output/total) — extend via telemetry module later
- Full optional fields in core type

**Rationale**: "If it's there, we should grab it for security and audit later." These fields are available from providers, cost nothing to include as optional fields, and will be needed by telemetry, audit, and budget modules. Better to capture them at the core level than to retrofit later.

---

## D-016: LLM Response — Stop Reason

**Decision**: Include `stop_reason: str` in core LLMResponse

**Alternatives considered**:
- Include in core
- Add later as part of observability module

**Rationale**: Agents in tool-calling loops need to know WHY the model stopped — `end_turn` (done talking), `tool_use` (wants to call tools), `max_tokens` (hit the limit). This determines whether the agent executes tools, continues, or handles truncation. Essential for the agentic loop, not optional.

---

## D-017: LLM Response — Thinking/Reasoning Content

**Decision**: Include `thinking: str | None` in core LLMResponse

**Alternatives considered**:
- Include in core
- Add later as part of audit/observability module

**Rationale**: Needed for observability and audit. Anthropic extended thinking and OpenAI reasoning tokens produce thinking content. Capturing it at the response level (not as a separate module concern) ensures it's available for any downstream use — audit, debugging, cost tracking.

---

## D-018: Provider Interface — Config Validation

**Decision**: Include `validate_config() -> bool` on the LLMProvider abstract base class

**Alternatives considered**:
- Just `complete()` — minimal interface
- `complete()` + `validate_config()` — providers can check their own config on load

**Rationale**: Each provider has different config requirements (API key, base URL, model availability). Letting the provider validate its own config on load catches misconfigurations early — "do I have an API key?", "is my base_url set?". Better to fail fast at load time than to fail on first API call.

---

## D-019: Provider Adapter Architecture

**Decision**: One `.py` file per provider in `adapters/` directory, lazy loaded based on config (B+C pattern)

**Alternatives considered**:
- **A — Provider-level adapters**: One adapter per API format. Maybe 8-12 adapters cover hundreds of models.
- **B — Adapter registry with lazy loading**: Same as A but each adapter imported only when needed. Agent using only Anthropic never loads OpenAI code.
- **C — Adapter + model profile separation**: Adapters handle API format translation. Separate model profiles registry handles model-specific metadata.
- **B+C combined**: Lazy-loaded adapters + config-driven model metadata

**Rationale**: B+C gives tightest dependency control and cleanest separation. Adapters handle API format translation. Model metadata lives in TOML config (not code). Each provider is self-contained. Adding a new provider = one `.py` file + one `.toml` file.

**Performance**: Python module imports are cached after first load — adapter import happens once at startup (microseconds). Per-call overhead is dict lookup (nanoseconds) + object construction (microseconds) on calls that take 500-5000ms. Abstraction layer adds <1ms overhead. Irrelevant.

---

## D-020: API Key Management

**Decision**: Environment variables (`.env`) for now, vault integration later

**Alternatives considered**:
- Environment variables — standard, simple, works with secrets managers
- Separate secrets file — `.arcllm.secrets.toml`, gitignored
- Passed at load time — `load_model("anthropic", api_key=key)`
- Vault integration — AWS Secrets Manager, HashiCorp Vault

**Rationale**: Env vars are the simplest starting point and work everywhere. Keys NEVER go in TOML config files (security-first principle). Config files reference which env var to read (`api_key_env = "ANTHROPIC_API_KEY"`). Vault integration comes as a security module later.

---

## D-021: Adapter Location — Same Repo vs Separate Packages

**Decision**: Same repo, in `adapters/` directory

**Alternatives considered**:
- Same repo, in `adapters/` — simpler to maintain, single install
- Separate packages (`arcllm-anthropic`, `arcllm-openai`) — tightest dependency control
- Single repo, lazy loaded — all in one package, imported on demand

**Rationale**: Simplest to maintain. Single repo, single version, single install. Lazy loading handles the "don't load what you don't use" concern without the overhead of managing multiple packages. Separate packages could come later if dependency isolation becomes critical.

---

## D-022: Model Metadata Source

**Decision**: Config-driven — TOML files per provider, editable without code changes

**Alternatives considered**:
- Hardcoded catalog (like pi-ai's `models.generated.ts`) — generated/maintained in code
- Config-driven — load from TOML files, updatable without code changes
- Runtime discovery — use provider model listing endpoints
- Hybrid — ship defaults, allow config override

**Rationale**: Config-driven aligns with "simplicity and reliability" goal. TOML files are human-readable, version-controllable, and updatable without redeploying code. For federal production environments, config changes go through change management — having them in files (not code) simplifies that process.

**Influence**: pi-ai uses an auto-generated TypeScript file with 300+ models. LiteLLM uses a YAML config. ArcLLM takes the config-driven approach for operational simplicity.

---

## D-023: Model Metadata Fields

**Decision**: Per-model fields include context_window, max_output_tokens, supports_tools, supports_vision, supports_thinking, input_modalities, and full cost breakdown (input, output, cache_read, cache_write per 1M tokens)

**Influence**: Derived from pi-ai's model metadata which tracks:
- `id` — model string for the API
- `name` — human-readable display name
- `reasoning` — boolean (extended thinking support)
- `input` — modality array: `["text"]` or `["text", "image"]`
- `contextWindow` — max context tokens
- `maxTokens` — max output tokens
- `cost` — object: input, output, cacheRead, cacheWrite per million tokens

**Rationale**: This metadata is needed for routing (which models support tools?), budget management (cost per call), validation (context window limits), and audit (what model was used, what were its capabilities). Full cost breakdown enables accurate spend tracking across providers.

---

## D-024: Provider Config Fields

**Decision**: Per-provider fields include api_format, base_url, api_key_env, default_model, and default_temperature

**Fields**:
- `api_format` — which API format: "anthropic-messages", "openai-chat", etc. Tells the adapter which translation logic to use.
- `base_url` — API endpoint (supports custom proxies, local models)
- `api_key_env` — which environment variable holds the API key (NOT the key itself)
- `default_model` — which model to use if none specified in `load_model()`
- `default_temperature` — provider-level default

**Influence**: pi-ai's provider config includes `baseUrl`, `api` (format), `apiKey` (env var or shell command), `headers`, and `compat` (compatibility flags for quirky providers).

**Rationale**: These are the minimum fields every adapter needs to function. `api_format` is critical because it determines which translation logic the adapter uses — many models share the same API format (all OpenAI-compatible models use "openai-chat").

---

## D-025: Global Config — Module Toggles

**Decision**: Global `config.toml` includes `[modules.*]` sections with `enabled = false` defaults and module-specific settings

**Rationale**: Single place to see what's turned on. Each module has its own section with its own settings. Everything is off by default — opt-in only. Module settings that affect behavior (like `monthly_limit_usd` for budget, `max_retries` for retry) live in the config, not hardcoded.

---

## D-026: HTTP Client

**Decision**: httpx

**Alternatives considered**:
- `requests` — synchronous, most popular, would need `aiohttp` for async
- `httpx` — async-native, lightweight, supports both sync and async
- `aiohttp` — async-only, heavier

**Rationale**: httpx is async-native (aligns with async-first decision), lightweight, and supports both sync and async from the same client. No need for two HTTP libraries.

---

## D-027: Python Version Floor

**Decision**: Python 3.11+

**Rationale**: Python 3.11 added `tomllib` to stdlib (zero-dependency TOML parsing) and improved typing features (`Self`, `TypeVarTuple`). 3.11 is widely deployed and available in all target federal environments.

---

## D-028: LLMResponse — Raw Field

**Decision**: Include `raw: Any = None` for the original provider response

**Rationale**: Each provider returns different response shapes. Rather than trying to type this (impossible to do correctly across all providers), store it as `Any` for debugging purposes. Agents and modules that need provider-specific data can access it. Core types don't try to normalize what can't be normalized.

---

## D-029: ToolResultBlock Content Type

**Decision**: `content: str | list[ContentBlock]` — supports both simple string results and structured multi-part results

**Rationale**: Most tool results are simple strings ("The weather is 72°F"). But some tools return structured data — images, multiple text blocks, or nested content. Supporting both keeps the type flexible enough for any tool without overcomplicating the simple case.

---

## D-030: Build Order

**Decision**: Types → Config → Single adapter → Test loop → Second adapter → Registry → Modules

**Rationale**: Each step validates the previous one. Types first because everything depends on them. Config second because adapters need it. Single adapter (Anthropic) proves end-to-end works. Test loop verifies the agentic cycle. Second adapter (OpenAI) forces the abstraction — if it works for two providers, it works for N. Registry provides the public API. Modules come last because they compose on top of a working core.

---