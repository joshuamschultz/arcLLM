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

## D-031: Config Data Model

**Decision**: Pydantic models for all config types (typed configs)

**Alternatives considered**:
- Pydantic BaseModel classes for config — typed, validated on load, same pattern as core types
- Dataclasses + manual validation — lighter weight but more code, no automatic validation
- TypedDict / plain dicts — minimal code, no validation at load time

**Rationale**: Config errors in production autonomous agents are catastrophic — wrong base_url, missing api_key_env, model name typo. These agents run unattended. Fail-fast validation is critical. Pydantic v2 is already in the dependency tree. Using raw dicts delays error discovery to runtime when it's hardest to debug.

**Influence**: LiteLLM uses raw dicts from YAML — config errors surface late (at API call time). pi-ai has typed config objects — errors caught at load time. ArcLLM follows pi-ai's approach.

---

## D-032: Config Validation Timing

**Decision**: Validate on load (fail-fast)

**Alternatives considered**:
- Validate on load — `tomllib.load()` → pydantic model → errors raised immediately
- Validate on first use — load as raw dict, validate when provider is actually needed (lazy)
- Two-phase — structural validation on load, semantic validation on use

**Rationale**: "Don't try to debug config at the same time as an LLM call." For agents running in production, fail-fast is the right default. Structural validation (does the TOML parse? are required fields present? are types correct?) happens on load. Semantic validation (is the API key actually set in env? is the base_url reachable?) is the adapter's job via `validate_config()`.

---

## D-033: Config Merge Strategy

**Decision**: Simple override chain — args > provider > global, flat merge, last-writer-wins

**Alternatives considered**:
- Simple override chain — provider overrides global, kwargs override everything
- Deep merge — nested dicts merged recursively
- Explicit layers — keep global and provider as separate objects, adapter resolves

**Rationale**: TOML structure is flat-ish tables. Deep merge is overkill. The real merge happens at call time (Step 6): global defaults provide fallback values, provider config overrides those, and kwargs at `load_model()` or `complete()` override everything. Simple, predictable, debuggable.

---

## D-034: Config File Discovery

**Decision**: Package-relative — use `Path(__file__).parent` to find config files

**Alternatives considered**:
- Package-relative via `__file__` — config found relative to installed package
- CWD-relative — look in current working directory
- Package defaults + override path — ship defaults, env var for override directory
- `importlib.resources` — more formal package resource API

**Rationale**: Config is part of the unified layer — it ships with the library. `__file__` works in both dev mode (`pip install -e`) and installed mode. No external path configuration needed. CWD-relative breaks when agents run from different directories. `importlib.resources` adds complexity for no benefit when files are alongside Python code.

---

## D-035: Provider Name Input Validation

**Decision**: Strict regex validation (`^[a-z][a-z0-9\-]*$`, max 64 chars) on `provider_name` parameter before path construction

**Alternatives considered**:
- No validation — rely on FileNotFoundError for bad names
- Path resolution check — construct path, then verify it resolves within `providers/` directory
- Allowlist — only accept known provider names from a registry

**Rationale**: `load_provider_config(provider_name)` interpolates the name directly into a file path (`providers/{name}.toml`). Without validation, path traversal attacks (`../../etc/passwd`) could read arbitrary `.toml` files. For a library targeting federal production (BlackArc Systems, CTG Federal), this is a compliance violation.

**Compliance**: NIST 800-53 AC-3 (Access Enforcement) — system must enforce approved authorizations for logical access to information. Unrestricted file path construction from user input violates this control. OWASP A01 (Broken Access Control) — path traversal is a direct violation.

**Implementation**: Regex validation at function entry, before any path construction. Rejects empty, too-long, uppercase, special characters, and path separators. Raises `ArcLLMConfigError` with clear message.

**Why not allowlist**: Provider configs are file-driven — new providers are added by dropping a TOML file, not by modifying code. An allowlist would break this extensibility.

---

## D-036: Step 4 Test Approach — Jupyter Notebook (Not Pytest Mocks)

