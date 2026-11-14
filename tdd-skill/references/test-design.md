# Test design — modes, seams, cases, RED/GREEN

> Conditional reference for `SKILL.md`. Read it when you are choosing what to
> test, where the seam is, or how to interpret a RED/GREEN result. It does not
> add a mandatory ceremony: select the mode and the depth by behavior and risk.

## 1. Choose the seam

Test the narrowest **public contract** that still expresses the behavior: a
module API, a seam between components, or a persistence contract. Tests coupled
to private helpers, call counts, or internal structure break on refactors that
change no behavior.

For a repository, "public" includes the observable persistence contract. A
targeted SQL assertion or a transaction/isolation check can be the right test
when the behavior *is* the database contract. Do not bypass a higher-level
contract merely to query the database, but do not reject SQL as a legitimate
contract either.

Reading production code is permitted at any point — to find the seam, understand
dependencies, or reproduce a bug. The restriction is on the **oracle**: the
expected value must not be copied from the implementation under test. Copying
the implementation into the assertion turns the test into a tautology.

## 2. Modes

### TDD (new behavior)

Write the smallest test that expresses the next behavior, run it, and observe a
failure for the claimed reason. Write the minimum coherent production change,
then refactor on green. Work in small vertical slices. A first-run green means
the behavior may already exist or the test is too weak: investigate.

### Bug regression

Reproduce the defect with a test that fails on the current baseline. The failure
must be the defect, not an unrelated setup error. Fix the cause, rerun the test,
and keep the regression test. If the test does not fail on the baseline, it does
not yet reproduce the defect.

### Characterization

When behavior is unknown, observe it and pin the observation before changing
anything. Characterization is allowed to pass on first run: the first useful
green is the point. It records what the system does; it does not assert that the
behavior is correct. If the observation looks wrong, separate the finding from
the test: report the suspected business bug instead of silently encoding a
correction as if it were current behavior.

### Refactoring

The suite must be green before you start. Refactor in small steps, stay green,
and broaden verification by risk. Do not change a test to make a refactor pass;
if a test must change, keep it separate and independently justify it (review
only if business behavior, scope or agreed risk requires it). A
behavior-preserving refactor does not add tests that encode the new internal
structure.

### Tests-only

Add or strengthen tests without changing production. Reading code is allowed;
the oracle still comes from the spec, examples, domain knowledge, or observed
behavior — not from copying the implementation. The first useful green can be
immediate. Do not add artificial production code just to manufacture a RED.

## 3. Choose discriminating cases

Pick cases that can distinguish correct from incorrect behavior:

- the canonical happy path;
- boundaries and edge values;
- error and absence paths;
- interactions and ordering where the risk lives;
- the regression that motivated the change;
- one case that would fail if the implementation silently returned a default.

Do not target a quota of functions, files, assertions or coverage lines. A few
sharp cases beat a broad, insensitive suite. Add a case when it changes what the
suite can detect, not to raise a count.

## 4. Interpreting RED

A failure is useful only when it is caused by the claim under test.

| Observation | Meaning |
|---|---|
| Assertion fails on the expected value | Good RED |
| Missing symbol / missing API / compile failure | Legitimate structural RED when the contract does not exist yet |
| Unrelated import, missing fixture, broken environment | Not RED; fix the setup and rerun |
| Test passes on first run | Investigate; in tests-only/characterization it may be the first useful green |
| Failure from a swallowed exception or fallback | Not a valid oracle; fix the test or the production error handling |

A structural RED is legitimate precisely because the public contract is absent.
Do not "fix" it by importing the implementation and copying its output.

## 5. Interpreting GREEN

GREEN means the smallest coherent change makes the claim true. It does not mean
the oracle is meaningful, the chronology was honest, or the business behavior is
correct. Those are separate questions, answered by test quality review,
independent evidence, and risk-based checks.

Technical corrections — typos, wiring, types, test setup — are autonomous. A
semantic correction (changing the expected behavior or the oracle) requires:

1. independent evidence (spec, domain rule, observed contract, reviewer);
2. a rerun that shows the new result;
3. a renewed RED against a safe baseline when a cycle is claimed.

If one of these is unavailable, report the gap explicitly. Never rewrite the
test merely because the implementation disagrees with it.

## 6. Real collaborators and doubles

Prefer a real collaborator when it is fast, deterministic and practical. This
keeps the test honest about wiring and contracts.

Use a double at an external boundary: network, third-party API, time,
randomness, or an unavailable/slow service. An internal double (a fake or stub
for code you control) is allowed only with a stated reason — for example, a slow
or non-deterministic dependency inside the module. It must never stand in for
the subject under test, and it must not hide the behavior the test claims to
verify.

A fake implemented in memory can be better than a mock: it keeps the contract
real enough to exercise the caller. Do not add a double just to make setup easy
if a fast real instance is available.

## 7. Reporting

Report the commands actually run, their scope (one test, package, module,
suite), their results, and what was not verified. Do not present a planned
command as executed. If the strict profile was not used, say so; if a semantic
change lacks independent evidence, name that limitation.

## 8. Strict profile (opt-in)

The optional `scripts/tdd-verify-cycle.sh` profile adds deterministic gates on
top of this doctrine. It is selected explicitly, never by default. Its honest
constraints:

- in a new-behavior cycle, test changes are additive — a new test file or a
  purely additive diff; deleting or rewriting existing test lines is rejected;
- refactor commits are GREEN-only and must not modify tests;
- the selected target must fail on the staged production baseline and pass once
  the change is restored (the baseline failure is mandatory on that target).

These gates prove ordering on the selected target. They do not prove that the
oracle is business-correct, that the chronology was not staged, or that the test
suite is strong. Use the core doctrine and, when risk justifies it, the advanced
checks instead of treating the script as a complete quality proof.
