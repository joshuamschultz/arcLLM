# Product Context

> This document provides stable product context that informs all feature specifications.
> Feature-specific details go in `.claude/specs/{feature}/` documents.

## Validation Checklist

- [x] Vision statement defined
- [x] All personas documented
- [x] User journey framework established
- [x] Success metrics framework defined
- [x] Business constraints listed
- [x] Domain glossary populated
- [ ] No [NEEDS CLARIFICATION] markers

---

## Vision & Mission

### Vision

A world where autonomous agents communicate with any LLM provider through a single, auditable, rock-solid abstraction — no SDK lock-in, no hidden state, no surprises.

### Mission

ArcLLM normalizes LLM communication for agentic tool-calling loops. Minimal core that does one thing perfectly. Everything else is opt-in modules.

### Value Proposition

- **vs. LiteLLM**: Cleaner architecture, no double-serialization bugs, opt-in modules instead of baked-in complexity
- **vs. Direct SDKs**: Provider-agnostic, normalized response types, auditable by default
- **vs. Frameworks (LangChain, etc.)**: Not a framework — a library. No opinions about agent architecture, just clean LLM communication
- **vs. pi-ai**: Python-native, config-driven model metadata, module system for enterprise needs (budget, audit, routing)

---

## User Personas

### Primary Persona: Agent Developer

- **Role/Title**: AI/ML Engineer building autonomous agents
- **Demographics**: Senior-level, deep Python experience, building production agent systems
- **Goals**: Import a library, call `load_model()`, get normalized responses with tool calls. No ceremony. No state management. No SDK lock-in.
- **Pain Points**: LiteLLM's double-serialization bugs across providers. SDK differences between Anthropic/OpenAI forcing adapter code in every project. No clean way to audit/trace LLM calls in production.
- **Behaviors**: Writes agentic loops that call LLMs hundreds of times per session. Manages message history externally. Needs tool calling to work flawlessly.

### Secondary Persona: Platform Engineer

- **Role/Title**: Infrastructure engineer operating agent fleets at scale
- **Demographics**: DevOps/SRE background, manages thousands of concurrent agents
- **Goals**: Budget controls, rate limiting, telemetry, audit trails across all agents. Provider fallback when one goes down. Cost visibility.
- **Pain Points**: No unified observability across LLM providers. No spending controls. No way to route traffic between providers based on rules.
- **Behaviors**: Configures via TOML, monitors via OpenTelemetry, enforces budgets. Doesn't write agent logic — enables the people who do.

### Tertiary Persona: Security/Compliance Officer

- **Role/Title**: Security engineer or compliance reviewer at federal agency
- **Demographics**: FedRAMP/NIST background, audits production systems
- **Goals**: Every LLM call traceable. No API keys in config files. PII redaction hooks. Request signing for audit trails.
- **Pain Points**: Most LLM libraries treat security as an afterthought. No audit trail for what was sent to/received from LLMs.
- **Behaviors**: Reviews configs, checks audit logs, validates that keys are vault-sourced and calls are signed.

---

## User Journey Framework

> This is a library, not a SaaS product. Journey is developer-centric.

### Standard Journey Stages

1. **Discovery**: Developer hits LLM integration pain (provider switching, tool call bugs, no audit trail) and finds ArcLLM
2. **Evaluation**: `pip install arcllm`, reads types, tries `load_model()` + `.complete()` in a script
3. **Adoption**: Replaces direct SDK calls in one agent with ArcLLM. Sees normalized responses work.
4. **Expansion**: Enables modules (telemetry, budget, audit). Adds second provider. Configures fallback.
5. **Production**: Deployed across agent fleet. TOML configs per environment. Full audit trail.
6. **Advocacy**: Recommends to other teams. Contributes provider adapters.

### Key Touchpoints

| Stage | Touchpoint | Success Metric |
|-------|------------|----------------|
| Evaluation | `pip install` + first `.complete()` call | Works in <5 minutes |
| Adoption | Replace SDK in one agent | Zero behavior change, cleaner code |
| Expansion | Enable first module | Config-only change, no code rewrites |
| Production | Fleet deployment | <1ms overhead per call |

---

## Success Metrics Framework

> Library metrics, not SaaS metrics.

### Adoption Metrics

| Metric | Description | Tracking Method |
|--------|-------------|-----------------|
| Time to First Call | Minutes from `pip install` to successful `.complete()` | Manual benchmark |
| Provider Coverage | Number of providers with working adapters | Test suite |
| Module Adoption | Which optional modules are enabled in production | Telemetry (opt-in) |

### Quality Metrics

| Metric | Description | Tracking Method |
|--------|-------------|-----------------|
| Overhead | Latency added by abstraction layer | Benchmark suite |
| Tool Call Accuracy | Correct parse rate across providers | Integration tests |
| Error Clarity | Parse errors include raw string + original error | Unit tests |

### Reliability Metrics

