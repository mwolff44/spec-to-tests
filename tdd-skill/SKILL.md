---
name: tdd
description: Test-driven development with red-green-refactor loop, hardened for AI agents. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development. Enforces agent-discipline rules to prevent test deletion, over-mocking, perpetually-green tests, and oracle drift.
---

# Test-Driven Development (AI-hardened)

> Fork of Matt Pocock's tdd skill, extended with explicit agent-discipline rules,
> spec-first phase, role separation (human vs AI), plan.md artifact, mutation testing,
> and hook templates. See `README.md` for the full diff and rationale.

## Philosophy

**Core principle**: Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests** are integration-style: they exercise real code paths through public APIs. They describe _what_ the system does, not _how_. A good test reads like a specification — `"user can checkout with valid cart"` tells you exactly what capability exists. These tests survive refactors because they don't care about internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or verify through external means (querying a DB directly instead of using the interface). Warning sign: a test breaks when you refactor but behavior hasn't changed.

See [tests.md](tests.md) for examples, [mocking.md](mocking.md) for mocking guidelines, and **[agent-discipline.md](agent-discipline.md) for the hard rules that prevent agent drift**.

## Roles (human vs AI) — read this first

This skill is designed for AI agent collaboration. Roles are NOT symmetric:

| Step | Authoring | Validation |
|---|---|---|
| Spec / intention | Human | Human |
| Test (RED) | Human (or AI proposes, human approves) | Human approves before Green |
| Production code (GREEN) | AI | Tests + CI + mutation score |
| Refactor | AI proposes, human approves | Tests stay green |

**Anti-pattern**: letting the same AI agent author both the test and the code for the same behavior in the same unsupervised loop. This is the fast path to "I made the test pass by changing the test."

If the human cannot author every test, at minimum: the AI must write tests **before** seeing or producing any implementation, and the human reviews them as a blocking gate before Green.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This is horizontal slicing — treating RED as "write all tests" and GREEN as "write all code." It produces **crap tests**:

- Tests written in bulk test _imagined_ behavior, not _actual_ behavior.
- You test the _shape_ of things (data structures, function signatures) rather than user-facing behavior.
- Tests become insensitive to real changes — they pass when behavior breaks and fail when behavior is fine.
- You outrun your headlights, committing to test structure before understanding the implementation.

**Correct approach**: Vertical slices via tracer bullets. One test → one implementation → repeat.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  ...
```

## Workflow

### 0. Spec-first (NEW)

Before any test, produce a minimal executable spec:

- [ ] One-paragraph intention in plain language (the WHY).
- [ ] 2–5 concrete examples of inputs/outputs or scenarios (the WHAT).
- [ ] Explicit non-goals (the NOT WHAT).
- [ ] Constraints: performance, error handling, security, side effects.
- [ ] Domain glossary terms used (match the project's vocabulary; respect ADRs).

This is the contract. Tests are derived from it. If the agent later proposes behavior outside this spec, that is drift — reject it.

### 1. Planning

- [ ] Confirm with user what interface changes are needed.
- [ ] Confirm with user which behaviors to test (prioritize).
- [ ] Identify opportunities for [deep modules](deep-modules.md) (small interface, deep implementation).
- [ ] Design interfaces for [testability](interface-design.md).
- [ ] **Create or update [`plan.md`](plan-template.md)** with the ordered list of tests. This is the artifact the agent follows.
- [ ] Get user approval on the plan.

**You can't test everything.** Confirm with the user exactly which behaviors matter. Focus on critical paths and complex logic.

### 2. Tracer bullet (first cycle)

Write ONE test that confirms ONE thing about the system:

```
RED:   write test for first behavior → run → VERIFY IT FAILS
GREEN: write minimal code to pass → run → VERIFY IT PASSES
```

The "verify it fails" step is a **gate**, not a comment. If the test passes on first run, **STOP**. Either the behavior already exists or the test does not test what it claims. See [agent-discipline.md](agent-discipline.md) §2.

### 3. Incremental loop

For each remaining behavior:

```
[ ] Pick next unchecked test from plan.md
[ ] Write the test
[ ] Run → confirm RED (test fails for the right reason)
[ ] Write minimal code
[ ] Run → confirm GREEN
[ ] Mark test done in plan.md
[ ] Commit (one Green = one commit, message links to plan.md item)
```

Rules:

- One test at a time.
- Only enough code to pass the current test.
- Don't anticipate future tests (no speculative generalization).
- Keep tests focused on observable behavior.
- **Never modify or delete an existing test to make code pass.** See [agent-discipline.md](agent-discipline.md) §1.

### 4. Refactor

After Green, look for [refactor candidates](refactoring.md):

- [ ] Extract duplication.
- [ ] Deepen modules (move complexity behind simple interfaces).
- [ ] Apply SOLID principles where natural.
- [ ] Consider what new code reveals about existing code.
- [ ] Run tests after each refactor step.
- [ ] **If mutation testing is enabled, check the mutation score did not regress.**

**Never refactor while RED.** Get to GREEN first.

### 5. Mutation gate (NEW, before merge)

On the modules touched in this session, run mutation testing (Stryker / mutmut / pitest / cargo-mutants). See [refactoring.md](refactoring.md) §Mutation testing.

- [ ] Mutation score ≥ project threshold (default 70%).
- [ ] No surviving mutants in the changed lines that represent real behavior loss.
- [ ] Any accepted survivor documented.

## Checklist per cycle (extended)

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive an internal refactor
[ ] Test actually contains assertions on the behavior under test
[ ] Test failed before the production code was written (RED confirmed)
[ ] Test passes for the right reason (not via swallowed exception or mocked return)
[ ] No existing test was modified or deleted during this cycle
[ ] Code is minimal for this test (no speculative features)
[ ] Mock usage justified (system boundary, see mocking.md)
[ ] Plan.md item marked done
[ ] One commit per Green+Refactor cycle
```

## Hard rules (non-negotiable)

These are encoded in [agent-discipline.md](agent-discipline.md) and ideally enforced by [hooks](hooks.md):

1. Never modify or delete an existing test to make new code pass.
2. If a test passes on first run, STOP — investigate, do not continue.
3. Never use `try/except` (or equivalent) to swallow failures in production code.
4. Never introduce mocks for code you control.
5. If a test seems wrong, STOP and ask the human — do not "fix" it.
6. One test at a time. One commit per cycle.

## See also

- [agent-discipline.md](agent-discipline.md) — hard rules and rationale.
- [plan-template.md](plan-template.md) — the artifact the agent follows.
- [hooks.md](hooks.md) — executable guardrails.
- [tests.md](tests.md) — good vs bad test examples.
- [mocking.md](mocking.md) — when (and only when) to mock.
- [interface-design.md](interface-design.md) — designing for testability.
- [deep-modules.md](deep-modules.md) — Ousterhout's principle.
- [refactoring.md](refactoring.md) — refactor candidates + mutation testing.
