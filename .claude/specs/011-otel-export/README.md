# Spec: 011-otel-export

## Metadata

| Field | Value |
|-------|-------|
| **ID** | 011 |
| **Name** | OpenTelemetry Export |
| **Type** | Library/Backend |
| **Status** | PENDING |
| **Created** | 2026-02-09 |
| **Confidence** | High (>70%) — Module pattern established in 007-010, all 10 decisions made |

## Summary

Adds OpenTelemetry (OTel) distributed tracing to ArcLLM via two changes: (1) a new `OtelModule` that creates a root span per `invoke()` call with GenAI semantic convention attributes plus custom `arcllm.*` attributes, and (2) deep integration in `BaseModule` that provides `_tracer` and `_span()` helper so every existing module (retry, fallback, rate_limit, telemetry, audit) creates child spans automatically. Config-driven SDK setup via `[modules.otel]` TOML section supports OTLP/console/none exporters with auth headers, TLS (mTLS), batch tuning, sampling, and resource attributes. `opentelemetry-api` is a core dependency (zero-cost no-op when SDK not configured); `opentelemetry-sdk` and exporters are optional extras (`pip install arcllm[otel]`). OtelModule sits outermost in the stack and auto-nests under agent framework spans when present.

## Source

ArcLLM Build Step 13. Decisions made interactively via `/build-arcllm 13` session.

## Decisions Log

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| D-079 Integration depth | Deep — BaseModule + per-module spans | Full trace waterfall showing retry attempts, fallback hops, rate-limit waits. Richest operational data for 10K agents. | 2026-02-09 |
| D-080 API dependency | Core dep (opentelemetry-api) | ~100KB, zero transitive deps, designed for library authors. No-op when SDK not configured. Always available, no import guards. | 2026-02-09 |
| D-081 Root span | OtelModule creates root, auto-nests under parent | Works standalone (traces without agent framework) AND auto-nests as child span when agent framework provides parent context. | 2026-02-09 |
| D-082 Attributes | GenAI semantic conventions + custom arcllm.* | Standard gen_ai.* for vendor dashboard auto-detection (Datadog, Grafana) plus custom arcllm.* for cost, retry, rate-limit details. | 2026-02-09 |
| D-083 SDK setup | Config-driven via TOML | Consistent with all other ArcLLM config. [modules.otel] section drives exporter, endpoint, protocol, sampling. | 2026-02-09 |
| D-084 SDK packages | Optional extras (pip install arcllm[otel]) | SDK + exporters are heavier (~1MB). Clear ArcLLMConfigError if enabled but not installed. Keeps base install light. | 2026-02-09 |
| D-085 TelemetryModule overlap | Keep both, separate concerns | TelemetryModule = structured logs (grep/Splunk). OtelModule = distributed traces (Jaeger/Datadog). Different pillars, both valuable. | 2026-02-09 |
| D-086 Span mechanism | _tracer + _span() helper in BaseModule | Each module explicitly wraps its logic. Gives modules control over span timing and attributes. Works with complex retry/fallback logic. | 2026-02-09 |
| D-087 Error recording | Record exceptions as events, ERROR only on final failure | Individual retry attempts: record exception event but status OK (handled). Root span ERROR only when operation truly fails. Clean trace UI. | 2026-02-09 |
| D-088 Config shape | Full enterprise: auth, TLS, batch tuning, resource attrs | Headers for OTLP auth, mTLS for federal/zero-trust, batch tuning for 10K agents, resource attributes for deployment metadata. | 2026-02-09 |

## Learnings

(To be populated during implementation)

## Cross-References

- PRD: `PRD.md` (this directory)
- SDD: `SDD.md` (this directory)
- PLAN: `PLAN.md` (this directory)
- Step 10 Spec: `.claude/specs/009-telemetry-module/`
- Step 11 Spec: `.claude/specs/010-audit-trail-module/`
- Step 8 Spec: `.claude/specs/008-rate-limiter/`
- Step 7 Spec: `.claude/specs/007-module-system-retry-fallback/`
- BaseModule: `src/arcllm/modules/base.py`
- Registry: `src/arcllm/registry.py`
- TelemetryModule: `src/arcllm/modules/telemetry.py`
- AuditModule: `src/arcllm/modules/audit.py`
- RetryModule: `src/arcllm/modules/retry.py`
- FallbackModule: `src/arcllm/modules/fallback.py`
- RateLimitModule: `src/arcllm/modules/rate_limit.py`
- Config: `src/arcllm/config.toml` (`[modules.otel]`)
- Product PRD: `docs/arcllm-prd.md`
- Decision Log: `.claude/decision-log.md`
- Steering: `.claude/steering/`
