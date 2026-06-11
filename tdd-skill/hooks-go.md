# Hooks — Go

Concrete, copy-paste-ready guardrails for Go projects using `go test` and
[`gremlins`](https://github.com/go-gremlins/gremlins) for mutation testing.
Maps to the four mechanisms in `hooks.md`.

Assumptions:
- Test files are `*_test.go`, located alongside production code (standard Go layout).
- Module structure under the repo root or under `cmd/`, `internal/`, `pkg/`.
- Test runner: `go test`.

## Setup options

| Option | When |
|---|---|
| **A. Plain git hooks** | Solo or quick start, zero dep. |
| **B. `lefthook`** | Recommended — single binary, fast, cross-language. |
| **C. `pre-commit` framework** | If the team already uses it across languages. |

### Option B — install once

Get the binary (Go install or release artifact):

```bash
go install github.com/evilmartians/lefthook@latest
lefthook install
```

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
  | grep -E '_test\.go$' || true)

for f in $CHANGED_TESTS; do
  if [[ "$f" != "$CURRENT_TEST" ]]; then
    echo "ERROR: test file '$f' modified outside the current cycle ($CURRENT_TEST)." >&2
    echo "Hint: agent-discipline.md §1 — never modify existing tests to make code pass." >&2
    exit 1
  fi
done
```

**lefthook** — `lefthook.yml`:

```yaml
pre-commit:
  parallel: true
  commands:
    tdd-cycle-guard:
      run: ./scripts/tdd-cycle-guard.sh
    fmt:
      glob: "*.go"
      run: gofmt -l {staged_files} && [ -z "$(gofmt -l {staged_files})" ]
    vet:
      run: go vet ./...
    staticcheck:
      run: staticcheck ./...
```

**Agent workflow** at cycle start:

```bash
echo "internal/checkout/checkout_test.go" > .tdd-cycle
git add internal/checkout/checkout_test.go    # the new failing test only
# ... write code, run tests ...
git commit -m "test+feat(checkout): T1 happy path"
rm .tdd-cycle
```

---

## §2. RED must fail first (and for the right reason)

`scripts/tdd-red.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Usage: tdd-red.sh ./internal/checkout TestHappyPath
PKG="${1:?usage: tdd-red.sh <package path> <test name>}"
TEST_NAME="${2:?usage: tdd-red.sh <package path> <test name>}"
LOG="$(mktemp)"

if go test -run "^${TEST_NAME}$" -count=1 "$PKG" > "$LOG" 2>&1; then
  echo "ERROR: test passed on first run — discipline §2. STOP and investigate." >&2
  cat "$LOG" >&2
  exit 1
fi

# Reject infrastructure errors (compile errors, missing packages, no tests)
if grep -E '(cannot find package|build failed|undefined:|no test files|^FAIL.*\[build failed\])' "$LOG" > /dev/null; then
  echo "ERROR: test failed for the WRONG reason (build/infra). Fix the test, re-run." >&2
  cat "$LOG" >&2
  exit 1
fi

# Ensure the failure is a real test failure, not a panic with no assertions
if ! grep -E '(--- FAIL:|FAIL\s+'"$PKG"')' "$LOG" > /dev/null; then
  echo "ERROR: test did not produce a normal FAIL — possible panic or skip." >&2
  cat "$LOG" >&2
  exit 1
fi

echo "RED confirmed: ${PKG} ${TEST_NAME}"
touch .tdd-red
```

Usage:

```bash
./scripts/tdd-red.sh ./internal/checkout TestCheckout_HappyPath
# proceed to GREEN only if .tdd-red exists
[[ -f .tdd-red ]] && go test ./... && rm .tdd-red
```

---

## §3. Lock test files between RED and Green

```bash
chmod a-w internal/checkout/checkout_test.go    # before Green
chmod u+w internal/checkout/checkout_test.go    # after Green commit
```

Alternative via git:

```bash
git update-index --skip-worktree internal/checkout/checkout_test.go
git update-index --no-skip-worktree internal/checkout/checkout_test.go
```

---

## §4. CI gate — mutation testing with gremlins

Install:

```bash
go install github.com/go-gremlins/gremlins/cmd/gremlins@latest
```

`gremlins.yaml` at repo root:

```yaml
mutants:
  # Built-in mutation sets — see go-gremlins docs for the full list
  arithmetic_base:    { enabled: true }
  conditionals_boundary: { enabled: true }
  conditionals_negation: { enabled: true }
  increment_decrement: { enabled: true }
  invert_assignments: { enabled: true }
  invert_bitwise:     { enabled: true }
  invert_logical:     { enabled: true }
  invert_loopctrl:    { enabled: true }
  invert_negatives:   { enabled: true }
  remove_self_assignments: { enabled: true }
  remove_statement:   { enabled: true }

silent: false
dry-run: false

test-cpu: 0          # use all cores
tags: ""             # build tags
threshold-efficacy: 70.0  # killed / (killed + lived) ≥ 70%
threshold-mcover:   60.0  # mutant coverage ≥ 60%
```

`.github/workflows/mutation.yml`:

```yaml
name: mutation
on:
  pull_request:
    branches: [main]
    paths: ['**/*.go']

