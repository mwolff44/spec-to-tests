# Hooks — TypeScript / JavaScript

Concrete, copy-paste-ready guardrails for TS/JS projects using `vitest` (or `jest`)
and StrykerJS. Maps to the six mechanisms in `hooks.md`. Every mechanism is
optional; the strict profile is opt-in, not the default.

Assumptions:
- Test files match `**/*.{test,spec}.{ts,tsx,js}` (configurable).
- Production code under `src/`.
- Package manager: `pnpm` (swap for `npm`/`yarn`/`bun` as needed).
- Test runner: `vitest`. (Jest patterns shown inline where they differ.)

## Setup options

| Option | When |
|---|---|
| **A. Plain git hooks** | Solo or quick start. |
| **B. `lefthook`** | Cross-platform, single binary, fast. Recommended. |
| **C. `husky` + `lint-staged`** | Most common in JS ecosystem. |

### Option B — install once

```bash
pnpm add -D lefthook
pnpm exec lefthook install
```

### Option C — install once

```bash
pnpm add -D husky lint-staged
pnpm exec husky init
```

---

## §0. Optional strict profile (opt-in)

Use the shared `scripts/tdd-verify-cycle.sh` with `TDD_LANG=ts` **only when you
explicitly select the strict profile**. It proves RED→GREEN ordering on the
selected target at commit time instead of trusting the agent — see
[hooks-python.md](hooks-python.md) §0 for the full rationale (gates A/B/C, the
additive/refactor constraints, the byte-for-byte worktree safety, and the
limit: ordering, not chronology or a business oracle). TS/React specifics:

- **Colocated tests.** Classified by suffix: `*.{test,spec}.{ts,tsx,js,jsx}` are
  tests, other `*.{ts,tsx,js,jsx}` are production — so `Component.test.tsx`
  sitting next to `Component.tsx` works, no `src/`-vs-`tests/` split needed.
- **Selector = vitest `-t` pattern.** The marker holds the test-name pattern,
  e.g. `checkout happy path`; the preset runs
  `npx vitest --run -t 'checkout happy path' --reporter=dot`.
- **Reporter.** The preset uses `--reporter=dot` (the old `basic` reporter was
  removed from current vitest — see the note in §2).

```yaml
# lefthook.yml
pre-commit:
  commands:
    tdd-verify-cycle:
      env: { TDD_LANG: ts }
      run: ./tdd-skill/scripts/tdd-verify-cycle.sh
```

Agent workflow:

```bash
echo 'checkout happy path' > .tdd-cycle
git add src/checkout.ts src/checkout.test.ts
TDD_LANG=ts git commit -m 'test+feat: checkout happy path'  # proves RED then GREEN
rm .tdd-cycle
```

For **Jest**, override the runner:
`TDD_RUN='npx jest -t "$sel"' TDD_RUN_ALL='npx jest'`.

---

## §1. Detect test modification during a Green cycle

> Legacy self-reported variant — prefer §0. Kept for setups that cannot run the
> test runner inside the pre-commit.

**Plain hook** — `.git/hooks/pre-commit` (chmod +x):

```bash
#!/usr/bin/env bash
set -euo pipefail

MARKER=".tdd-cycle"
[[ -f "$MARKER" ]] || exit 0

CURRENT_TEST="$(cat "$MARKER")"
CHANGED_TESTS=$(git diff --cached --name-only --diff-filter=AMD \
  | grep -E '\.(test|spec)\.(ts|tsx|js|jsx)$' || true)

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
    lint:
      glob: "*.{ts,tsx,js,jsx}"
      run: pnpm exec eslint --max-warnings 0 {staged_files}
    typecheck:
      glob: "*.{ts,tsx}"
      run: pnpm exec tsc --noEmit
```

**husky** — `.husky/pre-commit`:

```bash
#!/usr/bin/env bash
. "$(dirname "$0")/_/husky.sh"
./scripts/tdd-cycle-guard.sh
pnpm exec lint-staged
```

`package.json`:

```json
{
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": ["eslint --max-warnings 0"]
  }
}
```

---

