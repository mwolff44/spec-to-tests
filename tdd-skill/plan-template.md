# plan.md — Optional Plan Artifact

The `plan.md` artifact is an optional, persistent list of the tests or behaviors
you intend to cover. It helps across sessions and agent restarts. It is **not**
required, and it does not impose a commit or approval cadence. Use it when the
change is large enough that a written plan reduces risk; skip it for a small
fix.

Inspired by Kent Beck's augmented-coding workflow (2025).

## Template

Copy the section below into a `plan.md` at the root of the feature branch or in
the module being worked on.

```markdown
# Plan — <feature or module name>

## Mode

<TDD | bug regression | characterization | refactoring | tests-only>

## Spec

<one-paragraph intention — the WHY>

## Examples

- Input X → Output Y (the canonical case)
- Edge: empty input → returns Z
- Edge: invalid input → raises E

## Non-goals

- <what this feature explicitly does NOT do>

## Seam / contract (proposed)

```
<public signature(s) or persistence contract — not private helpers>
```

## Cases (ordered by risk, not quota)

- [ ] C1 — happy path: <one-line behavior>
- [ ] C2 — empty input: <behavior>
- [ ] C3 — invalid input: <behavior>
- [ ] C4 — boundary: <behavior>
- [ ] C5 — regression: <behavior>

## Follow-ups (not for this session)

- <issue noticed in passing, do not fix now>

## Decisions

- <ADR-style line: chose X over Y because Z>
```

## Working with the agent

A reasonable loop for a TDD slice:

```
1. Read plan.md (if one exists).
2. Pick the next case by risk or dependency.
3. Write the test. Confirm RED for the right reason (or first useful green in
   tests-only/characterization).
4. Write minimal production code. Confirm GREEN.
5. Refactor if useful. Tests stay green.
6. Mark the case done in plan.md.
7. Report commands actually run, scope and results. Commit/review according to
   the repository's risk policy.
```

There is no mandatory stop after each case. Human checkpoints are by risk. The
agent does not autonomously chain risky changes; it does not need a ceremonial
pause after every trivial one either.

## Prompt to give the agent on session start

```
Read SKILL.md and agent-discipline.md before anything else. Your source of
truth is plan.md when one exists, otherwise the stated objective.

On "go":
  1. Pick the next case by risk.
  2. Write the test, run it, and report the actual failure reason
     (or the first useful green in tests-only/characterization).
  3. Write the minimum coherent production code, run it, report GREEN.
  4. Refactor only on an understood green.
  5. Mark the case done in plan.md.
  6. Report commands run, scope and limits. Commit/review per repo policy.

Rules from agent-discipline.md apply. If unsure, STOP and ask.
```

## Why a file can help

- Survives session crashes, context compaction and restarts.
- Reviewable as a file (diff, blame, PR comments).
- Multi-agent friendly: another agent can pick up the next case.
- Auditable: the plan is a record of intent, while the report records what was
  actually run.

## When plan.md is wrong

If the agent discovers mid-cycle that a planned case is impossible, redundant or
contradicts the spec: **STOP**. Surface the conflict, propose an update, and wait
for a decision when the risk warrants it. Do not silently skip or rewrite the
entry.