**Decision**: Validate the agentic loop with a Jupyter notebook making real API calls, rather than additional pytest mocks

**Alternatives considered**:
- Pytest with mocked httpx responses — more deterministic, runs offline
- Pytest with VCR/cassettes — records real responses, replays offline
- Standalone Python script — no notebook tooling needed

**Rationale**: Step 4's purpose is to validate the *unified interface* works end-to-end against the real API, not to add more unit tests (Step 3 already has 84 unit tests with 99% coverage). A notebook provides interactive, visual validation of the full agentic tool-calling loop. Josh clarified: "we are not actually building the loop here, we are simply going to test the unified interface with a loop."

**Influence**: Also created `walkthrough/run_step_04.py` as a script equivalent for CI/headless execution.

---

## D-037: Step 4 Tool Selection — Both Calculator and Web Search

**Decision**: Include both calculator (real eval) and web search (canned results) tools in the notebook

**Alternatives considered**:
- Calculator only — simplest
- Search only — tests string content handling
- Both — tests multi-tool selection

**Rationale**: Both tools exercise different content patterns (numeric vs string results) and together test the multi-tool selection capability. The multi-tool test validates the LLM correctly picks which tool to use when multiple are available.

---

## D-038: StopReason Normalization

**Decision**: Define `StopReason = Literal["end_turn", "tool_use", "max_tokens", "stop_sequence"]` as canonical stop reasons. Each adapter maps provider-native values to these.

**Alternatives considered**:
- Pass through provider-native values — each adapter returns whatever the provider sends. Simple but agents must know which provider they're using, defeating the abstraction.
- Dual field (normalized + raw) — normalize to canonical set AND store original provider value in `raw_stop_reason`. Best of both worlds but over-engineering since `LLMResponse.raw` already contains the original.

**Rationale**: The whole point of ArcLLM is a unified interface. If an agent checks `stop_reason == "tool_use"` after an Anthropic call, that same check must work after an OpenAI call. Anthropic's values are clean and descriptive — adopt them as canonical. Using a `Literal` type catches typos at pydantic validation time, not at runtime during a live agent loop.

**Mapping**:
| OpenAI `finish_reason` | ArcLLM `StopReason` |
|------------------------|---------------------|
| `"stop"` | `"end_turn"` |
| `"tool_calls"` | `"tool_use"` |
| `"length"` | `"max_tokens"` |
| `"content_filter"` | `"end_turn"` |

---

## D-039: Tool Result Message Flattening (OpenAI)

**Decision**: The OpenAI adapter's `_format_messages()` method handles one-to-many expansion transparently. A single ArcLLM message with N `ToolResultBlock`s becomes N separate OpenAI messages, each with `role: "tool"` and `tool_call_id` at the message level.

**Alternatives considered**:
- Require agents to use different message format per provider — would defeat the unified abstraction entirely.

**Rationale**: Agents use the same `ToolResultBlock` message-building pattern regardless of provider. The adapter owns the translation complexity. One ArcLLM message with 3 tool results -> 3 OpenAI messages. This is invisible to the agent.

---

## D-040: Mirror Anthropic Adapter Structure for OpenAI

**Decision**: OpenAI adapter uses the same private-method-per-concern pattern as the Anthropic adapter: `_build_headers()`, `_build_request_body()`, `_format_message()`, `_format_tool()`, `_parse_response()`, `_parse_tool_call()`, `_parse_usage()`. Plus OpenAI-specific `_map_stop_reason()`.

**Alternatives considered**:
- Different structure optimized for OpenAI's simpler API — but consistency is more important than micro-optimization.

**Rationale**: Proven in Step 3. Each method independently testable. When OpenAI changes their API, update one method. Consistent structure across adapters makes the codebase easier to maintain and learn. A developer who understands the Anthropic adapter instantly understands the OpenAI adapter.

---

## D-041: Convention-Based Registry

**Decision**: Provider name drives TOML path, module path, and class name by convention.

**Alternatives considered**:
- Static mapping dict — explicit but another file to maintain
- TOML `adapter_module` field + importlib — flexible but config-coupled
- `entry_points` plugin system — standard Python but overkill