## §2. RED confirmation — default for TDD and bug-regression missing behavior only

`scripts/tdd-red.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

TEST_PATTERN="${1:?usage: tdd-red.sh <vitest test name pattern>}"
LOG="$(mktemp)"

# vitest: -t selects by test name, --run disables watch
# (use --reporter=dot; the `basic` reporter was removed from recent vitest)
if pnpm exec vitest --run -t "$TEST_PATTERN" --reporter=dot > "$LOG" 2>&1; then
  echo "NO RED: the test passed on first run. This wrapper is for TDD/bug-regression missing behavior only. If this is characterization or tests-only, keep the useful coverage and reclassify; refactoring does not use this wrapper. Never force production code or an expected value." >&2
  cat "$LOG" >&2
  exit 1
fi

# Reject unrelated infrastructure errors. A missing module or type error can be
# a legitimate structural RED when the public API is absent; inspect it rather
# than rejecting every TS error automatically.
if grep -E '(SyntaxError|No test files found|Failed to load)' "$LOG" > /dev/null; then
  echo "ERROR: test failed for the WRONG reason (infra). Fix the test, re-run." >&2
  cat "$LOG" >&2
  exit 1
fi

echo "RED confirmed for: $TEST_PATTERN"
touch .tdd-red
```

For **Jest**, replace the vitest line:

```bash
pnpm exec jest -t "$TEST_PATTERN" --silent
```

Usage in agent loop:

```bash
./scripts/tdd-red.sh "checkout > happy path"
# TDD/bug-regression missing behavior only. If the test is already green,
# reclassify (characterization/tests-only) and keep the useful coverage.
[[ -f .tdd-red ]] && pnpm test && rm .tdd-red
```

---

## §3. Review the test diff (no file locking)

Before the commit, inspect the test diff:

```bash
git diff --cached -- 'src/**/*.{test,spec}.{ts,tsx,js,jsx}'
```

Confirm that test changes are additive or are an independently justified
correction (review only for business ambiguity, scope change or agreed risk). Do **not** use `chmod a-w`, `git update-index --skip-worktree` or
`--assume-unchanged` as a lock: those hide or confuse the diff and are not an
integrity boundary. Keep the diff visible.

---

## §4. CI gate — mutation testing with StrykerJS

Install:

```bash
pnpm add -D @stryker-mutator/core @stryker-mutator/vitest-runner @stryker-mutator/typescript-checker
```

(Use `@stryker-mutator/jest-runner` for Jest.)

`stryker.config.json`:

```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "packageManager": "pnpm",
  "reporters": ["progress", "clear-text", "html", "json"],
  "testRunner": "vitest",
  "checkers": ["typescript"],
  "tsconfigFile": "tsconfig.json",
  "mutate": [
    "src/**/*.ts",
    "!src/**/*.test.ts",
    "!src/**/*.spec.ts",
    "!src/**/__tests__/**"
  ],
  "incremental": true,
  "incrementalFile": ".stryker-tmp/incremental.json",
  "thresholds": { "high": 85, "low": 70, "break": 70 },
  "coverageAnalysis": "perTest",
  "concurrency": 4,
  "timeoutMS": 30000
}
```

`.github/workflows/mutation.yml`:

```yaml
name: mutation
on:
  pull_request:
    branches: [main]
    paths: ['src/**/*.ts', 'src/**/*.tsx']

jobs:
  stryker:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }

      - uses: pnpm/action-setup@v4
        with: { version: 9 }

      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'pnpm' }

      - run: pnpm install --frozen-lockfile

      - name: Restore Stryker incremental cache
        uses: actions/cache@v4
        with:
          path: .stryker-tmp
          key: stryker-${{ github.base_ref }}-${{ github.sha }}
          restore-keys: stryker-${{ github.base_ref }}-

      - name: Determine changed files
        id: changed
        run: |
          FILES=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \
            -- 'src/**/*.ts' 'src/**/*.tsx' \
            | grep -vE '\.(test|spec)\.tsx?$' || true)
          echo "files<<EOF" >> "$GITHUB_OUTPUT"
          echo "$FILES" >> "$GITHUB_OUTPUT"
          echo "EOF" >> "$GITHUB_OUTPUT"

      - name: Stryker (changed only)
        if: steps.changed.outputs.files != ''
        env:
          CHANGED_FILES: ${{ steps.changed.outputs.files }}
        run: |
          # CHANGED_FILES is newline-delimited (the delimiter produced above).
          # Build an argument array; never splice the expression into the shell.
          args=()
          while IFS= read -r f; do
            [[ -n "$f" ]] && args+=("--mutate" "$f")
          done <<< "$CHANGED_FILES"
          pnpm exec stryker run "${args[@]}"

      - uses: actions/upload-artifact@v4
        if: always() && steps.changed.outputs.files != ''
        with:
          name: stryker-report
          path: reports/mutation/
```