jobs:
  gremlins:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }

      - uses: actions/setup-go@v5
        with: { go-version: 'stable', cache: true }

      - name: Install gremlins
        run: go install github.com/go-gremlins/gremlins/cmd/gremlins@latest

      - name: Determine changed Go packages
        id: changed
        run: |
          # Map changed *.go files to their containing package paths
          PKGS=$(git diff --name-only origin/${{ github.base_ref }}...HEAD -- '*.go' \
            | grep -v '_test\.go$' \
            | xargs -n1 dirname \
            | sort -u \
            | sed 's|^|./|' \
            | tr '\n' ' ')
          echo "pkgs=$PKGS" >> "$GITHUB_OUTPUT"
          echo "Changed packages: $PKGS"

      - name: Run gremlins on changed packages
        if: steps.changed.outputs.pkgs != ''
        run: |
          set -o pipefail
          gremlins unleash ${{ steps.changed.outputs.pkgs }} \
            --config gremlins.yaml \
            --output gremlins-report.json
        # gremlins exits non-zero when thresholds are not met

      - uses: actions/upload-artifact@v4
        if: always() && steps.changed.outputs.pkgs != ''
        with:
          name: gremlins-report
          path: gremlins-report.json
```

The `threshold-efficacy` and `threshold-mcover` in `gremlins.yaml` are the
gates — `gremlins unleash` returns non-zero on violation.

---

## §5. Assertion density and forbidden patterns

Go has no "assertions" per se — tests fail via `t.Error`, `t.Errorf`, `t.Fatal`,
`t.Fatalf`. The smell to detect is a test function that never calls any of
these (no `t.Error*`, no `t.Fatal*`, no `require.*` / `assert.*` from testify).

`.golangci.yml`:

```yaml
linters:
  enable:
    - errcheck       # detect unchecked errors (incl. silently-swallowed)
    - staticcheck
    - govet
    - revive
    - thelper        # test helpers must call t.Helper()
    - tparallel      # t.Parallel correctness
    - paralleltest   # missing t.Parallel
    - testifylint    # if you use testify
    - testpackage    # encourage *_test.go in separate package
    - gocritic
    - bodyclose
    - errorlint
    - nilerr
    - nilnil
    - nlreturn
    - unparam

issues:
  exclude-rules:
    - path: _test\.go
      linters: [errcheck, gosec]

linters-settings:
  errcheck:
    check-blank: true
    exclude-functions:
      - (io.Closer).Close   # idiomatic for deferred close
```

CI script to detect test functions with no assertion calls
(`scripts/check_assertion_density.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Find Test* funcs that contain no t.Error*, t.Fatal*, require.*, assert.* calls.
FAILED=0
while IFS= read -r file; do
  # Extract function bodies for Test* funcs and check for assertion calls
  awk '
    /^func Test[A-Z][A-Za-z0-9_]*\(/ {
      name=$0; depth=0; body=""; in_fn=1
    }
    in_fn {
      body=body"\n"$0
      for (i=1; i<=length($0); i++) {
        c=substr($0,i,1)
        if (c=="{") depth++
        else if (c=="}") {
          depth--
          if (depth==0) {
            if (body !~ /(t\.(Error|Fatal|Skip)|require\.|assert\.)/) {
              print FILENAME ": no assertion in " name
              exit_code=1
            }
            in_fn=0
            break
          }
        }
      }
    }
    END { exit exit_code+0 }
  ' "$file" || FAILED=1
done < <(find . -name '*_test.go' -not -path './vendor/*')

exit "$FAILED"
```

CI `grep` guards (`.github/workflows/lint.yml`):

```yaml
- name: Forbidden patterns
  run: |
    # Empty error swallowing in production
    if git grep -nE 'if err != nil \{\s*\}' -- '*.go' | grep -v '_test\.go'; then
      echo "Empty error block in production — agent-discipline.md §3"; exit 1
    fi
    # Errors assigned to _ in production (sometimes legit; flag for review)
    if git grep -nE '_, ?_ = .*\(' -- '*.go' | grep -v '_test\.go' \
        | grep -vE '(\.Close|\.Sync)\(\)'; then
      echo "WARNING: errors discarded into _"
    fi
    # t.Skip without a reason
    if git grep -nE 't\.Skip\(\s*\)' -- '*_test.go'; then
      echo "t.Skip without a reason — explain why or remove"; exit 1
    fi
    # Assertion density
    ./scripts/check_assertion_density.sh
```

---

## §6. Agent role split (optional, advanced)

Claude Code `settings.json`:

```json
{
  "permissions": {
    "tools": {
      "Edit":  { "paths": ["**/*_test.go"] },
      "Write": { "paths": ["**/*_test.go"] },
      "Read":  { "paths": ["**/*.go"] }
    }
  }
}
```

Inverse for implementer session.

---

## Go-specific notes for AI agents

A few patterns where Go agents misbehave more than in Python/TS — keep these
in mind in the system prompt:

1. **Generated empty error-returns** — agents often write `return nil` to make
   a test pass instead of implementing the logic. Mutation testing kills these
   reliably; `errcheck` doesn't, since the caller still gets a nil.
2. **`t.Skip` instead of fix** — when stuck, agents may skip the failing test.
   The §5 guard catches naked `t.Skip()`.
3. **Table-driven test bloat** — agents love generating large table-driven
   tests with one assertion shape. This is fine when intentional, but check
   that each case actually exercises a distinct branch — mutation testing
   surfaces redundant cases.
4. **`if err != nil { _ = err }` patterns** — silent swallowing in disguise.
   `errorlint` + `nilerr` flag most cases.

---

## Minimum viable Go setup (3 things)

1. `lefthook` running `tdd-cycle-guard.sh` (§1).
2. `scripts/tdd-red.sh` invoked before each Green (§2).
3. `gremlins` GitHub Action with thresholds in `gremlins.yaml` (§4).

Plus, near-zero-cost: enable `paralleltest` + `errcheck` + `thelper` in
`golangci-lint`. These catch a large share of agent-generated test smells
at lint time, before mutation testing ever runs.