**Rationale**: File structure is the registry. Zero config for discovery. No mapping dict to maintain. Adding a provider = drop a `.py` file and a `.toml` file. Convention: `provider_name` → `arcllm.adapters.{name}` → `{Name.title()}Adapter`.

---

## D-042: Class Name Convention

**Decision**: `provider_name.title() + 'Adapter'` — renamed `OpenAIAdapter` to `OpenaiAdapter`.

**Alternatives considered**:
- Exception dict for known cases (e.g., `openai → OpenAIAdapter`)
- Scan module for BaseAdapter subclass

**Rationale**: Predictable, no exception maps. Pure convention means zero maintenance. `openai.title()` → `Openai` → `OpenaiAdapter`. Works for any provider name without special cases.

---

## D-043: Module-Level Config Cache

**Decision**: Cache `ProviderConfig` in module-level dict with `clear_cache()` for testing.

**Alternatives considered**:
- Load every time — wasteful at scale
- Explicit Registry object — more ceremony, same effect

**Rationale**: Avoids re-parsing TOML per `load_model()` call. Essential at scale with thousands of agents. `clear_cache()` ensures test isolation. CPython GIL provides thread safety for dict operations.

---

## D-044: No **kwargs on load_model()

**Decision**: Remove `**kwargs` from `load_model()` — only `provider` and `model` params.

**Alternatives considered**:
- Keep `**kwargs` and add to `BaseAdapter` — but adapters don't need arbitrary args
- Catch `TypeError` and wrap in `ArcLLMConfigError` — defensive but masks the real issue

**Rationale**: `BaseAdapter.__init__` doesn't accept `**kwargs`. Forwarding them causes confusing `TypeError` at adapter construction time instead of a clear API error. Explicit params only.

---

## D-045: No Hyphens in Provider Names

**Decision**: Provider name regex allows underscores but not hyphens: `^[a-z][a-z0-9_]*$`.

**Alternatives considered**:
- Keep hyphens and auto-convert to underscores at import time

**Rationale**: Provider name maps to Python module name via convention. Hyphens are invalid in Python identifiers. Allowing them would pass validation but fail at import.

---

## D-046: Lazy Adapter Imports

**Decision**: Adapter classes lazy-loaded via `__getattr__` in `__init__.py`, not eagerly imported.

**Alternatives considered**:
- Remove adapters from `__init__.py` entirely
- Keep eager imports

**Rationale**: `import arcllm` should not trigger httpx loading. Adapters loaded on-demand by `load_model()` or explicit attribute access.

---

## D-047: Wrapper Module Pattern

**Decision**: Wrapper classes (middleware pattern) — each module is an `LLMProvider` wrapping an inner provider.

**Alternatives considered**:
- If-checks in `invoke()` — simple but tightly coupled
- Decorator pattern — similar but less discoverable
- Event hooks — powerful but complex
- Subclass mixin — fragile with multiple modules

**Rationale**: Composable, testable independently, transparent to agents. `Retry(Fallback(adapter))` — each module intercepts `invoke()`, does its thing, delegates to inner. Scales to N modules without adapter changes.

---

## D-048: Separate Retry and Fallback Modules

**Decision**: Two separate modules: `RetryModule` and `FallbackModule` (not combined).

**Alternatives considered**:
- Combined `ResilienceModule` with both behaviors

**Rationale**: Single responsibility. Independently configurable. Can use one without the other. Agent that only needs retry doesn't pay for fallback code.

---

## D-049: Retry Triggers

**Decision**: Retry on HTTP 429/500/502/503/529 + `httpx.ConnectError` + `httpx.TimeoutException`.

**Alternatives considered**:
- Retry all 5xx
- Configurable-only with no defaults

**Rationale**: Industry standard retryable codes. 529 is Anthropic-specific overload. Connection and timeout errors are always transient. Non-retryable codes (400, 401, 403) fail immediately.

---

## D-050: Exponential Backoff with Jitter