These numbers are **per-module examples chosen by risk**; there is no universal
threshold. Stryker exits non-zero when the score drops below the configured
`break` value, so set it deliberately for the module under change.

---

## §5. Assertion density and forbidden patterns

`.eslintrc.cjs`:

```js
module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'vitest'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:vitest/recommended', // or 'plugin:jest/recommended'
  ],
  rules: {
    // No empty catch in production
    'no-empty': ['error', { allowEmptyCatch: false }],
    // No unused exception variables
    '@typescript-eslint/no-unused-vars': ['error', { caughtErrors: 'all' }],
  },
  overrides: [
    {
      files: ['**/*.{test,spec}.{ts,tsx,js,jsx}'],
      rules: {
        'vitest/expect-expect': 'error',        // each test must have an expect
        'vitest/no-disabled-tests': 'error',
        'vitest/no-focused-tests': 'error',
        'vitest/no-identical-title': 'error',
        'vitest/valid-expect': 'error',
        'vitest/no-conditional-expect': 'error',
        'vitest/prefer-strict-equal': 'warn',
      },
    },
  ],
};
```

(For Jest, swap `plugin:vitest/*` → `plugin:jest/*` and the same rule families exist under `jest/`.)

CI `grep` guards as a safety net (`.github/workflows/lint.yml`):

```yaml
- name: Forbidden patterns
  run: |
    # Empty catch blocks in production
    if git grep -nE 'catch\s*\([^)]*\)\s*\{\s*\}' -- 'src/**/*.{ts,tsx}' \
        | grep -v '\.test\.\|\.spec\.'; then
      echo "Empty catch in src/ — agent-discipline.md §3"; exit 1
    fi
    # .only / .skip leaked to main
    if git grep -nE '\b(describe|it|test)\.(only|skip)\b' -- 'src/**/*.{ts,tsx,test.ts}'; then
      echo "Leftover .only or .skip"; exit 1
    fi
    # toHaveBeenCalled without matchers (over-mocking smell)
    COUNT=$(git grep -cE 'expect\([^)]+\)\.toHaveBeenCalled\(\)' -- 'src/**/*.test.ts' \
      | awk -F: '{s+=$2} END {print s+0}')
    if (( COUNT > 5 )); then
      echo "WARNING: $COUNT bare toHaveBeenCalled() — over-mocking smell"
    fi
```

---

## §6. Independent review by risk (optional, advanced)

When the risk justifies it, have another person or agent review the claim, the
oracle's provenance and the diff. This is a **review process**, not a mandatory
role split and not a harness configuration. The skill contains no tool or
permission fields: use your environment's review mechanism and keep the diff
visible.

---

## Minimum viable TS setup (optional)

1. `scripts/tdd-verify-cycle.sh` as an **opt-in** pre-commit with `TDD_LANG=ts`
   (§0) — proven RED→GREEN on the selected target, with the additive and
   refactor constraints stated in the strict profile.
2. StrykerJS GitHub Action with a per-module `thresholds.break` and incremental
   cache (§4) — the assertion-quality backstop `--no-verify` can't skip.

The ESLint `vitest/expect-expect` rule (§5) is a near-zero-cost bonus that
catches a large share of perpetually-green tests at lint time, before mutation
testing ever runs.
