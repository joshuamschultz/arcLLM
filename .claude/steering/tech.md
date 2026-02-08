# Technical Context

> This document provides stable technical context that informs all feature specifications.
> Feature-specific details go in `.claude/specs/{feature}/` documents.

## Validation Checklist

- [x] Technology stack documented
- [x] Project commands listed
- [x] Quality thresholds defined
- [x] Error handling patterns documented
- [x] Testing approach defined
- [x] Security requirements listed
- [ ] No [NEEDS CLARIFICATION] markers

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Language | Python | 3.11+ | Strict typing, `tomllib` in stdlib |
| Types/Validation | Pydantic | v2.0+ | Discriminated unions, model validation |
| HTTP Client | httpx | 0.25+ | Async-native, lightweight |
| Config | TOML (tomllib) | stdlib | Zero dependency for config parsing |
| Async | asyncio | stdlib | Async-first with sync wrapper |

### Key Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| pydantic | Type validation, serialization, JSON schema | >=2.0 |
| httpx | Async HTTP client for provider API calls | >=0.25 |

### Development Tools

| Tool | Purpose | Config File |
|------|---------|-------------|
| pytest | Test runner | `pyproject.toml [tool.pytest]` |
| pytest-asyncio | Async test support | `pyproject.toml` (`asyncio_mode = "auto"`) |
| pip | Package management | `pyproject.toml` |

### Explicitly NOT Used

| Technology | Why Not |
|------------|---------|
| pyyaml | TOML is stdlib, zero dependency |
| requests | httpx is async-native |
| Provider SDKs (anthropic, openai) | Direct HTTP via httpx, no SDK dependency |
| Any framework | Library, not framework |

---

## Project Commands

### Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Python REPL with arcllm available
python -c "from arcllm import load_model"
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_types.py -v

# Run with coverage
pytest --cov=arcllm

# Run async tests (auto mode configured)
pytest tests/test_anthropic.py -v
```

### Quality Checks

```bash
# Type checking (when mypy is added)
mypy src/arcllm/

# Run all tests + coverage
pytest --cov=arcllm --cov-report=term-missing
```

---

## Quality Thresholds

### Coverage Requirements

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| Line Coverage | >=80% | CI gate |
| Branch Coverage | >=75% | CI gate |
| Core types.py | 100% | Mandatory |
| Adapters | >=90% | CI gate |

### Code Quality

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| Type Errors | 0 | CI gate (mypy strict) |
| Complexity | <=10 per function | Review |
| Duplication | <=3% | Review |

### Security

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| API Keys in Code/Config | 0 | Audit scan |
| Critical Vulnerabilities | 0 | CI gate |
| Dependency Audit | Pass | CI gate |

### Performance

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Abstraction Overhead | <1ms per call | Benchmark suite |
| Import Time | <100ms | Startup benchmark |
| Memory per Model Object | Minimal (stateless) | Profiling |

---

## Technical Constraints

| ID | Constraint | Type | Rationale |
|----|------------|------|-----------|
| CON-1 | Python 3.11+ required | Technical | stdlib tomllib, modern typing |
| CON-2 | Async-first, sync wrapper available | Technical | Agent loops are typically async |
| CON-3 | No conversation state in model object | Architecture | Agent manages its own messages |
| CON-4 | Provider quirks stay in adapters | Architecture | Core types must be clean/universal |
| CON-5 | Config in TOML, never in code | Architecture | Teams own their provider configs independently |
| CON-6 | API keys from environment only | Security | Never in config files, vault integration later |
| CON-7 | <1ms overhead per call | Performance | Abstraction must be invisible |
| CON-8 | No provider SDK dependencies | Architecture | Direct HTTP via httpx |

---

## Error Handling Pattern

### Exception Hierarchy

```python
ArcLLMError                    # Base — catch all arcllm errors
├── ArcLLMParseError           # Tool call argument parse failure
│   ├── raw_string: str        # The unparseable string
│   └── original_error: Exception  # The underlying error
└── ArcLLMConfigError          # Config validation failure
    └── message: str           # What went wrong