**Decision**: `min(base * 2^attempt + uniform(0, backoff), max_wait)` — exponential backoff with proportional jitter.

**Alternatives considered**:
- Fixed delay — no backoff, poor for sustained failures
- Exponential without jitter — thundering herd problem
- Full jitter: `uniform(0, backoff)` replacing backoff entirely — too random

**Rationale**: Exponential backoff increases wait time between retries. Jitter proportional to backoff (not fixed to base) decorrelates concurrent retriers more effectively at higher retry counts.

**Note**: Originally implemented with `uniform(0, base)` (fixed jitter). Changed to `uniform(0, backoff)` (proportional) during review — see D-052.

---

## D-051: Config-Driven Fallback Chain

**Decision**: Config-driven fallback chain with on-demand `load_model()` for each fallback provider.

**Alternatives considered**:
- Pre-loaded fallback adapters at construction time

**Rationale**: Only creates fallback adapters when needed. Chain order from config.toml. On primary failure, walks the chain calling `load_model(provider_name)` for each. If all fail, raises the original (primary) error.

---

## D-052: Proportional Jitter (Review Fix)

**Decision**: Changed jitter from `uniform(0, self._backoff_base)` to `uniform(0, backoff)` — jitter scales with backoff.

**Alternatives considered**:
- Keep fixed jitter `uniform(0, base)` — simpler but less effective at higher retry counts
- Full jitter: `uniform(0, backoff)` replacing backoff entirely — too random, loses exponential growth

**Rationale**: Flagged during 6-agent review (architect-reviewer). At attempt 3 with base=1.0, backoff=8.0 but jitter was only 0-1.0 — ineffective decorrelation. Proportional jitter (0 to 8.0) properly spreads retriers at all attempt levels.

---

## D-053: Module Config Validation (Review Fix)

**Decision**: Bounds validation in `RetryModule` and `FallbackModule` constructors.

**Alternatives considered**:
- Pydantic config models — more structured but adds complexity for 3-4 fields
- No validation — rely on runtime errors (division by zero, negative sleep)

**Rationale**: Flagged by 3 review agents (security, QA, architecture). Invalid configs should fail at construction, not during operation. `max_retries >= 0`, `backoff_base > 0`, `max_wait > 0`, `chain length <= 10`. Consistent with fail-fast philosophy (D-032).

---

## D-054: Module Settings Cache (Review Fix)

**Decision**: Pre-extract module settings from `model_dump()` into `_module_settings_cache` dict.

**Alternatives considered**:
- Call `model_dump()` each time — wasteful, 2x per `load_model()` call
- Store raw pydantic objects and access attributes — more coupling to pydantic internals

**Rationale**: Flagged by performance-engineer review. `_resolve_module_config()` is called twice per `load_model()` (once for retry, once for fallback). Pre-extracting settings on first global config load avoids repeated pydantic serialization. Cache cleared alongside other caches via `clear_cache()`.

---

## D-055: Token Bucket Algorithm

**Decision**: Token bucket algorithm for rate limiting — capacity = burst size, refill rate = RPM/60 tokens/sec.

**Alternatives considered**:
- Sliding window counter — smoother but more complex, no burst allowance
- Leaky bucket — fixed rate, no bursts, highest latency
- Adaptive — reactive (gets 429s before adjusting), complex, hard to reason about

**Rationale**: Allows bursts (good for agents waking simultaneously), enforces average rate. Battle-tested in production systems (nginx, AWS API Gateway, Stripe). Simple to implement with well-defined math.

---

## D-056: Per-Provider Shared Buckets

**Decision**: Rate limit buckets are shared per provider — all agents using the same API key share one bucket.

