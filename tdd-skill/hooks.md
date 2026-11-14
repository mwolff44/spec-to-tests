# Hooks — Optional Guardrails (overview)

> The rules in `agent-discipline.md` are the doctrine. Hooks are **optional**
> deterministic aids that enforce a subset; they are not required, and they do
> not replace a meaningful oracle or a diff review.

This file is the language-agnostic index of six guardrail mechanisms. For
copy-paste-ready scripts and CI workflows, jump to your language file:

- [`hooks-python.md`](hooks-python.md) — pytest + mutmut + ruff
- [`hooks-typescript.md`](hooks-typescript.md) — vitest/jest + StrykerJS + ESLint
- [`hooks-go.md`](hooks-go.md) — go test + gremlins + golangci-lint

All three language files use the same numbering below. Same numbering is
intentional — "§2 RED gate" means the same thing regardless of stack.

## §0 — the optional strict profile (one script, all languages)

`scripts/tdd-verify-cycle.sh` folds §1 (test-diff guard) and §2 (RED gate) into a
single **opt-in** pre-commit for teams that want deterministic enforcement. One
script serves all three stacks via `TDD_LANG=python|go|ts` (files classified by
suffix, so colocated Go/React tests work).

The strict profile's honest constraints:

- **Additive test changes only** in a new-behavior cycle: a new test file, or a
  purely additive diff to an existing one. Deleting or rewriting existing test
  lines is rejected.
- **Refactor commits are GREEN-only** and do not modify tests.
- **The selected target must fail on the staged production baseline** and pass
  once the change is restored.
- It proves **ordering on that target**. It does not prove an honest chronology,
  a business-correct oracle, or a strong suite.

The six mechanisms below remain the à-la-carte reference. In particular §1 and
§2 describe the lightweight self-reported variant for setups that cannot run
tests inside the pre-commit. Do not describe the strict profile as the default.

## The six mechanisms

### §1. Detect test modification during a cycle

**Enforces** `agent-discipline.md §1` (do not edit tests to make code pass).

A marker file (`.tdd-cycle`) records which test file is the current one for a
new-behavior cycle. A pre-commit hook rejects modifications to any **other** test
file in the same commit. The agent declares the cycle at start and removes the
marker after the commit.

This is a diff check, not a file lock. It does not require making files
read-only, and it must not hide changes from `git diff`.

### §2. RED confirmation — default for TDD and bug-regression missing behavior only

**Enforces** `agent-discipline.md §2` (interpret a first-run green) and `§5`
(failure must be for the right reason).

A wrapper script runs the new test and inspects the output. Its default scope is
**TDD and bug-regression missing behavior only** — not characterization,
tests-only or refactoring.

- a **missing symbol/API or compile failure is a legitimate structural RED**
  when the contract does not exist yet;
- an **unrelated import, missing fixture or environment error is not RED** — fix
  the setup and rerun;
- a first-run green means **no RED** for that default. Inspect it: if the case is
  characterization or tests-only, reclassify and keep the useful coverage; never
  force production code or an expected value.

### §3. Review the test diff (no file locking)

**Belt-and-braces version of §1, without immutability.** Before the commit,
inspect `git diff` for the test files and confirm that changes are additive or
are an independently justified correction (review only for business ambiguity,
scope change or agreed risk).

Do **not** use `chmod a-w`, `git update-index --skip-worktree` or
`--assume-unchanged` as a lock: they hide or confuse the diff, can lose work,
and are not a security or integrity boundary. Keep the changes visible.

### §4. CI gate — targeted mutation testing

**Enforces** the spirit of ThoughtWorks Radar v33: catch "perpetually green"
tests by mutating production code and checking that the suite kills the mutants.

- Scope mutation to changed critical modules; full-suite runs are a scheduled
  choice, not a per-PR default.
- Choose thresholds **per module and risk**. There is no universal 70% rule.
- A survivor is investigated, not automatically a failure: real gap, equivalent
  mutant, or dead code.

### §5. Assertion density and forbidden patterns

**Enforces** `agent-discipline.md §3` (no swallowed failures) and the principle
that a test without an assertion is not a test.

Three layers:
- Native linter rules (ruff/eslint/golangci-lint) for cheap catches.
- Custom AST/regex scripts for the rest (empty test bodies, bare excepts,
  silent error swallowing, leftover `.only` / `t.Skip()`).
- CI grep guards as a safety net.

Assertion density is a warning signal, not a quota. A test can legitimately
verify a side effect through a helper or a fake.

### §6. Independent review by risk (optional)

**Supports** `agent-discipline.md` §7 and the risk-based review guidance.

When the change is security-sensitive, hard to reverse, semantically ambiguous,
or the author cannot establish the oracle independently, have another person or
agent review the claim, the oracle's provenance and the diff. This is
**risk-based**, not a mandatory role split for every cycle.

Do not encode harness-specific tool or permission fields in the skill. Use the
review mechanism your environment provides; the doctrine only requires that the
diff stays visible and the reviewer can inspect it.

## The minimum viable set

If you adopt only a few mechanisms:

1. **§1** — test-diff check (pre-commit or manual review).
2. **§2** — RED interpretation.
3. **§4** — targeted mutation on critical changed modules, when the cost is
   justified.

These address three documented AI-agent failure modes:

| Failure mode | Source | Defended by |
|---|---|---|
| Suppression / modification of tests | Beck 2025 | §1 |
| Unexplained first-run green | Martin (Three Laws) | §2 |
| Perpetually green tests | ThoughtWorks Radar v33 | §4 |

§5 (linter rules) is near-zero-cost and catches a meaningful share of agent
smells at lint time. §3 and §6 are situational.

## Implementation cost (rough)

| Language | Lines of config | CI minutes per PR (typical) |
|---|---|---|
| Python | ~150 | 5–15 (mutmut) |
| TypeScript | ~200 | 5–20 (Stryker, with incremental cache) |
| Go | ~150 | 5–25 (gremlins, depends on package count) |

CI cost is the main constraint. Mitigations in each language file:

- Scope mutation runs to changed files/packages only.
- Cache incremental state across runs.
- Reserve full-suite mutation for a scheduled run.
- Exclude generated code, vendor, migrations.