| Metric | Description | Tracking Method |
|--------|-------------|-----------------|
| Test Coverage | Line/branch coverage on core | pytest-cov |
| Provider Parity | Same behavior across all providers | Cross-provider test suite |
| Uptime Impact | Library never causes downtime vs. direct SDK | Production monitoring |

### Security Metrics

| Metric | Description | Tracking Method |
|--------|-------------|-----------------|
| Key Exposure | Zero API keys in config files or logs | Audit scan |
| Audit Completeness | Every LLM call logged when audit module enabled | Audit trail validation |
| PII Leakage | Zero PII in logs/telemetry | Redaction tests |

---

## Business Constraints

### Compliance & Legal

| Requirement | Description | Impact |
|-------------|-------------|--------|
| FedRAMP Pathway | Must be deployable in FedRAMP-authorized environments | No external calls except to LLM providers. Config-only, no phone-home. |
| Federal Production | Used in CTG Federal production systems | Audit trail, key management, request signing required |
| No Vendor Lock-in | Must support multiple LLM providers | Clean adapter abstraction, no provider-specific leaks |

### Business Rules

| Rule | Description | Enforced By |
|------|-------------|-------------|
| Security First | Every design decision evaluated: security > control > functionality | Architecture review |
| Minimal Core | Core does ONE thing. Everything else is opt-in module. | Code review |
| No Conversation State | Model object holds config/metadata only. Agent manages messages. | Type system (no state fields) |
| Config-Driven | Model metadata, settings, module toggles in TOML. Not code. | Config loader |

### Scale Requirements

- **Concurrency**: Thousands of concurrent autonomous agents
- **Organizations**: BlackArc Systems, CTG Federal
- **Performance**: Abstraction adds <1ms overhead on calls that take 500-5000ms

---

## Competitive Landscape

### Primary Competitors

| Competitor | Strengths | Weaknesses | ArcLLM Differentiation |
|------------|-----------|------------|------------------------|
| LiteLLM | Broad provider support, OpenAI-compatible format, good routing/fallback | Double-serialization bugs in tool calls, monolithic, all-or-nothing | Modular, clean tool call handling, opt-in complexity |
| pi-ai | Clean architecture, model-object pattern, type-check+parse approach | TypeScript only, no enterprise modules, limited provider support | Python-native, config-driven, enterprise modules (audit, budget, security) |
| Direct SDKs (Anthropic, OpenAI) | First-party support, latest features | Provider lock-in, different APIs, no unified types | Provider-agnostic, normalized types, single interface |
| LangChain | Huge ecosystem, many integrations | Opinionated framework, heavy abstraction, not agent-focused | Library not framework, minimal core, agent-native |

### Market Position

Production-grade library for teams building autonomous agent systems at scale. Enterprise-focused (federal compliance, audit, budget). Not competing for hobbyist/prototype market.

---

## Risk Framework

### Risk Categories

| Category | Description | Mitigation Approach |
|----------|-------------|---------------------|
| Provider API Changes | LLM providers change APIs/response formats | Adapter isolation, integration test suite per provider |
| Tool Call Edge Cases | Provider-specific quirks in tool call handling | Type-check+parse pattern, comprehensive test matrix |
| Scale Issues | Performance degrades under concurrent load | Async-first design, benchmark suite, <1ms overhead target |
| Security Gaps | Audit trail or key management insufficient for federal | Security-first design principle, dedicated security module |
| Dependency Risk | Pydantic or httpx introduce breaking changes | Pin minimum versions, test against latest |

---

## Domain Glossary

| Term | Definition | Context |
|------|------------|---------|
| Adapter | Provider-specific translation layer (e.g., `adapters/anthropic.py`) | Translates ArcLLM types to/from provider API format |
| Agent | Autonomous software system that calls LLMs in a loop with tool use | ArcLLM's primary consumer — not a human user |
| Agentic Loop | The cycle: send messages → get tool calls → execute tools → send results → repeat | Core use case ArcLLM is built for |
| ContentBlock | Discriminated union type for message content (text, image, tool_use, tool_result) | Foundation type in `types.py` |
| Module | Opt-in functionality (telemetry, audit, budget, etc.) | Loaded explicitly, not baked into core |
| Provider | LLM service (Anthropic, OpenAI, Ollama, etc.) | Each gets an adapter and a TOML config |
| Tool Call | LLM requesting the agent execute a function | Returned in LLMResponse as list[ToolCall] |
| Tool Result | Agent's response after executing a tool call | Sent back as ToolResultBlock in next message |

---

## Open Questions (Product-Level)

None currently — architecture and product decisions are locked in the master prompt.

---

## References

- Master Prompt: `/Users/joshschultz/AI/arcllm/arcllm-master-prompt.md`
- PRD: `/Users/joshschultz/AI/arcllm/arcllm-prd.md`
- Reference implementations: LiteLLM, pi-ai (@mariozechner/pi-ai)
