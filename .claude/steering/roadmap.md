# Product Roadmap

> This document provides implementation planning context that informs feature execution.
> Feature-specific tasks go in `.claude/specs/{feature}/PLAN.md` documents.

## Validation Checklist

- [x] Current phase defined
- [x] Phase goals clear
- [x] Dependencies mapped
- [x] Parallel work identified
- [x] Success criteria defined
- [ ] No [NEEDS CLARIFICATION] markers

---

## Roadmap Overview

### Current Phase

**Phase**: Phase 1 — Core Foundation
**Steps**: 1-6 (of 16)
**Focus**: Types, config, adapters, registry — prove the abstraction works

### Phase Summary

| Phase | Name | Steps | Focus | Status |
|-------|------|-------|-------|--------|
| 1 | Core Foundation | 1-6 | Types, config, two adapters, registry, `load_model()` | Current |
| 2 | Module System | 7-9 | Fallback, retry, rate limiter, router — validate module pattern | Planned |
| 3 | Observability | 10-13 | Telemetry, audit, budget, OpenTelemetry | Planned |
| 4 | Enterprise | 14-16 | Security layer, local providers, full integration test | Planned |

---

## Implementation Philosophy

### Specification Compliance

> Each step has a plan file: `arcllm-step-{NN}-*.md`

#### Before Each Step

1. Read step plan in `/Users/joshschultz/AI/arcllm/arcllm-step-{NN}-*.md`
2. Walk through tasks conceptually (teaching mode — see arcllm-builder skill)
3. Present any remaining decisions to Josh
4. Build incrementally, verify each task

#### Deviation Protocol

If implementation cannot follow plan exactly:

1. **Document** the deviation and reason
2. **Discuss with Josh** before proceeding
3. **Update plan** if deviation is an improvement
4. **Record decision** in `arcllm-state.json`

### TDD Approach

> Each step follows Test-Driven Development.

```
For each task:
1. Understand the concept (what and why)
2. Write tests first (when applicable)
3. Implement to pass tests
4. Verify acceptance criteria
```

---

## Phase 1: Core Foundation (Steps 1-6)

### Goals

- [x] Step plan exists for Step 1
- [ ] Working Python package with validated types
- [ ] Config loading from TOML (global + per-provider)
- [ ] Anthropic adapter with tool calling support
- [ ] Agentic loop test proving full cycle works
- [ ] OpenAI adapter validating the abstraction
- [ ] `load_model()` public API working

### Build Order

| Step | What | Depends On | Status |
|------|------|------------|--------|
| 1 | Project setup + pydantic types | None | Planned (plan exists) |
| 2 | Config loading (global + provider TOMLs) | Step 1 | Not started |
| 3 | Anthropic adapter + tool support | Steps 1, 2 | Not started |
| 4 | Test harness — agentic loop | Step 3 | Not started |
| 5 | OpenAI adapter | Steps 1, 2, 3 | Not started |
| 6 | Provider registry + load_model() | Steps 1-5 | Not started |

### Dependencies

```
Step 1 (types) ──→ Step 2 (config) ──→ Step 3 (anthropic) ──→ Step 4 (test harness)
                                  └──→ Step 5 (openai)
Step 3 + Step 5 ──→ Step 6 (registry + load_model)
```

### Parallel Opportunities

| Sequential (must be in order) | Parallel (after Step 2) |
|-------------------------------|------------------------|
| Steps 1 → 2 → 3 (foundation) | Step 5 (OpenAI) can start after Step 2, parallel with Step 3 |

### Phase 1 Acceptance

- [ ] `pip install -e ".[dev]"` works
- [ ] `from arcllm import load_model` imports cleanly
- [ ] `model = load_model("anthropic")` returns working model
- [ ] `model = load_model("openai")` returns working model
- [ ] Full agentic loop test passes (messages → tool calls → tool results → response)
- [ ] All tests pass with >=80% coverage

---

## Phase 2: Module System (Steps 7-9)

### Goals

- [ ] Fallback + retry module validates module pattern
- [ ] Rate limiter validates module composability
- [ ] Router module for model selection rules

### Build Order

| Step | What | Depends On | Status |
|------|------|------------|--------|
| 7 | Fallback + retry | Phase 1 complete | Not started |
| 8 | Rate limiter | Phase 1 complete | Not started |
| 9 | Router | Phase 1 complete | Not started |

