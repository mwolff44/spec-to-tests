---
date: 2026-05-20
context: Extended fork of Matt Pocock's TDD skill to discipline AI agents
upstream-source: https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd
upstream-license: see repo mattpocock/skills
---

# tdd-skill (extended fork)

Fork of Matt Pocock's TDD skill, extended to address the AI-agent pathologies in
TDD documented in 2024-2026 (Beck, Fowler, ThoughtWorks Radar v33, arxiv
papers). The default doctrine is deliberately small; deterministic guardrails
are optional strict profiles.

## Why this fork

The original skill is solid for a disciplined human but under-equipped against
the failure modes specific to AI agents:

| Agent pathology | Source | Handled by the original? | Handled here? |
|---|---|---|---|
| Horizontal slicing (all tests first) | Beck 2025 | Yes (excellent) | Kept |
| Over-mocking by default | arxiv 2602.00409 | Yes (mock at boundaries only) | Reconciled: real collaborators first; internal doubles justified |
| Test through interface only | GOOS, Pocock | Yes | Kept |
| Deleting tests to make them pass | Beck 2025 (Pragmatic Engineer) | **No** | `agent-discipline.md` §1 |
| Test must fail first (gate) | Martin, Three Laws | Partial | Mode-aware RED in `SKILL.md`; optional strict gate |
| Perpetually green / empty assertions | ThoughtWorks Radar v33 | No | `refactoring.md` + optional mutation checks |
| Explicit human/AI split | Fowler 2025 | No | Risk-based review, not mandatory roles |
| Upstream executable spec | Fowler 2025 | Implicit | `SKILL.md` (frame the change) |
| Persistent plan.md | Beck 2025 (augmented coding) | No | Optional `plan-template.md` |
| Hooks / file perms / CI gates | ThoughtWorks v33 | No | Optional `hooks.md`; no harness permission fields |
| Oracle problem | arxiv 2602.07900 | No | `agent-discipline.md` §6 |

## Files

```
tdd-skill/
├── README.md               ← this file
├── SKILL.md                ← main entry point (core doctrine)
├── references/
│   ├── test-design.md      ← modes, seams, cases, RED/GREEN (conditional)
│   └── advanced-checks.md  ← properties, contracts, mutation, flakiness
├── evals/
│   ├── README.md           ← comparison protocol (not executed)
│   └── cases.json          ← eight activation/near-miss/scenario cases
├── agent-discipline.md     ← expanded rules and rationale
├── plan-template.md        ← optional plan artifact
├── hooks.md                ← optional guardrail mechanisms index
├── hooks-python.md         ← optional strict-profile scripts (pytest + mutmut)
├── hooks-typescript.md     ← optional strict-profile scripts (vitest/jest + Stryker)
├── hooks-go.md             ← optional strict-profile scripts (go test + gremlins)
├── scripts/
│   └── tdd-verify-cycle.sh ← optional strict opt-in RED→GREEN commit gate
├── tests/
│   └── test_tdd_verify_cycle.py ← hermetic script tests (separate from doctrine)
│                                 run: python3 -m unittest discover \
│                                 -s tdd-skill/tests -p 'test_*.py' -v
├── driver-state-machine.md ← optional FSM reference / autonomous blueprint
├── tests.md                ← good vs bad tests (adapted from Pocock)
├── mocking.md              ← doubles at boundaries (adapted from Pocock)
├── interface-design.md     ← DI, side-effect-free (from Pocock)
├── deep-modules.md         ← Ousterhout (from Pocock)
└── refactoring.md          ← extended with targeted mutation testing
```

## Attribution

"Philosophy", "Anti-Pattern: Horizontal Slices", "Tracer Bullet" sections,
`tests.md`, `mocking.md`, `interface-design.md`, `deep-modules.md`, and the base
of `refactoring.md`: Matt Pocock, repo `mattpocock/skills`.

Additions: see the table above. The `tests.md`, `mocking.md` and
`refactoring.md` files are marked as adapted where this fork changed their
content; the original MIT-licensed material remains credited and preserved in
spirit. The repository `LICENSE` covers the fork.

## How to use

1. As an **agent skill**: drop the folder into your agent's skill directory.
   The agent invokes it via a TDD mention or explicitly.
2. As **team doctrine**: read `SKILL.md` and `agent-discipline.md` before an AI
   session. Add the optional guardrails from `hooks.md` only when the team wants
   deterministic enforcement.
3. As a **personal reference**: read it to frame a TDD session with any agent.

## The strict profile is opt-in

`scripts/tdd-verify-cycle.sh` and the language templates implement a **strict
profile**. Select it explicitly. Its honest constraints:

- New-behavior cycles accept additive test changes only.
- Refactor commits are GREEN-only and do not modify tests.
- The selected target must fail on the staged production baseline and pass once
  the change is restored.
- It proves ordering on that target. It does **not** prove an honest chronology,
  a business-correct oracle, or a strong suite.
- It is not required for ordinary TDD and is not selected by default.

## Acknowledged limitations

- The hooks are **templates** to adapt to the project. They are optional.
- The skill does not replace human review of assertion quality: the commit-time
  gate proves ordering, not meaning. Mutation testing is a targeted backstop.
- Mutation testing has a non-trivial cost; scope it to critical modules and
  choose thresholds by risk, with no universal percentage.
- The evaluation in `evals/` is a protocol, not an executed benchmark.
