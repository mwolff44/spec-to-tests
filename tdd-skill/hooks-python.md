# Hooks — Python

Concrete, copy-paste-ready guardrails for Python projects using `pytest`.
Maps to the six mechanisms in `hooks.md`. Every mechanism is optional; the
strict profile is opt-in, not the default.

Assumptions:
- Test files live under `tests/` and are named `test_*.py`.
- Production code under `src/` (adjust paths as needed).
- `pytest` as test runner; `mutmut` for mutation testing.

## Setup options

| Option | When |
|---|---|
| **A. Plain git hooks** | Solo or quick start, no framework dependency. |
| **B. `pre-commit` framework** | Team workflow, shared config in repo. Recommended. |

### Option B — install once

```bash
pip install pre-commit
pre-commit install
```

Then drop the `.pre-commit-config.yaml` snippets shown below into the repo root.

---

## §0. Optional strict profile (opt-in)

`scripts/tdd-verify-cycle.sh` is **one language-agnostic script** (pick a preset
with `TDD_LANG=python|go|ts`, see [hooks-go.md](hooks-go.md) §0 /
[hooks-typescript.md](hooks-typescript.md) §0). It is an **explicitly selected
strict profile**, not the default doctrine. It replaces the *self-reported* pair
below (§1 marker guard + §2 `tdd-red.sh`) with a single pre-commit that proves
ordering on the selected target instead of trusting the agent's narration. It
folds three gates into one chokepoint (the commit):

- **A — cycle declaration is required within this profile.** Production code
  staged with no `.tdd-cycle` is rejected. This closes the escape hatch of §1
  (whose `[[ -f marker ]] || exit 0` meant "no marker ⇒ pass"): the default in
  this profile is *deny*, and an agent cannot bypass the guard by simply not
  declaring a cycle.
