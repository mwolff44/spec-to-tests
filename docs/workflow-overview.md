# Workflow overview — from specification to execution

Overview of the workflow proposed in the article series. This document serves as a reference for the reader who wants the complete picture at a glance.

## The workflow in five steps

```
┌──────────────────────────────────────────────────────────────┐
│ 1. SPECIFICATION                                             │
│    Human formalizes the intent:                              │
│      • User story → Gherkin                                  │
│      • Typed examples (table-driven, fixtures)               │
│      • Candidate properties (invariants, round-trip)        │
│      • Contracts / types (icontract, Zod, OpenAPI)           │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. TESTS                                                     │
│    Human writes (or strictly validates) tests BEFORE         │
│    any production code is written.                           │
│    Useful deterministic tools here:                           │
│      • Hypothesis ghostwriter (PBT skeletons)               │
│      • Pynguin / EvoSuite (structural tests)                │
│      • GraphWalker / ModelJUnit (model-based)                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. AI EXECUTION                                              │
│    The agent implements under the constraint of the tests:   │
│      • One cycle = one test = one commit                     │
│      • Persistent plan.md that the agent follows              │
│      • Hard rules from tdd-skill/agent-discipline.md          │
│      • RED→GREEN proven at commit by the §0 pre-commit gate   │
│        (tdd-skill/scripts/tdd-verify-cycle.sh)                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. VERIFICATION                                              │
│    Multi-agent (writer + critic) + deterministic tools:      │
│      • Critic-agent enforces TDD discipline                  │
│      • Mutation testing scoped to changes                    │
│      • Coverage gate (line + branch)                         │
│      • Lint + smells detector                                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. AUDIT                                                     │
│    Regular loop (monthly or quarterly):                      │
│      • Level 1 static cheap (15 min)                         │
│      • Level 2 dynamic (1 hour)                              │
│      • Level 3 AI-assisted (1 day)                           │
└──────────────────────────────────────────────────────────────┘
```

## Mapping articles → steps

| Article | Main step covered |
|---|---|
| 1 — *AI didn't kill tests* | General context, why the workflow |
| 2 — *Executable specification* | Step 1 |
| 3 — *Who writes the test, who writes the code?* | Steps 2 and 3, role distribution |
| 4 — *Measuring whether tests are worth something* | Step 4 (quality verification) |
| 5 — *Property-based testing* | Key tool for steps 2 and 4 |
| 6 — *Putting it into practice: React + Go* | Applying the workflow to a modern stack |
| 7 — *Launching execution: from plan to PR* | Step 3 in practice + step 5 (audit) |

## Tools referenced in the series

### Tests, frameworks and runners
- **Python**: pytest, [Hypothesis](https://hypothesis.readthedocs.io/), [mutmut](https://github.com/boxed/mutmut), [ruff](https://docs.astral.sh/ruff/)
- **TypeScript / React**: [Vitest](https://vitest.dev/), [React Testing Library](https://testing-library.com/), [MSW](https://mswjs.io/), [fast-check](https://fast-check.dev/), [StrykerJS](https://stryker-mutator.io/)
- **Go**: `testing` + [testify](https://github.com/stretchr/testify), [testcontainers-go](https://golang.testcontainers.org/), [rapid](https://github.com/flyingmutant/rapid), [gremlins](https://github.com/go-gremlins/gremlins), [golangci-lint](https://golangci-lint.run/)
- **Cross-stack**: [Pact](https://docs.pact.io/), [Playwright](https://playwright.dev/)

### Deterministic test generation tools
- [Hypothesis ghostwriter](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html) — Python
- [Pynguin](https://pynguin.readthedocs.io/) — Python
- [EvoSuite](https://www.evosuite.org/) — Java
- [GraphWalker](https://graphwalker.github.io/) — Multi-language (model-based testing)
- [KLEE](https://klee-se.org/) — C/C++ (symbolic execution)

### Academic research cited
- *Augmented Coding* — Kent Beck (2025)
- *Spec-Driven Development* — Martin Fowler (2025)
- *Are Coding Agents Generating Over-Mocked Tests?* — arxiv 2602.00409 (2025)
- *Acceptance Test Generation with LLMs* — arxiv 2504.07244 (2025)
- *Agentic Property-Based Testing* — arxiv 2510.09907 (2025)
- *Multi-Agent Verification* — arxiv 2502.20379 (2025)

## Where to find what in this repository

```
spec-to-tests/
│
├── tdd-skill/                              ← steps 3-4
│   Hard rules to discipline the AI agent:
│   agent-discipline.md, plan-template.md, hooks-*.md,
│   scripts/tdd-verify-cycle.sh (proven RED→GREEN gate,
│   Python/Go/TS), driver-state-machine.md (FSM reference)
│
├── examples/pbt-sip/                       ← step 2 (article 5)
│   Hypothesis demo on a SIP parser and a dialog FSM.
│   Includes intentional bugs that PBT finds.
│
├── examples/billing-react-go/              ← step 6 (article 6)
│   Mini React + Go application with testcontainers,
│   MSW and Pact. The full workflow stack.
│
└── docs/workflow-overview.md               ← this document
```
