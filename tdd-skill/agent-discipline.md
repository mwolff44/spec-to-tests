# Agent Discipline — Hard Rules

> These rules exist because AI agents have documented failure modes under TDD that
> humans rarely exhibit. Sources: Beck (Pragmatic Engineer 2025), arxiv 2602.00409
> (over-mocked tests), arxiv 2602.07900 (incorrect oracles), ThoughtWorks Radar v33.
>
> Each rule has a **WHY** (the failure mode it prevents) and a **HOW** (how the
> agent must behave). If a rule conflicts with apparent task progress, the rule wins.

## §1. Never modify or delete an existing test to make code pass

**WHY** — Documented pattern: confronted with a red test, agents tend to "fix" the test rather than the code. The test is the spec; modifying it silently destroys the contract.

**HOW**:
- If the test seems wrong: **STOP**. Surface the suspicion to the human with concrete reasoning. Wait for explicit approval before any test change.
- Allowed test changes during Green: **none**.
- Allowed test changes outside Green: only when the spec itself is being revised, and the change is reviewed independently of the production code change.
- Renaming a test, reordering its assertions, "clarifying" its setup mid-cycle: not allowed.

**Enforcement** — Ideally a pre-commit hook (see `hooks.md`) detecting modifications to test files during a cycle, or read-only test files between RED and Green.

## §2. If a test passes on first run, STOP

**WHY** — A test that goes green without any code change either (a) tests behavior that already exists (and the cycle is moot), or (b) tests nothing meaningful (assertion vide, oracle dégénéré). Continuing produces "perpetually green" tests — the failure mode ThoughtWorks Radar v33 flags as critical.

**HOW**:
- After writing a test, run it. Expect RED.
- If GREEN: do not write production code. Investigate:
  - Is the behavior already implemented? Then this test duplicates coverage — discard or replace.
  - Is the assertion meaningful? Does it actually exercise the claimed behavior?
  - Is there a swallowed exception or default value masking the failure?
- Only resume the cycle when the test fails for the right reason.

## §3. Never swallow failures in production code

**WHY** — A bare `try/except` or equivalent makes a red test go green by hiding the error. The test passes; the bug ships.

**HOW**:
- No `except:` without a specific exception type and a comment on WHY this exception is expected.
- No `catch (e) {}` empty blocks.
- No default fallback values that mask a missing implementation.
- If error handling is the behavior under test, it has its own test that asserts the error path.

## §4. Never mock code you control

**WHY** — Empirical study (arxiv 2602.00409): agents over-mock by default because it's the path of least resistance. The resulting tests pass but verify nothing real (test theatre).

**HOW**:
- Mock only at **system boundaries**: external APIs, network, time, randomness, the file system (sometimes), the database (prefer a real test DB or testcontainers).
- For internal collaborators: use real instances.
- If a real instance is hard to use in a test, that is a **design signal** — fix the coupling rather than mocking.
- See [mocking.md](mocking.md) for the full guidance.

## §5. Verify the test fails for the right reason

**WHY** — A test can be RED for the wrong reason (typo in the import, syntax error, wrong fixture). If you then write code and it goes GREEN, you have proven nothing. Documented in *Rethinking the Value of Agent-Generated Tests* (arxiv 2602.07900).

**HOW**:
- After RED, read the failure message. It must mention the assertion you care about, not an unrelated error.
- If the failure is "module not found" or "fixture missing", fix the test infrastructure first, re-confirm RED, then proceed.

## §6. The test's oracle must be derivable from the spec, not the code

**WHY** — If the agent reads the implementation to figure out "what should the expected value be?", the test becomes a tautology — it asserts that the code does what the code does. This is the oracle problem in LLM-generated tests.

**HOW**:
- The expected value comes from the spec (see SKILL.md §0), from a worked example, from a reference implementation, or from domain knowledge.
- If the agent cannot determine the expected value without reading the implementation under test, STOP and ask.
- Property-based testing (Hypothesis, fast-check, proptest) is a good defense: properties are derivable without an oracle per case.

## §7. One test, one cycle, one commit

**WHY** — Batching cycles loses traceability. If something breaks three behaviors later, bisecting is painful. Beck's augmented-coding workflow commits after each Green-then-Refactor.

**HOW**:
- After Green and any refactor, commit. Conventional commit message referencing the plan.md item: `test: <behavior>` or `feat: <behavior>` with a body linking to the plan.
- Do not stage unrelated changes.
- If a refactor reveals an unrelated issue, note it in `plan.md` under a "follow-ups" section. Do not fix it in this cycle.

## §8. No speculative generalization

**WHY** — Agents tend to "future-proof" by adding parameters, options, abstractions not exercised by any test. This adds untested surface and bloats the interface.

**HOW**:
- The Three Laws of TDD (Martin): write the minimum test to fail, write the minimum code to pass.
- New parameters, options, flags: only if a test requires them.
- Generalization is a **refactor**, after Green, driven by duplication or a new test, never speculative.

## §9. No comments explaining WHAT the code does

**WHY** — Agents generate verbose explanatory comments restating the code. These rot, mislead, and bloat. They do not explain WHY.

**HOW**:
- A comment is allowed only when it explains a non-obvious WHY: a hidden constraint, a workaround, a counter-intuitive invariant, a perf trade-off.
- No docstring restating function name and parameter types.
- Tests are the executable documentation of behavior.

## §10. If unsure, STOP and ask

**WHY** — Agents prefer to produce output rather than ask. This produces plausible drift. The cost of asking is low; the cost of silent drift is high.

**HOW**:
- Ambiguity in the spec → ask.
- Test seems wrong → ask (§1).
- Test passes on first run → ask (§2).
- Mocking required but boundary unclear → ask (§4).
- Oracle unclear → ask (§6).
- "Asking" means: write the question, wait. Do not guess.

## Rule precedence

If rules conflict, the precedence is:

1. §1 (don't touch the test) — never broken.
2. §3 (don't swallow failures) — never broken.
3. §4 (don't mock what you control) — broken only with explicit human approval and a comment.
4. §10 (ask) — when in doubt, this always applies.

The other rules can be relaxed with **explicit, logged** human approval per occurrence. Document the deviation in the commit message or plan.md.