- **B — test-modification guard (§1).** In a cycle commit a test file may only
  *grow*: a new file, or a **purely additive** diff to an existing one, is fine
  (that is how you author the cycle's test). Deleting a test, or a diff that
  removes/changes existing lines in one, is rejected — that is the "alter a test
  to make code pass" violation. Distinguished at the diff level, so no need to
  know which file is "the cycle test" (works for colocated Go/React tests too).
- **C — RED→GREEN proof (§2, §5).** With the staged production code reverted to
  its HEAD state the cycle test *must fail*; with it restored the test *must
  pass*. The ordering is verified deterministically at commit time on that
  target; this does not prove the chronology was honest or that the oracle is
  business-correct. The old "wrong-reason" grep is dropped from RED (a
  missing-symbol `ImportError` is a legitimate Python structural RED); genuine
  wiring breakage persists into GREEN and is caught there instead — no false
  rejects on the normal Python flow.

It touches only the worktree copies of the staged src files (backed up and
restored byte-for-byte), so untracked files and unrelated unstaged edits are
never disturbed — no `git stash`, no pop-conflict, no data-loss hazard.

**Wire it:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tdd-verify-cycle
        name: TDD RED→GREEN proof (hardened)
        entry: tdd-skill/scripts/tdd-verify-cycle.sh
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

Or as a plain hook: `cp tdd-skill/scripts/tdd-verify-cycle.sh .git/hooks/pre-commit`.

**Agent workflow** (simpler than before — the RED proof is no longer the agent's
job to run):

```bash
echo 'tests/test_x.py::test_y' > .tdd-cycle   # declare the cycle test (node id)
# write the test, write the code
git add tests/test_x.py src/x.py
git commit -m 'test+feat: T1'                 # hook proves RED then GREEN
rm .tdd-cycle
# behavior-preserving change? declare a refactor commit instead:
echo 'refactor' > .tdd-cycle                  # GREEN-only: suite must stay green
```

**Config** (env): `TDD_LANG=python` (default) sets the file-classification
regexes and runner. Override any knob directly: `TDD_TEST_RE`, `TDD_SRC_RE`,
`TDD_RUN` (template for one selector, references `"$sel"`), `TDD_RUN_ALL`. The
Python preset classifies `test_*.py` / `*_test.py` / anything under `tests/` as
tests, everything else `*.py` as production, and runs `pytest "$sel"`.

`TDD_RUN` is trusted shell code supplied by the operator, never data taken from
the test name. The selector is passed as **one quoted argument** (for example
`-- "$sel"`); never interpolate it into `sh -c`, `eval` it, or re-parse it as
shell/JSON. Treat test names and paths as data.

**Limits.** `git commit --no-verify` bypasses it, like any pre-commit — the hard
backstop is the CI gate (§4/§5), unreachable by `--no-verify`. And an
import-driven RED can still hide an assertion-vacuous test (`assert True` next to
a real import): that residual "test theatre" is what mutation testing (§4) exists
to kill. This gate proves *ordering*, not *assertion quality*.

The two mechanisms below (§1, §2) remain documented as the lightweight,
self-reported variant — use them only if you cannot run tests in the pre-commit.

---

## §1. Detect test modification during a Green cycle

**Plain hook** — `.git/hooks/pre-commit` (chmod +x):

```bash
#!/usr/bin/env bash
set -euo pipefail

MARKER=".tdd-cycle"
[[ -f "$MARKER" ]] || exit 0

CURRENT_TEST="$(cat "$MARKER")"
CHANGED_TESTS=$(git diff --cached --name-only --diff-filter=AMD \
  | grep -E '(^|/)tests?/.*\.py$' || true)

for f in $CHANGED_TESTS; do
  if [[ "$f" != "$CURRENT_TEST" ]]; then
    echo "ERROR: test file '$f' modified outside the current cycle ($CURRENT_TEST)." >&2
    echo "Hint: agent-discipline.md §1 — never modify existing tests to make code pass." >&2
    exit 1
  fi
done
```

**pre-commit framework** — `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: tdd-cycle-guard
        name: TDD cycle guard (no test changes outside current cycle)
        entry: ./scripts/tdd-cycle-guard.sh
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

`scripts/tdd-cycle-guard.sh` = same body as the plain hook above.

**Agent workflow** at cycle start:

```bash
echo "tests/test_checkout.py" > .tdd-cycle   # declare the cycle's test
git add tests/test_checkout.py               # only the new failing test
# ... write code, run tests ...
git commit -m "test+feat: T1 happy path"     # passes the guard
rm .tdd-cycle                                # cycle done
```

---

## §2. RED confirmation — default for TDD and bug-regression missing behavior only

`scripts/tdd-red.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

TEST_ID="${1:?usage: tdd-red.sh <pytest node id>}"
LOG="$(mktemp)"

if pytest "$TEST_ID" --tb=short -q > "$LOG" 2>&1; then
  echo "NO RED: the test passed on first run. This wrapper is for TDD/bug-regression missing behavior only. If this is characterization or tests-only, keep the useful coverage and reclassify; refactoring does not use this wrapper. Never force production code or an expected value." >&2
  cat "$LOG" >&2
  exit 1
fi

# Reject unrelated infrastructure errors. A missing API (ImportError) can be a
# legitimate structural RED in Python; do not blanket-reject it.
if grep -E '(SyntaxError|fixture .* not found|collected 0 items)' "$LOG" > /dev/null; then
  echo "ERROR: test failed for the WRONG reason (infra). Fix the test, re-run." >&2
  cat "$LOG" >&2
  exit 1
fi

echo "RED confirmed for $TEST_ID."
touch .tdd-red
```

Usage in the agent loop:

```bash
./scripts/tdd-red.sh tests/test_checkout.py::test_happy_path
# TDD/bug-regression missing behavior only. If the test is already green,
# reclassify (characterization/tests-only) and keep the useful coverage.
[[ -f .tdd-red ]] && pytest -q && rm .tdd-red
```

---

## §3. Review the test diff (no file locking)

Before the commit, inspect the test diff:

```bash
git diff --cached -- tests/ src/
```

Confirm that test changes are additive or are an independently justified
correction (review only for business ambiguity, scope change or agreed risk). Do **not** use `chmod a-w`, `git update-index --assume-unchanged` or
`--skip-worktree` as a lock: those hide or confuse the diff, can lose work, and
are not an integrity boundary. Keep the diff visible.

---

## §4. CI gate — mutation testing on changed files

`.github/workflows/mutation.yml`:

```yaml
name: mutation
on:
  pull_request:
    branches: [main]
    paths: ['src/**/*.py', 'tests/**/*.py']

jobs:
  mutmut:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }

      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      - name: Install
        run: |
          pip install -e ".[dev]"
          pip install mutmut pytest pytest-xdist

      - name: Determine changed Python files under src/
        id: changed
        run: |
          FILES=$(git diff --name-only origin/main...HEAD -- 'src/**/*.py' | tr '\n' ',' | sed 's/,$//')
          echo "files=$FILES" >> "$GITHUB_OUTPUT"
          echo "Changed: $FILES"

      - name: Run mutmut
        if: steps.changed.outputs.files != ''
        env:
          CHANGED_FILES: ${{ steps.changed.outputs.files }}
        run: |
          # CHANGED_FILES is the comma-delimited single value produced above;
          # pass it as one quoted argument, never splice the expression here.
          mutmut run \
            --paths-to-mutate "$CHANGED_FILES" \
            --runner "pytest -x -q" \
            || true
          mutmut results
          mutmut junitxml > mutmut.xml || true

      - name: Enforce threshold
        if: steps.changed.outputs.files != ''
        env:
          MUTATION_THRESHOLD: "0.80"  # illustrative — choose per module and risk
        run: python scripts/check_mutation_score.py --threshold "$MUTATION_THRESHOLD"

      - uses: actions/upload-artifact@v4
        if: always() && steps.changed.outputs.files != ''
        with:
          name: mutmut-results
          path: |
            mutmut.xml
            .mutmut-cache
