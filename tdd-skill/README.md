---
date: 2026-05-20
context: Extended fork of Matt Pocock's TDD skill to discipline AI agents
upstream-source: https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd
upstream-license: see repo mattpocock/skills
---

# tdd-skill (extended fork)

Fork of Matt Pocock's TDD skill, extended to explicitly address the AI-agent
pathologies in TDD documented in 2024-2026 (Beck, Fowler, ThoughtWorks Radar
v33, arxiv papers).

## Why this fork

The original skill is solid for a disciplined human but under-equipped against
the failure modes specific to AI agents:

| Agent pathology | Source | Handled by the original? | Handled here? |
|---|---|---|---|
| Horizontal slicing (all tests first) | Beck 2025 | Yes (excellent) | Kept |
| Over-mocking by default | arxiv 2602.00409 | Yes (mock at boundaries only) | Kept |
| Test through interface only | GOOS, Pocock | Yes | Kept |
| Deleting tests to make them pass | Beck 2025 (Pragmatic Engineer) | **No** | `agent-discipline.md` |
| Test must fail first (gate) | Martin, Three Laws | Partial | `agent-discipline.md` + `scripts/tdd-verify-cycle.sh` |
| Perpetually green / empty assertions | ThoughtWorks Radar v33 | No | `refactoring.md` + `hooks.md` (mutation testing) |
| Explicit human/AI split | Fowler 2025 | No | `SKILL.md` (Roles section) |
| Upstream executable spec | Fowler 2025 | Implicit | `SKILL.md` (Spec-first section) |
| Persistent plan.md | Beck 2025 (augmented coding) | No | `plan-template.md` |
| Hooks / file perms / CI gates | ThoughtWorks v33 | No | `hooks.md` |
| Per-cycle commit discipline | Beck 2025 | No | `SKILL.md` (extended workflow) |
| Oracle problem | arxiv 2602.07900 | No | `agent-discipline.md` |

## Files

```
tdd-skill/
├── README.md               ← this file
├── SKILL.md                ← main entry point (extended)
├── agent-discipline.md     ← NEW: hard anti-drift rules
├── plan-template.md        ← NEW: external artifact the agent follows
├── hooks.md                ← NEW: index of the guardrail mechanisms
├── hooks-python.md         ← NEW: copy-paste scripts for pytest + mutmut
├── hooks-typescript.md     ← NEW: copy-paste scripts for vitest/jest + Stryker
├── hooks-go.md             ← NEW: copy-paste scripts for go test + gremlins
├── scripts/
│   └── tdd-verify-cycle.sh ← NEW: hardened, language-agnostic RED→GREEN
│                              pre-commit that PROVES the cycle at commit time
├── driver-state-machine.md ← NEW: the loop as an explicit FSM
│                              (reference / autonomous blueprint)
├── tests.md                ← good vs bad tests (from Pocock)
├── mocking.md              ← mock at boundaries only (from Pocock)
├── interface-design.md     ← DI, side-effect-free (from Pocock)
├── deep-modules.md         ← Ousterhout (from Pocock)
└── refactoring.md          ← extended with mutation testing
```

## Attribution

"Philosophy", "Anti-Pattern: Horizontal Slices", "Tracer Bullet" sections,
`tests.md`, `mocking.md`, `interface-design.md`, `deep-modules.md`, and the base
of `refactoring.md`: Matt Pocock, repo `mattpocock/skills`.

Additions: see the table above.

## How to use

1. As a **Claude Code skill**: drop the folder into `~/.claude/skills/tdd-skill/`.
   The agent invokes it via a TDD mention or explicitly.
2. As **team doctrine**: read SKILL.md + agent-discipline.md before each AI
   session. Enable the hooks from `hooks.md` in CI, and the `scripts/tdd-verify-cycle.sh`
   pre-commit (§0) locally.
3. As a **personal reference**: read to frame a TDD session with Claude Code /
   Cursor / Aider.

## Acknowledged limitations

- The hooks in `hooks.md` are **templates**, to be adapted to the project
  (Python/TS/Go/Rust). `scripts/tdd-verify-cycle.sh` covers Python/Go/TS out of
  the box via `TDD_LANG`.
- The skill does not replace human code review on assertion quality: the
  commit-time gate proves the RED→GREEN *ordering*, not that assertions are
  meaningful — mutation testing is the backstop for that.
- Mutation testing has a non-trivial CI cost — enable it on critical modules
  first.
