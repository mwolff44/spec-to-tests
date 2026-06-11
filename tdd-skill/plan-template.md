# plan.md — Template and Workflow

The `plan.md` artifact is the **persistent, ordered list of tests** the agent must
implement. It is the source of truth for "what comes next" across sessions and
across agent restarts. Inspired by Kent Beck's augmented-coding workflow (2025).

## Template

Copy the section below into a fresh `plan.md` at the root of the feature branch
or in the module being worked on.

```markdown
# Plan — <feature or module name>

## Spec

<one-paragraph intention — the WHY>

## Examples

- Input X → Output Y (the canonical case)
- Edge: empty input → returns Z
- Edge: invalid input → raises E

## Non-goals

- <what this feature explicitly does NOT do>

## Interface (proposed)

```
<signature(s) — function names, parameters, return types>
```

## Tests (ordered, one per cycle)

- [ ] T1 — happy path: <one-line behavior>
- [ ] T2 — empty input: <behavior>
- [ ] T3 — invalid input: <behavior>
- [ ] T4 — boundary: <behavior>
- [ ] T5 — error propagation: <behavior>

## Follow-ups (not for this session)

- <issue noticed in passing, do not fix now>

## Decisions

- <ADR-style line: chose X over Y because Z>
```

## Workflow with the agent

The agent's loop is:

```
1. Read plan.md.
2. Pick the first unchecked test in "Tests".
3. Write the test. Confirm RED (right reason).
4. Write minimal production code. Confirm GREEN.
5. Refactor if obvious. Tests stay green.
6. Mark the test [x] in plan.md.
7. Commit. Message format:
     test: T<n> <behavior>
     refs: plan.md
8. Stop. Wait for "go" before next cycle.
```

This explicit stop after each cycle is intentional — it creates the **human
checkpoint** that prevents drift. The agent does not autonomously chain cycles
unless the human says so.

## Prompt to give the agent on session start

```
You operate in strict TDD mode. Read SKILL.md and agent-discipline.md before
anything else. Your source of truth is plan.md.

On "go":
  1. Pick the next unchecked test in plan.md.
  2. Write the test, run it, confirm it fails for the right reason.
  3. Write minimal code, run it, confirm green.
  4. Propose ONE refactor at most. Wait for approval.
  5. Mark the test done in plan.md.
  6. Commit (one cycle = one commit).
  7. STOP. Wait for "go".

Hard rules from agent-discipline.md apply. If unsure, STOP and ask.
```

## Why plan.md is external (not in chat context)

- Survives session crashes, context compaction, restarts.
- Reviewable as a file (diff, blame, PR comments).
- Multi-agent friendly: any agent can pick up the next item.
- Auditable: at the end, the plan file is a record of what was actually done vs intended.

## Why ordered, not a backlog

Order matters in TDD. The next test should be the smallest behavior that adds
value given everything already implemented. A bag of unordered tests invites
horizontal slicing (see SKILL.md anti-pattern). The author of plan.md (human)
chooses the order; the agent does not reshuffle.

## When plan.md is wrong

If the agent discovers, mid-cycle, that a planned test is impossible, redundant,
or contradicts the spec: **STOP**. Surface the conflict, propose an update to
plan.md, wait for human approval. Do not silently skip or rewrite the entry.
