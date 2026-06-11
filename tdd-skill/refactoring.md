# Refactor Candidates

> Source: Matt Pocock, `mattpocock/skills`, base section kept as-is.
> Extended with the **Mutation testing** section (this fork).

After a TDD cycle, look for:

- **Duplication** → Extract function/class
- **Long methods** → Break into private helpers (keep tests on public interface)
- **Shallow modules** → Combine or deepen
- **Feature envy** → Move logic to where data lives
- **Primitive obsession** → Introduce value objects
- **Existing code** the new code reveals as problematic

Refactor only on green. Run tests after each step. Commit each refactor as a
separate commit when meaningful.

---

## Mutation testing (added in this fork)

After a feature is "tests-green", mutation testing is the second pass that
asks: **are the tests strong enough?**

Why this matters specifically with AI-generated code (ThoughtWorks Radar v33):
agents tend to produce tests that pass regardless of logic — missing assertions,
mocks decoupled from the code under test, vacuous truths. Mutation testing
mutates the production code (`==` → `!=`, `+` → `-`, off-by-one, removed
statements) and reports how many mutants the test suite **kills**. Survivors
are tests that should have failed but didn't.

### Tooling

| Language | Tool |
|---|---|
| Python | `mutmut`, `cosmic-ray` |
| TypeScript / JavaScript | `stryker-mutator` |
| Java / Kotlin | `pitest` |
| Rust | `cargo-mutants` |
| Go | `gremlins` |
| Ruby | `mutant` |
| C / C++ | `mull` |

### When to run it

- **Locally**: after a non-trivial feature cycle, before opening a PR.
- **CI**: scoped to changed files on PRs. Full-suite mutation runs nightly.
- **Module thresholds**: set a `low`/`break` mutation score per module
  (e.g. 80% on `auth/`, 60% on `ui/`). Match the criticality.

### Reading survivors

Each survivor is a question:

1. Is the mutation a real behavior change that no test asserts on?
   → write the missing assertion or the missing test.
2. Is it semantically equivalent (an `&&` that can be `&` because the operands
   are booleans, etc.)?
   → mark as equivalent / accepted, with a justifying comment.
3. Is the line dead code?
   → delete it.

The point is not to chase 100% mutation score — it's to surface **assertion
gaps** that an LLM-generated test suite tends to hide.

### Cost control

Mutation testing is CPU-heavy. To keep it tractable:

- Scope to **changed lines** in CI (`stryker --incremental`, `mutmut run --paths-to-mutate $(git diff ...)`).
- Cache results across runs.
- Run full suites nightly on the main branch, not per-PR.
- Exclude generated code, vendor, migrations.

See `hooks.md` §4 for a concrete CI workflow template.
