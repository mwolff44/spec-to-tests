# Advanced checks — conditional, risk-based

> Conditional reference for `SKILL.md`. Use these checks when the risk or the
> stack calls for them. None is a universal gate, and none replaces a meaningful
> oracle.

## Properties

Property-based tests express a relation that must hold for a generated input
space: round-trip, invariant, idempotence, metamorphic relation, or a model-based
oracle. They are useful for parsers, codecs, numeric boundaries, routing tables,
state machines and protocol sequences.

Use them when the relation is derivable from the spec or domain knowledge. A
property copied from the implementation is as tautological as a copied example.
Keep strategies focused; prefer generating valid inputs over filtering heavily.
Do not add properties merely to increase test count.

## Contracts

Test the contract at a boundary when two components evolve independently:
consumer/provider contracts (for example Pact), or an OpenAPI/type contract.
Contract tests are worth their cost when the boundary is real and the failure
would otherwise appear only in integration. A contract is not a substitute for
behavior tests on either side.

## Targeted mutation

Mutation testing asks whether the suite detects a changed behavior. It is a
backstop for weak assertions, not a universal score to maximize.

- Scope it to changed critical modules, not the whole repository on every run.
- Choose thresholds per module and risk; there is no universal 70% rule.
- Investigate survivors: a real behavior gap calls for an assertion; an
  equivalent mutant is accepted with a note; dead code is removed.
- Treat the cost as a real trade-off: mutation runs are CPU-heavy, so cache,
  scope and schedule them deliberately.

A high mutation score does not prove the oracle is business-correct. It only
shows the suite reacts to the mutations that were generated.

## Flakiness

A flaky test is a defect in the test or in the system, not noise to retry away.
Prefer deterministic time, randomness, ordering and shared state. If a test is
genuinely non-deterministic, isolate the source and make the failure
reproducible. Do not add retries that hide the failure; if a quarantine is
unavoidable, record it with an owner and a removal condition.

## Independent review

Independent review is risk-based. Use it when the change is security-sensitive,
hard to reverse, semantically ambiguous, or when the author cannot establish the
oracle independently. It is not a mandatory role split for every cycle, and it
does not require a particular harness or permission model.

A reviewer should check: the claim, the oracle's provenance, the failure reason,
the scope of verification, and whether the test would survive a behavior-
preserving refactor. Reviewing the diff is expected; do not hide or rewrite
history to make a review easier.
