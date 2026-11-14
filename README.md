# spec-to-tests

> Runnable companion material for the article series
> **["From Specification to Execution — a workflow for reliable code in the AI era"](https://www.blog-des-telecoms.com/blog/ia-tests-indispensables-workflow/)**
> on [blog-des-telecoms.com](https://blog-des-telecoms.com/).

The central idea of the series: in the age of AI agents capable of generating code in seconds, quality is no longer about writing code — it's about the **specification** upstream and the **tests** that guide the agent. This repository gathers demos, *skills*, and concrete examples to put this workflow into practice.

## Contents

```
spec-to-tests/
├── tdd-skill/                    Extended TDD skill for AI agents,
│                                 hardened to discipline them.
│                                 Fork of Matt Pocock's skill.
│                                 Core doctrine + optional strict profiles,
│                                 conditional references, and an eval protocol.
│
├── examples/
│   ├── pbt-sip/                  Property-based testing with Hypothesis
│   │                             on a SIP parser and a SIP dialog FSM.
│   │                             Demonstrates stateful PBT in a telecom context.
│   │
│   └── billing-react-go/         Full-stack demo — React + Go (Gin/GORM/PostgreSQL)
│                                 with Vitest+RTL+MSW, testcontainers-go,
│                                 and Pact contract testing (consumer/provider).
│
└── docs/
    └── workflow-overview.md      Workflow overview,
                                  referenced from the blog articles.
```

## Articles in the series

| # | Title | Link |
|---|---|---|
| 1 | AI didn't kill tests, it made them indispensable | [Article 1](https://www.blog-des-telecoms.com/blog/ia-tests-indispensables-workflow/) |
| 2 | Executable specification: what you give humans and AI to read | [Article 2](https://www.blog-des-telecoms.com/blog/specification-executable-gherkin-proprietes/) |
| 3 | Who writes the test, who writes the code? The human / AI / tools split | [Article 3](https://www.blog-des-telecoms.com/en/blog/who-writes-what-humans-ai-deterministic-tools/) |
| 4 | Measuring whether tests are worth something: the 4 axes | [Article 4](https://www.blog-des-telecoms.com/en/blog/measuring-test-quality-four-axes/) |
| 5 | Property-based testing: the defense against weak oracles | [Article 5](https://www.blog-des-telecoms.com/en/blog/property-based-testing-defense-weak-oracles/) |
| 6 | Putting it into practice: React + Go (Gin / GORM / PostgreSQL) | [coming soon] |
| 7 | Launching execution: from plan to PR | [coming soon] |

## Quick start

### 1. Property-based testing on SIP (Python)

```bash
cd examples/pbt-sip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v --hypothesis-show-statistics
```

Two suites:
- `test_sip_roundtrip.py` — round-trip property on a SIP parser.
- `test_dialog_stateful.py` — `RuleBasedStateMachine` on a SIP dialog FSM.

Both contain an intentional bug that Hypothesis finds in milliseconds. See the folder README for details and the fix exercise.

### 2. Billing React + Go with Pact (full-stack)

```bash
cd examples/billing-react-go
# Backend
cd api && go mod tidy && go test -race ./pricing/... ./handlers/...
cd ../frontend && pnpm install && pnpm test
# Contract testing
pnpm test:pact                       # consumer (generates the pact)
cd ../api && go test -tags=pact ./pacts/...   # provider (verifies the pact)
# Full E2E via Docker
cd .. && docker compose up --build
```

### 3. Using the TDD skill with an AI agent

```bash
cp -r tdd-skill <your-agent-skill-directory>/
# Invoke via a TDD mention or explicitly.
```

The skill provides:
- A compact core (`SKILL.md`) with mode-aware TDD, bug-regression,
  characterization, refactoring and tests-only workflows.
- An expanded `agent-discipline.md` with rules and rationale.
- Conditional references: `references/test-design.md` and
  `references/advanced-checks.md`.
- An optional `plan.md` artifact for larger changes.
- Optional, strict, opt-in guardrails: `scripts/tdd-verify-cycle.sh` proves
  RED→GREEN ordering on a selected target for Python/Go/TS; it does not prove
  the chronology or a business-correct oracle.
- Optional per-language hook templates and targeted mutation checks; no
  universal mutation threshold.
- An optional FSM reference (`driver-state-machine.md`) and an eval protocol
  (`evals/`) that has not been executed as an agentic benchmark.

## Attribution

The `tdd-skill/` folder is an **extended fork** of Matt Pocock's TDD skill — [`mattpocock/skills`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd). The additions (agent discipline, optional plan, optional per-language *hooks*, targeted mutation checks, eval protocol) are documented in `tdd-skill/README.md`. All of Pocock's original contributions are preserved and clearly credited; files whose content was revised are marked as adapted rather than kept as-is. The repository is MIT-licensed, and the upstream provenance is recorded in `tdd-skill/README.md`.

The `pbt-sip/` and `billing-react-go/` demos are original.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including commercially. Attribution appreciated.

## How to contribute

Issues and pull requests are welcome. A few open angles:

- Porting the demos to other stacks (Vue, Svelte, FastAPI, Spring Boot…).
- Adapting `tdd-skill/` to other agent environments (Cursor, Aider, OpenCode).
- Additional business use cases for stateful PBT (dialplan FSM, RTP state, etc.).
- Feedback on applying the workflow in production.

Before any substantial PR, please open an issue to discuss the approach.

## Author

**Mathias Wolff** — telecom architect at [Wazo](https://wazo.io), author of the [blog des télécoms](https://blog-des-telecoms.com).
[LinkedIn](https://www.linkedin.com/in/mathias-wolff-47a7941/) · [Celea Consulting](https://celea.org)

## Going further

- [Kent Beck — *Augmented Coding: Beyond the Vibes* (2025)](https://signals.aktagon.com/articles/2025/09/augmented-coding-beyond-the-vibes/)
- [Martin Fowler — *Exploring Gen AI: Spec-Driven Development* (2025)](https://martinfowler.com/tags/testing.html)
- [ThoughtWorks Technology Radar v33 (2025)](https://www.thoughtworks.com/radar)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- [Pact contract testing](https://docs.pact.io/)
