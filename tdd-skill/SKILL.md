---
name: tdd
description: Use when the user requests test-first development, red-green-refactor, integration tests, or a bug fix built with TDD. Protect tests from deletion, over-mocking, and oracle drift.
---

# Test-Driven Development

> Fork of Matt Pocock's TDD skill, extended for AI agents. See `README.md` for
> provenance and the list of additions; the original philosophy and examples are
> credited there. This core is deliberately small; deeper material is in
> `references/`.

## What good looks like

Tests are useful when they pin behavior that matters and can fail for a real
reason. Keep them small and direct (KISS), and choose cases by behavior and
risk — never by a quota of functions, files or lines.

- Test a **public contract**: a seam, module boundary, or persistence contract.
  For a repository, the SQL/transactional behavior can be the contract.
- Prefer **real collaborators** when they are fast, deterministic and practical.
  Use doubles at external boundaries; an internal double needs a stated reason
  and must never stand in for the code under test.
- Reading production code is allowed. The **oracle** — the expected result —
  must come from the spec, an example, domain knowledge, or characterization of
  observed behavior; it must not be copied from the implementation under test.
- A test is not done because it is green. It is done when it would fail if the
  claimed behavior changed.

Avoid:
- horizontal slicing (all tests first, then all code);
- tests of private helpers or call counts;
- assertions that pass regardless of the behavior;
- a green run that no plausible defect could turn red.

## Choose the mode

| Mode | Use when | First useful green |
|---|---|---|
| **TDD** | New behavior, test can be written first | After minimal production code |
| **Bug regression** | A reported defect | After the fix; the test must fail on the old baseline |
| **Characterization** | Behavior is unknown and must be pinned before a change | Immediately, by observing current behavior |
| **Refactoring** | Behavior must not change | Already green before and after |
| **Tests-only** | Adding or strengthening coverage without changing production | Immediately, from existing behavior |

Characterization records what the system does; it does not decide whether that
behavior is correct business behavior. That correction is a separate change.

`references/test-design.md` is the conditional depth for seams, cases and
RED/GREEN interpretation. Advanced checks — properties, contracts, mutation,
flakiness, independent review — are also conditional: read
`references/advanced-checks.md` only when the risk or stack calls for them.

## Workflow

### 1. Frame the change

State the intent, a few concrete examples, non-goals and the main risks. Pick the
mode and the public seam. Identify discriminating cases: boundaries, error paths,
interactions, regressions, and the one case that distinguishes the new behavior
from the old. For TDD, work in small vertical slices — one behavior, its test,
its code — rather than batching imagined tests. Plan only as much as the risk
justifies; `plan-template.md` is optional, not a required artifact.

### 2. RED — make the claim observable

Write one focused test (or a small coherent set for characterization/tests-only)
and run it. Observe the failure output:

- It must fail for the reason you claim: the assertion, or an absent API.
- A missing API or compile error is a legitimate **structural RED** when the
  test calls a contract that does not exist yet.
- An unrelated import, fixture or environment error is not RED; fix it, then
  rerun.
- If the test passes on first run: in tests-only or characterization this can be
  the first useful green. Otherwise stop and investigate — the behavior may
  already exist, or the test may assert nothing real.

### 3. GREEN — the smallest coherent change

Write the minimum production change that makes the claim true without
speculative generalization.

- Technical corrections (typos, wiring, types) are autonomous. Semantic
  corrections are also allowed when independently justified; changing expected
  behavior or the oracle additionally needs evidence, a rerun, and a renewed RED
  against a safe baseline. If that evidence is unavailable, state the gap; do
  not claim a proven cycle. Review is for business ambiguity, scope change or an
  agreed risk — not an automatic revision gate.
- Do not add production code merely to make a test file look busy in tests-only
  or characterization mode.

### 4. Refactor — only on an understood green

Refactor when the suite is green and you can explain why. Do not refactor
production code while RED is unexplained. Keep the relevant tests green, then
broaden verification (package, module, suite) according to risk.
Behavior-preserving refactors do not change tests to force a result.

### 5. Report

Say what changed, the commands actually run, their scope and results, and what
was not verified. Do not present an intended command as executed.

## Hard rules

1. **Never modify or delete an existing test to make code pass.** Additive test
   changes are normal. Corrections are allowed when independently justified:
   technical fixes need no ceremony; a semantic correction needs evidence, a
   rerun, and a renewed RED when a cycle is claimed — otherwise state the gap.
   Do not edit an expectation just to match the code. Review is for business
   ambiguity, scope change or an agreed risk, not a default gate.
2. **A first-run green is a signal, not automatically a failure.** Interpret it
   by mode; investigate when it claims new behavior.
3. **Never swallow failures** to make a test pass.
4. **Doubles only with a reason.** Boundary doubles are normal; internal doubles
   need justification and never replace the subject under test.
5. **The oracle is not copied from the code under test.**
6. **If unsure, stop and ask** rather than guess.

Independent review is risk-based, not a mandatory role split. Commits and human
checkpoints follow the repository's risk policy; there is no universal
one-commit-per-cycle rule.

## Optional guardrails

`hooks.md`, the per-language hook templates, `driver-state-machine.md` and
`scripts/tdd-verify-cycle.sh` are **optional, strict profiles**. They are useful
when a team wants deterministic enforcement, but they are opt-in and are not the
default doctrine. The script proves ordering on the selected target; it does not
prove that the chronology was honest or that the oracle is business-correct.

## See also

- `references/test-design.md` — modes, seams, cases, RED/GREEN details.
- `references/advanced-checks.md` — properties, contracts, mutation, flakiness.
- `agent-discipline.md` — expanded rules and rationale.
- `tests.md` — good vs bad test examples (adapted from Pocock).
- `mocking.md` — real collaborators and boundary doubles (adapted from Pocock).
- `interface-design.md`, `deep-modules.md` — design for testability.
- `refactoring.md` — refactor candidates and targeted mutation.
- `plan-template.md` — optional plan artifact.
- `hooks.md`, `driver-state-machine.md` — optional strict guardrails.