### Key Decision (Future)

Steps 7-9 will define the **module interface pattern**. This is the most important decision in Phase 2 — how modules compose with adapters. Options will include decorator pattern, middleware chain, or wrapper classes.

---

## Phase 3: Observability (Steps 10-13)

### Goals

- [ ] Telemetry (timing, tokens, cost per call)
- [ ] Audit trail (call logging, reasoning capture)
- [ ] Budget manager (spending limits)
- [ ] OpenTelemetry export

### Build Order

| Step | What | Depends On | Status |
|------|------|------------|--------|
| 10 | Telemetry | Phase 1 | Not started |
| 11 | Audit trail | Phase 1 | Not started |
| 12 | Budget manager | Step 10 (needs cost data) | Not started |
| 13 | Observability (OTel) | Step 10 | Not started |

---

## Phase 4: Enterprise (Steps 14-16)

### Goals

- [ ] Security layer (vault, signing, PII redaction)
- [ ] Local/open-source providers (Ollama, vLLM)
- [ ] Full integration test with all modules

### Build Order

| Step | What | Depends On | Status |
|------|------|------------|--------|
| 14 | Security layer | Phases 1-3 | Not started |
| 15 | Local providers (Ollama, vLLM) | Phase 1 | Not started |
| 16 | Integration test | All steps | Not started |

---

## Task Execution Framework

### Task Metadata Tags

> Used in step plan files for tracking.

| Tag | Purpose | Example |
|-----|---------|---------|
| `[depends: StepN]` | Step dependency | `[depends: Step1]` |
| `[activity: type]` | Agent selection hint | `[activity: type-design]` |

### Task States

| State | Meaning | Next Action |
|-------|---------|-------------|
| `[ ]` | Not started | Begin when dependencies complete |
| `[~]` | In progress | Continue |
| `[x]` | Complete | Verify, move to next |
| `[!]` | Blocked | Resolve blocker |

---

## Success Criteria Framework

### Automated Verification

> Run these before considering any step complete.

```bash
# All tests pass
pytest -v

# Coverage meets threshold
pytest --cov=arcllm --cov-report=term-missing

# Package installs cleanly
pip install -e ".[dev]"

# Imports work
python -c "from arcllm import Message, LLMResponse"
```

### Manual Verification

> Per the arcllm-builder skill — Josh verifies understanding of every piece.

| Category | Criteria | Reviewer |
|----------|----------|----------|
| Understanding | Josh can explain every type and why it exists | Josh |
| Functionality | `.complete()` works with real provider | Josh + tests |
| Tool Calling | Full agentic loop cycle passes | Integration test |
| Config | TOML changes reflected without code changes | Manual test |

---

## Risk Register

### Active Risks

| Risk | Impact | Likelihood | Mitigation | Status |
|------|--------|------------|------------|--------|
| Provider API changes during build | M | L | Adapter isolation, test per provider | Monitoring |
| Pydantic v2 forward ref complexity | L | M | model_rebuild() approach, test early | Step 1 covers this |
| Tool call parsing edge cases | H | M | Comprehensive test matrix per provider | Steps 3, 5 |
| Module composition complexity | M | M | Design pattern decision in Step 7 | Future |

---

## Milestone Tracking

### Phase 1 Milestones

| Milestone | Step | Criteria | Status |
|-----------|------|----------|--------|
| Types validated | 1 | All 12 type tests pass | Not started |
| Config working | 2 | Global + provider TOML loading | Not started |
| First provider | 3 | Anthropic adapter with tool calls | Not started |
| Abstraction proven | 5 | Two providers, same interface | Not started |
| Public API | 6 | `load_model()` works end-to-end | Not started |

---

## Open Questions (Roadmap)

None currently — build order is locked in the master prompt.

---

## References

- Master Prompt (build order): `/Users/joshschultz/AI/arcllm/arcllm-master-prompt.md`
- PRD (full requirements): `/Users/joshschultz/AI/arcllm/arcllm-prd.md`
- Step 1 Plan: `/Users/joshschultz/AI/arcllm/arcllm-step-01-plan.md`
- State tracking: `/Users/joshschultz/AI/arcllm/.claude/arcllm-state.json`
- Builder skill: `.claude/skills/arcllm-builder/SKILL.md`