**Alternatives considered**:
- Per-model-instance — each `load_model()` gets its own bucket (multiplies effective rate)
- Global single bucket — all providers share one (doesn't match provider rate limits)
- Per-model per-provider — too granular, providers limit by key not model

**Rationale**: Matches how provider rate limits actually work. 100 agents sharing an Anthropic key with 60 RPM must collectively stay under 60 RPM. Per-instance would each think they have 60 RPM.

---

## D-057: Module-Level Bucket Registry

**Decision**: Module-level `_bucket_registry` dict in `rate_limit.py` maps provider names to `TokenBucket` instances.

**Alternatives considered**:
- Class-level dict on `RateLimitModule` — harder to test, same effect
- Separate SharedState singleton — over-engineered for a dict

**Rationale**: Simple, testable via `clear_buckets()`, consistent with the config cache pattern in `registry.py`. `clear_cache()` hooks into `clear_buckets()` automatically.

---

## D-058: Block + WARNING on Throttle

**Decision**: When bucket is empty, `await asyncio.sleep()` until token refills. Emit WARNING log with provider name and wait duration.

**Alternatives considered**:
- Raise exception (immediate fail) — agents must handle, adds complexity
- Callback/event notification — over-engineered for logging
- Silent wait — no observability, hard to diagnose slow calls

**Rationale**: Transparent to agents (`model.invoke()` just takes longer), ops gets visibility via WARNING logs. Best of both worlds.

---

## D-059: Separate burst_capacity Config

**Decision**: `burst_capacity` is a separate config param, defaults to `requests_per_minute`, overridable via `load_model()`.

**Alternatives considered**:
- Always equal to RPM — no separate config
- Hardcoded burst factor (e.g., 2x RPM) — inflexible

**Rationale**: Separate param gives fine-grained control. Default = RPM means zero config needed. Override at call site for specific use cases.

---

## D-060: Rate Limit Innermost in Stack

**Decision**: Stacking order: `Retry(Fallback(RateLimit(adapter)))` — rate limit is innermost module.

**Alternatives considered**:
- Outermost — would throttle retries and fallbacks, not just API calls
- Between retry and fallback — inconsistent semantics

**Rationale**: Rate limit wraps the adapter directly. Each actual API call (including retries and fallback attempts) is individually rate-limited. This matches the intent: throttle outgoing requests.

---

## D-061: Provider Name from inner.name

**Decision**: Use `inner.name` property as the bucket registry key.

**Alternatives considered**:
- Separate `provider_name` config key — redundant, error-prone
- Read from provider TOML — not available at module construction

**Rationale**: `LLMProvider.name` is already defined on every adapter. No extra config, no ambiguity.

---

## D-062: Config Validation (RPM > 0, burst >= 1)

**Decision**: Validate `requests_per_minute > 0` and `burst_capacity >= 1` at construction, raise `ArcLLMConfigError`.

**Alternatives considered**:
- Clamp to minimums silently — hides bugs
- Warning log only — allows runtime errors later

**Rationale**: Fail fast at construction. Consistent with RetryModule/FallbackModule validation pattern (D-053).

---

## D-063: clear_buckets() + clear_cache() Hook

**Decision**: `clear_buckets()` function in `rate_limit.py`, hooked into `registry.clear_cache()`.

**Alternatives considered**:
- Fixture-only cleanup — fragile, easy to forget
- No shared state (per-instance buckets) — defeats per-provider sharing (D-056)

**Rationale**: Test isolation requires clearing shared state. `clear_cache()` already exists for config caches; adding `clear_buckets()` there ensures automatic cleanup.

---

## D-064: Telemetry Output — Structured Logging Only

**Decision**: Structured logging only — no callback, no accumulator.

**Alternatives considered**:
- Callback function — more flexible but adds functions to `load_model()` config
- In-memory accumulator — useful for budget but not telemetry's concern
- Both logging + callback — over-engineered for a first version

**Rationale**: Simple, toggle-able via config. Budget and OTel handle their own concerns. No functions in `load_model()` config keeps the interface clean.

---

## D-065: Telemetry Cost Calculation

**Decision**: Calculate and log `cost_usd` per call from provider pricing metadata.

**Alternatives considered**:
- Log tokens only, no cost — leaves cost calculation to external tools
- Separate cost module — more modular but adds another module for a simple formula

**Rationale**: Pricing already in provider TOML. Cost per call is essential for budget tracking and ops visibility. Formula is simple: `(tokens * cost_per_1m) / 1_000_000`.

---

## D-066: Pricing Injection via setdefault()

**Decision**: `load_model()` injects pricing from ProviderConfig model metadata into telemetry config dict via `setdefault()`.

**Alternatives considered**:
- TelemetryModule reads ProviderConfig directly — creates coupling to config layer
- Separate pricing config section — duplicates data already in provider TOML

**Rationale**: Pricing lives in provider TOML. TelemetryModule shouldn't know about ProviderConfig. `setdefault()` allows explicit overrides in kwarg dict to win.

---

## D-067: Telemetry Stack Position — Outermost

**Decision**: Telemetry outermost: `Telemetry(Retry(Fallback(RateLimit(adapter))))`.

**Alternatives considered**:
- Innermost (just adapter time) — misses retry/fallback/rate-limit wait time
- Between retry and fallback — inconsistent semantics

**Rationale**: Measures total wall-clock including retries, fallback, and rate-limit wait. Most useful operational metric for understanding end-to-end call latency.

---

## D-068: Telemetry Log Level — INFO Default

**Decision**: INFO by default, configurable via `log_level` in config dict.

**Alternatives considered**:
- DEBUG (too quiet by default) — telemetry should be visible when enabled
- Fixed INFO (not configurable) — inflexible for noisy environments

**Rationale**: Telemetry should be visible when enabled. Configurable for environments where it creates too much noise.

---

## D-069: Telemetry Log Fields

**Decision**: provider, model, duration_ms, input_tokens, output_tokens, total_tokens, cache_read/write_tokens (conditional), cost_usd, stop_reason.

**Alternatives considered**:
- Minimal (just timing + cost) — insufficient for debugging
- Include raw response size — adds complexity, raw is for debugging only

**Rationale**: Complete operational visibility per call. Cache tokens omitted when absent to reduce noise.

---

## D-070: Audit Output — Structured Logging (Shared Helper)

**Decision**: Structured logging using shared `log_structured()` helper from `_logging.py`.

**Alternatives considered**:
- Manual f-string building (like original telemetry) — inconsistent, more code
- Separate audit log format — diverges from telemetry pattern

**Rationale**: Consistent with telemetry. Shared helper handles sanitization, None omission, and float formatting automatically. One place to change log format across all modules.

---

## D-071: Audit Log Level — INFO Default

**Decision**: INFO by default, configurable via `log_level`. Same validation pattern as TelemetryModule.

**Alternatives considered**:
- DEBUG default — audit should be visible by default for compliance
- CRITICAL — too restrictive

**Rationale**: Audit events should be visible by default. Same validation pattern (set of valid names, `ArcLLMConfigError` on invalid) ensures consistency.

---

## D-072: Audit Fields — Metadata Only

**Decision**: provider, model, message_count, stop_reason, tools_provided (conditional), tool_calls (conditional), content_length.

**Alternatives considered**:
- Include raw content — PII exposure risk
- Include timing — telemetry already handles this
- Include token usage — telemetry already handles this

**Rationale**: Covers all compliance-relevant metadata (NIST 800-53 AU-3) without PII exposure. content_length provides size metric without content.

---

## D-073: PII-Safe Audit by Default

**Decision**: No raw message content or response content logged by default.

**Alternatives considered**:
- Always log content — unacceptable for classified environments
- Truncate content — still exposes partial PII
- Hash content — loses debugging utility

**Rationale**: Federal compliance (NIST 800-53 AU-3): audit trail must exist but must not create new PII exposure vectors. Audit logs may be stored in systems with different classification levels than the data itself.

---

## D-074: Content Opt-In at DEBUG Level

**Decision**: `include_messages` and `include_response` boolean flags. Content logged at DEBUG level (separate from main audit record).

**Alternatives considered**:
- Log at same level as audit record — no additional safety gate
- Require both flags to be set — overly restrictive

**Rationale**: Double opt-in: config flag must be True AND DEBUG logging must be enabled. In production, DEBUG is typically disabled. Even if config flag is accidentally left on, content won't appear unless DEBUG is explicitly enabled.

---