```

`scripts/check_mutation_score.py` (minimal):

```python
#!/usr/bin/env python3
import argparse, subprocess, sys, re

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=float, required=True,
                   help="per-module/risk threshold; there is no universal value")
    args = p.parse_args()

    out = subprocess.check_output(["mutmut", "results"], text=True)
    killed   = sum(1 for _ in re.finditer(r"^\s*\d+\s+killed",   out, re.M))
    survived = sum(1 for _ in re.finditer(r"^\s*\d+\s+survived", out, re.M))
    total = killed + survived
    if total == 0:
        print("No mutants — skipping.")
        return 0
    score = killed / total
    print(f"Mutation score: {score:.2%} ({killed}/{total})")
    if score < args.threshold:
        print(f"FAIL: below threshold {args.threshold:.0%}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Note: `mutmut` v3 has changed result-parsing semantics; pin a version in `requirements-dev.txt` and adjust the parser if needed.

---

## §5. Assertion density and forbidden patterns

`pyproject.toml`:

```toml
[tool.ruff.lint]
select = [
  "E", "F", "W",
  "PT",   # flake8-pytest-style
  "B",    # bugbear
  "ARG",  # unused arguments
  "S",    # bandit (security, but also flags except: pass)
]
ignore = ["S101"]  # assert ok in tests

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S", "ARG"]

[tool.pytest.ini_options]
addopts = "-ra --strict-markers --strict-config"
required_plugins = ["pytest-asyncio"]  # adjust per project
```

Install assertless-style checks via `flake8-pytest-style` (already in ruff `PT`).

CI `grep` guards (in `.github/workflows/lint.yml`):

```yaml
- name: Forbidden patterns
  run: |
    # Bare except in production
    if git grep -nE 'except\s*:\s*$' -- 'src/**/*.py'; then
      echo "Bare except: in src/ — agent-discipline.md §3"; exit 1
    fi
    # Empty test bodies
    if git grep -nE 'def test_\w+\([^)]*\):\s*(pass|\.\.\.)\s*$' -- 'tests/**/*.py'; then
      echo "Empty test body"; exit 1
    fi
    # Tests without any assertion or pytest.raises
    python scripts/check_assertion_density.py tests/
```

`scripts/check_assertion_density.py`:

```python
#!/usr/bin/env python3
"""Fail if any test function has zero assert/pytest.raises/expect."""
import ast, sys, pathlib

def check(path):
    tree = ast.parse(path.read_text())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            has = any(
                isinstance(n, ast.Assert) or (
                    isinstance(n, ast.With) and any(
                        getattr(item.context_expr, 'attr', '') == 'raises'
                        for item in n.items
                    )
                )
                for n in ast.walk(node)
            )
            if not has:
                bad.append(f"{path}:{node.lineno}:{node.name}")
    return bad

errors = []
for f in pathlib.Path(sys.argv[1]).rglob("test_*.py"):
    errors.extend(check(f))

if errors:
    print("Tests with no assertions:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
```

---

## §6. Independent review by risk (optional, advanced)

When the risk justifies it, have another person or agent review the claim, the
oracle's provenance and the diff. This is a **review process**, not a mandatory
role split and not a harness configuration. The skill intentionally contains no
tool or permission fields: use the review mechanism your environment provides,
and keep the diff visible so the reviewer can inspect it.

---

## Minimum viable Python setup (optional)

If you adopt only two optional mechanisms:

1. `scripts/tdd-verify-cycle.sh` as an **opt-in** pre-commit (§0) — folds §1 +
   §2 into a proven RED→GREEN gate on the selected target, with the additive and
   refactor constraints stated above.
2. `mutmut` GitHub Action on PRs (§4) — the assertion-quality backstop that a
   commit-time gate cannot provide, and the layer `--no-verify` cannot skip.

This covers the three documented AI-agent failure modes in TDD:

| Failure mode | Source | Defended by |
|---|---|---|
| Suppression / mod of tests | Beck 2025 | §0 gate B |
| Code without a failing test first | Martin (Three Laws) | §0 gate A + C |
| Perpetually-green / vacuous tests | ThoughtWorks Radar v33 | §0 gate C + §4 |

If you cannot run tests inside the pre-commit (too slow, no env), fall back to
the lightweight self-reported pair §1 + §2 plus §4.
