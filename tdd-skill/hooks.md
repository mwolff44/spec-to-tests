# Hooks — Executable Guardrails (overview)

> Rules in `agent-discipline.md` are doctrinal. Hooks make a subset of them
> enforceable. The principle from ThoughtWorks Radar v33: **deterministic
> quality gates integrated into the agent loop**, so failures trigger
> auto-correction before human review.

This file is the **language-agnostic index** of the six guardrail mechanisms.
For copy-paste-ready scripts and CI workflows, jump to your language file:

- [`hooks-python.md`](hooks-python.md) — pytest + mutmut + ruff
- [`hooks-typescript.md`](hooks-typescript.md) — vitest/jest + StrykerJS + ESLint
- [`hooks-go.md`](hooks-go.md) — go test + gremlins + golangci-lint

All three language files implement the same six mechanisms below, with
identical numbering. Same numbering is intentional — when you say "§2 RED gate"
in conversation, it means the same thing regardless of stack.

## The six mechanisms

### §1. Detect test modification during a Green cycle

**Enforces** `agent-discipline.md §1` (never modify tests to pass).

A marker file (`.tdd-cycle`) records which test file is the current one.
A pre-commit hook rejects modifications to any **other** test file in the same
commit. Agent declares the cycle at start, removes the marker after a clean
Green commit.

### §2. RED must fail first (and for the right reason)

**Enforces** `agent-discipline.md §2` (if a test passes on first run, STOP)
and `§5` (failure must be for the right reason — not an import error).

A wrapper script around the test runner runs the new test, inspects the output,
and creates a `.tdd-red` marker only when the test failed for an assertion
reason. The Green step requires `.tdd-red` to exist.

### §3. Lock test files between RED and Green

**Belt-and-braces version of §1.** During an unsupervised agent run, test files
become read-only between RED confirmation and Green commit. Two approaches:

- `chmod a-w` then `chmod u+w` — simplest.
- `git update-index --skip-worktree` — harder for the agent to undo without
  surfacing the action.

### §4. CI gate — mutation testing on changed files

**Enforces** the spirit of ThoughtWorks Radar v33: catch "perpetually green"
tests by mutating production code and checking that the test suite kills the
mutants. Scoped to changed files/packages in PRs; full-suite runs nightly.

Thresholds typical: 70% mutation score on critical modules, 60% on others.

### §5. Assertion density and forbidden patterns

**Enforces** `agent-discipline.md §3` (no swallowed failures) and the implicit
rule that a test without assertions is not a test.

Three layers:
- Native linter rules (ruff/eslint/golangci-lint) for the cheap catches.
- Custom AST/regex scripts for the rest (empty test bodies, bare excepts,
  silent error swallowing, leftover `.only` / `t.Skip()`).
- CI grep guards as a safety net.

### §6. Agent role split (optional, advanced)

**Enforces** `SKILL.md §Roles` (test author ≠ code author).

Two agent sessions with restricted Claude Code tool permissions:

- Test session: write/read test files, read production headers only.
- Implementer session: write/read production files, tests as read-only text.

Useful when running a long unsupervised loop. Overkill for supervised work.

## The minimum viable set (3 mechanisms)

If you adopt only three:

1. **§1** — test modification guard (pre-commit, ~30 lines bash).
2. **§2** — RED gate wrapper script (manual invocation, ~20 lines bash).
3. **§4** — mutation testing in CI on changed files only.

These cover the three documented AI-agent failure modes in TDD:

| Failure mode | Source | Defended by |
|---|---|---|
| Suppression / mod of tests | Beck 2025 | §1 |
| Test passes on first run | Martin (Three Laws) | §2 |
| Perpetually green tests | ThoughtWorks Radar v33 | §4 |

§5 (linter rules) is near-zero-cost and catches a meaningful share of agent
smells at lint time, before mutation testing ever runs — strongly recommended
even on top of the minimum set.

§3 and §6 are situational: useful for long unsupervised agent runs, optional
for supervised work.

## Implementation cost (rough)

| Language | Lines of config | CI minutes per PR (typical) |
|---|---|---|
| Python | ~150 | 5–15 (mutmut) |
| TypeScript | ~200 | 5–20 (Stryker, with incremental cache) |
| Go | ~150 | 5–25 (gremlins, depends on package count) |

CI cost is the main constraint. Mitigations in each language file:

- Scope mutation runs to changed files/packages only.
- Cache incremental state across runs.
- Reserve full-suite mutation for nightly on `main`.
- Exclude generated code, vendor, migrations.
