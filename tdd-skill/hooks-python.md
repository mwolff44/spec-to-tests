# Hooks — Python

Concrete, copy-paste-ready guardrails for Python projects using `pytest`.
Maps to the four mechanisms in `hooks.md`.

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

## §2. RED must fail first (and for the right reason)

`scripts/tdd-red.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

TEST_ID="${1:?usage: tdd-red.sh <pytest node id>}"
LOG="$(mktemp)"

if pytest "$TEST_ID" --tb=short -q > "$LOG" 2>&1; then
  echo "ERROR: test passed on first run — discipline §2. STOP and investigate." >&2
  cat "$LOG" >&2
  exit 1
fi

# Reject infrastructure errors masquerading as RED.
if grep -E '(ModuleNotFoundError|ImportError|SyntaxError|fixture .* not found|collected 0 items)' "$LOG" > /dev/null; then
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
# only proceed to write production code if .tdd-red exists
[[ -f .tdd-red ]] && pytest -q && rm .tdd-red
```

---

## §3. Lock test files between RED and Green

```bash
# entering Green phase
chmod a-w tests/test_checkout.py

# after Green commit
chmod u+w tests/test_checkout.py
```

For a stronger lock that survives chmod tampering, use git's index assume:

```bash
git update-index --assume-unchanged tests/test_checkout.py   # before Green
git update-index --no-assume-unchanged tests/test_checkout.py # after
```

(Caveat: `--assume-unchanged` is a local optimization, not a lock. Combine with §1 hook.)

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
        run: |
          mutmut run \
            --paths-to-mutate "${{ steps.changed.outputs.files }}" \
            --runner "pytest -x -q" \
            || true
          mutmut results
          mutmut junitxml > mutmut.xml || true

      - name: Enforce threshold
        if: steps.changed.outputs.files != ''
        run: python scripts/check_mutation_score.py --threshold 0.70

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
    p.add_argument("--threshold", type=float, default=0.70)
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

## §6. Agent role split (optional, advanced)

In Claude Code `settings.json`, scope tool permissions per session:

```json
{
  "permissions": {
    "tools": {
      "Edit":  { "paths": ["tests/**/*.py"] },
      "Write": { "paths": ["tests/**/*.py"] },
      "Read":  { "paths": ["src/**/*.py", "tests/**/*.py"] }
    }
  }
}
```

This restricts the "test author" session to test files. The "implementer"
session uses the inverse (write to `src/` only, read tests as text).

---

## Minimum viable Python setup (3 things)

If you adopt only three:

1. `pre-commit` with `tdd-cycle-guard.sh` (§1).
2. `scripts/tdd-red.sh` invoked manually before each Green (§2).
3. `mutmut` GitHub Action on PRs (§4).

This covers the three documented AI-agent failure modes in TDD with under
150 lines of project configuration.