```

### Error Philosophy

- **Fail fast, fail loud**: Raise `ArcLLMParseError` immediately on tool call parse failure. Don't sanitize or fallback — the agent loop handles errors.
- **Attach raw data**: Every error includes the raw input that caused it. Agent can log, retry, or escalate.
- **No silent failures**: If a provider returns unexpected format, raise rather than guess.

### Tool Call Argument Parsing

```
Provider returns arguments →
  Is it a dict? → Pass through (already parsed)
  Is it a string? → json.loads() →
    Success → Return parsed dict
    Failure → Raise ArcLLMParseError(raw_string=the_string, original_error=the_json_error)
```

---

## Testing Approach

### Test Pyramid

```
         /\
        /  \  Integration (20%)
       /    \  Full agentic loop with mock provider
      /------\
     /        \  Adapter Tests (30%)
    /          \  Per-provider translation correctness
   /--------------\
  /                \  Unit (50%)
 /                  \  Types, config, parsing, exceptions
```

### Test File Conventions

| Test Type | Location | Naming |
|-----------|----------|--------|
| Unit (types) | `tests/test_types.py` | `test_{type}_{scenario}` |
| Unit (config) | `tests/test_config.py` | `test_{loader}_{scenario}` |
| Adapter | `tests/test_{provider}.py` | `test_{provider}_{operation}` |
| Integration | `tests/test_agentic_loop.py` | `test_{scenario}_loop` |

### Testing Libraries

| Purpose | Library | Usage |
|---------|---------|-------|
| Test Runner | pytest | All tests |
| Async Support | pytest-asyncio | Async adapter/integration tests |
| HTTP Mocking | httpx mock or respx | Mock provider API responses |
| Fixtures | pytest fixtures | Model objects, sample messages, configs |

### Test Data Strategy

| Approach | Use Case |
|----------|----------|
| Fixtures | Sample messages, tool calls, provider responses |
| Factories | Generating varied ContentBlock combinations |
| Recorded responses | Real provider responses captured for regression |
| Mock servers | httpx-level mocks for adapter tests |

---

## Security Requirements

### API Key Management

- [x] Keys from environment variables only (`os.environ`)
- [x] Provider TOML specifies `api_key_env` (variable name), not the key itself
- [ ] Vault integration (future — module in Step 14)
- [ ] Request signing (future — module in Step 14)

### Data Protection

- [x] No PII in core types or logs by default
- [ ] PII redaction hooks (future — security module)
- [x] `raw` field on LLMResponse for debugging only, not logged
- [x] TLS enforced (httpx default)

### Audit Trail

- [ ] Every LLM call logged when audit module enabled (Step 11)
- [ ] Reasoning/thinking content captured (Step 11)
- [x] Usage tracking (tokens, cache, reasoning) in every response

---

## API Conventions

### Not applicable

ArcLLM is a library, not a service. No REST/GraphQL API.

### Python API Contract

```python
# Public API surface (from __init__.py)
from arcllm import load_model                    # Entry point
from arcllm import Message, Tool, LLMResponse    # Core types
from arcllm import ArcLLMError, ArcLLMParseError # Exceptions

# Usage pattern
model = load_model("anthropic")
response = await model.invoke(messages, tools=tools)
```

---

## Activity Hints Reference

> Used in PLAN.md for agent selection during implementation.

| Activity | Description | Typical Agent |
|----------|-------------|---------------|
| `unit-testing` | Write unit tests for types, config, parsing | test-implementation-agent |
| `integration-testing` | Write agentic loop integration tests | test-implementation-agent |
| `backend-development` | Implement adapters, config loader, registry | python-pro |
| `type-design` | Design pydantic types and discriminated unions | python-pro |
| `config-design` | TOML config structure and loading | python-pro |
| `security-review` | Key management, audit trail, PII | security-engineer |
| `performance-optimization` | Benchmark overhead, async optimization | performance-engineer |
| `run-tests` | Execute test suite | quality-checker |

---

## Open Questions (Technical)

None currently — all technical decisions are locked in the master prompt.

---

## References

- Master Prompt: `/Users/joshschultz/AI/arcllm/arcllm-master-prompt.md`
- PRD: `/Users/joshschultz/AI/arcllm/arcllm-prd.md`
- Pydantic v2 docs: https://docs.pydantic.dev/latest/
- httpx docs: https://www.python-httpx.org/
