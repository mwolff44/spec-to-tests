# Agent Discipline — Rules and Rationale

> Expanded behavioral rules for AI agents. `SKILL.md` is the compact doctrine;
> this file explains the failure modes. The guardrails in `hooks.md` are
> **optional** and enforce only a subset — they are not the source of the rules.

Each rule has a **WHY** (the failure it prevents) and a **HOW** (how the agent
should behave). If a rule conflicts with apparent task progress, the rule wins.
A rule that is not marked non-negotiable can be relaxed with an explicit,
recorded reason — never silently.

## §1. Never modify or delete an existing test to make code pass

**WHY** — Confronted with a red test, agents tend to "fix" the test rather than
the code. The test is the contract; editing it to reach green destroys the
evidence.

**HOW**:
- **Additive** test changes are normal: new tests, new cases, stronger
  assertions. They do not need a special ceremony.
- If an existing test is independently shown to be wrong, correct it when the
  evidence justifies it — technical or semantic — separately from the production
  change that motivated it. A semantic correction needs evidence, a rerun and a
  renewed RED when a cycle is claimed; otherwise state the gap. Review only if
  the business behavior is ambiguous, scope changes, or an agreed risk requires
  it.
- Renaming, reordering or deleting assertions to make a failure disappear is
  forbidden. Do not hide test edits in a diff or rewrite history.
- There is no file-immutability requirement. Protect the *contract*, not the
  bytes of the file.
- The optional strict profile enforces additive-only diffs for new-behavior
  cycles; that is an opt-in team choice, not universal doctrine.

## §2. A first-run green needs interpretation

**WHY** — A test that passes without a code change can mean the behavior already
exists, the test asserts nothing meaningful, or the mode is characterization.
Continuing blindly produces "perpetually green" tests.

**HOW** — Interpret by mode:
- **TDD (new behavior)**: stop and investigate. Is the behavior already
  implemented? Is the assertion meaningful? Is a swallowed exception or default
  masking the failure?
- **Tests-only / characterization**: a first-run green can be the **first useful
  green**. Do not invent production code to manufacture a RED.
- **Bug regression**: the test must fail on the old baseline; a first-run green
  means it does not reproduce the defect yet.
- **Refactoring**: the suite is expected to be green already.

## §3. Never swallow failures in production code

**WHY** — A bare `try/except` or equivalent makes a red test go green by hiding
the error. The test passes; the bug ships.

**HOW**:
- No `except:` without a specific exception type and a comment on why the
  exception is expected.
- No empty `catch` blocks.
- No default fallback values that mask a missing implementation.
- If error handling is the behavior under test, it has its own test that asserts
  the error path.

## §4. Use doubles with a reason

**WHY** — Agents can over-mock by default, producing tests that pass but verify
nothing. The opposite failure — forbidding every internal double — also pushes
agents toward brittle, slow tests.

**HOW**:
- Prefer a **real collaborator** when it is fast, deterministic and practical.
- Boundary doubles are normal: external APIs, network, time, randomness, and an
  unavailable or impractical external service.
- An **internal double** (for code you control) is allowed with a stated reason,
  for example a slow or non-deterministic dependency. Prefer a small fake with a
  faithful contract over call-count mocking.
- **Never double the subject under test.** The behavior the test claims to
  verify must be real.
- If a real instance is hard to use, treat that as a design signal — but that is
  a signal, not an absolute prohibition on doubles.
- See [mocking.md](mocking.md) for the full guidance.

## §5. Verify the test fails for the right reason

**WHY** — A test can be RED because of a typo in the import, a syntax error or a
missing fixture. Writing code after that proves nothing.

**HOW**:
- After RED, read the failure. It must mention the assertion or the absent
  public contract you care about.
- A **missing symbol, missing API or compile failure is a legitimate structural
  RED** when the contract does not exist yet.
- An unrelated import, fixture or environment error is **not** RED. Fix the
  setup, rerun, and only then proceed.
- Do not count a failure you cannot attribute to the claim under test.

## §6. The oracle comes from the spec or observation, not from the code

**WHY** — If the agent reads the implementation to decide the expected value,
the test becomes a tautology: it asserts that the code does what the code does.

**HOW**:
- Reading production code is allowed — to find the seam, understand a
  dependency, or reproduce a bug.
- The expected value comes from the spec, a worked example, domain knowledge, a
  reference implementation, or characterization of observed behavior.
- Characterization records what the system does; it does not claim the behavior
  is business-correct.
- If the expected value cannot be determined without copying the implementation,
  stop and ask.
- Property-based testing is a useful defense: a relation is often derivable
  without a per-case oracle.

## §7. Cadence follows risk

**WHY** — Batching or forcing a commit/approval after every test does not fit
every repo. The useful invariant is traceability and honest verification, not a
universal rhythm.

**HOW**:
- Commit at a coherent point and follow the repository's review policy.
- Human checkpoints are by risk: security-sensitive, hard-to-reverse,
  semantically ambiguous, or large changes deserve earlier review.
- There is no universal one-test/one-commit rule and no mandatory approval per
  cycle.
- If the optional strict profile is selected, its commit mechanics apply to that
  profile only.
- Do not stage unrelated changes.

## §8. No speculative generalization

**WHY** — Agents tend to "future-proof" by adding parameters, options and
abstractions no test exercises. This adds untested surface and bloats the
interface.

**HOW**:
- Write the minimum code to satisfy the current claim.
- New parameters, options or flags only when a test requires them.
- Generalization is a refactor after green, driven by duplication or a new test,
  never speculative.

## §9. No comments explaining WHAT the code does

**WHY** — Agents generate verbose comments restating the code. These rot, mislead
and bloat; they do not explain why.

**HOW**:
- A comment is allowed only for a non-obvious why: a hidden constraint, a
  workaround, a counter-intuitive invariant, a performance trade-off.
- No docstring restating the function name and parameter types.
- Tests are the executable documentation of behavior.

## §10. If unsure, STOP and ask

**WHY** — Agents prefer to produce output rather than ask. The cost of asking is
low; the cost of silent drift is high.

**HOW**:
- Ambiguity in the spec → ask.
- A test seems wrong → ask (§1).
- A first-run green is unexplained → ask (§2).
- A double is needed but the boundary or reason is unclear → ask (§4).
- The oracle is unclear → ask (§6).
- "Asking" means: write the question, wait. Do not guess.

## Rule precedence

1. §1 (do not edit a test to make code pass) and §3 (do not swallow failures)
   are never broken.
2. §4 (doubles) is applied with a stated reason; it is not an absolute
   prohibition.
3. §10 (ask) always applies when in doubt.
4. Other rules can be relaxed with an explicit, recorded reason.

Independent review and role separation are **risk-based options**, not mandatory
roles. No particular harness, permission model or file-locking mechanism is
required by this doctrine.
