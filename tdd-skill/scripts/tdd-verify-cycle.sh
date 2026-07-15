#!/usr/bin/env bash
# tdd-verify-cycle.sh — hardened, language-agnostic pre-commit gate for the
# red-green-refactor loop (Python / Go / TypeScript-JS, or any runner you wire).
#
# It replaces the self-reported .tdd-red convention with a proof executed at
# commit time: the RED-before-GREEN ordering is verified by the hook, not
# narrated by the agent. See hooks-{python,go,typescript}.md §0/§2 and
# agent-discipline.md §1/§2/§5.
#
# Three gates, one chokepoint (the commit):
#   A. Cycle-declaration guard — production code staged without a declared cycle
#      is REJECTED (closes the `[[ -f marker ]] || exit 0` escape hatch of the
#      old §1 hook: default is now deny, not pass).
#   B. Test-modification guard (§1) — in a code-landing (cycle) commit a test
#      file may only GROW: adding a new file, or appending to an existing one
#      (a purely additive diff), is allowed — that is how you author the cycle's
#      test. DELETING a test file, or a diff that removes/changes existing lines
#      in one, is REJECTED. This distinguishes "append a new test" from "alter an
#      existing test to make code pass" at the diff level, with no need to know
#      which file is "the cycle test" (language-agnostic form of §1).
#   C. RED→GREEN proof (§2, §5) — with the staged production files reverted to
#      HEAD the cycle target MUST fail (RED); with them restored it MUST pass
#      (GREEN). The old "wrong-reason" grep is dropped from RED: a missing-symbol
#      ImportError (Python) or a compile failure (Go, because test and code share
#      a package) is a *legitimate* RED. Genuine wiring breakage persists into
#      GREEN and is caught there — GREEN subsumes the reason check.
#
# Files are classified by SUFFIX regex, not by directory, so colocated tests
# (Go `foo_test.go`, React `Component.test.tsx`) work as well as a separate
# `tests/` tree (Python).
#
# Marker file `.tdd-cycle` (first line):
#   <run selector>       → RED→GREEN mode. The selector is passed to the runner
#                          (pytest node id / `pkg::TestName` for Go / vitest -t
#                          pattern for TS).
#   refactor [selector]  → GREEN-only mode: no code was reverted; the selector,
#                          or the whole suite if none, must stay green.
#
# Config: pick a preset with TDD_LANG (python|go|ts), or override any of the
# four knobs directly:
#   TDD_SRC_RE   regex of production files (matched, minus TDD_TEST_RE)
#   TDD_TEST_RE  regex of test files
#   TDD_RUN      runner for one selector; the template references "$sel"
#   TDD_RUN_ALL  runner for the whole suite
#
# Bypass note: `git commit --no-verify` skips this, like any pre-commit hook.
# The hard backstop is the server-side CI gate (§4/§5), unreachable by --no-verify.
set -euo pipefail

MARKER=".tdd-cycle"
TDD_LANG="${TDD_LANG:-python}"

case "$TDD_LANG" in
  python)
    : "${TDD_SRC_RE:=\.py$}"
    : "${TDD_TEST_RE:=(^|/)(test_[^/]*\.py|[^/]*_test\.py)$|(^|/)tests?/.*\.py$}"
    [[ -n "${TDD_RUN:-}" ]]     || TDD_RUN='pytest "$sel" -q --tb=short'
    [[ -n "${TDD_RUN_ALL:-}" ]] || TDD_RUN_ALL='pytest -q --tb=short'
    ;;
  go)
    : "${TDD_SRC_RE:=\.go$}"
    : "${TDD_TEST_RE:=_test\.go$}"
    # selector syntax: '<pkg>::<TestName>', e.g. ./internal/checkout::TestHappy
    [[ -n "${TDD_RUN:-}" ]]     || TDD_RUN='go test -count=1 -run "^${sel##*::}$" "${sel%%::*}"'
    [[ -n "${TDD_RUN_ALL:-}" ]] || TDD_RUN_ALL='go test ./...'
    ;;
  ts|js|typescript|javascript)
    : "${TDD_SRC_RE:=\.(ts|tsx|js|jsx|mts|cts)$}"
    : "${TDD_TEST_RE:=\.(test|spec)\.(ts|tsx|js|jsx|mts|cts)$}"
    [[ -n "${TDD_RUN:-}" ]]     || TDD_RUN='npx vitest --run -t "$sel" --reporter=dot'
    [[ -n "${TDD_RUN_ALL:-}" ]] || TDD_RUN_ALL='npx vitest --run --reporter=dot'
    ;;
  custom)
    : "${TDD_SRC_RE:?set TDD_SRC_RE for TDD_LANG=custom}"
    : "${TDD_TEST_RE:?set TDD_TEST_RE for TDD_LANG=custom}"
    : "${TDD_RUN:?set TDD_RUN for TDD_LANG=custom}"
    : "${TDD_RUN_ALL:?set TDD_RUN_ALL for TDD_LANG=custom}"
    ;;
  *)
    echo "TDD-GATE: unknown TDD_LANG='$TDD_LANG' (python|go|ts|custom)." >&2; exit 1
    ;;
esac

die()  { echo "TDD-GATE: $*" >&2; exit 1; }
info() { echo "TDD-GATE: $*" >&2; }

# --- what is being committed (the index), classified by suffix regex ----------
staged_src=$(git diff --cached --name-only --diff-filter=AM \
  | grep -E "$TDD_SRC_RE" | grep -Ev "$TDD_TEST_RE" || true)
# test files deleted — always a §1 violation in a cycle.
staged_test_dels=$(git diff --cached --name-only --diff-filter=D \
  | grep -E "$TDD_TEST_RE" || true)
# test files modified (M) — allowed only if the diff is purely additive.
staged_test_edits=$(git diff --cached --name-only --diff-filter=M \
  | grep -E "$TDD_TEST_RE" || true)
# any staged test change (add/modify/delete) — used by refactor mode.
staged_tests_any=$(git diff --cached --name-only --diff-filter=AMD \
  | grep -E "$TDD_TEST_RE" || true)

# Nothing production-relevant staged and no cycle open → not our business.
if [[ -z "$staged_src" && ! -f "$MARKER" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# Gate A — cycle declaration is mandatory when production code lands.
# ---------------------------------------------------------------------------
if [[ -n "$staged_src" && ! -f "$MARKER" ]]; then
  die "production code staged with no '$MARKER' declared.
     Declare the cycle first, e.g.:
       echo '<run selector>' > $MARKER   # RED→GREEN cycle
       echo 'refactor' > $MARKER         # green-only refactor commit
     (agent-discipline.md §1/§2 — no untracked production changes)."
fi

RAW="$(head -n1 "$MARKER")"
MODE="cycle"
SELECTOR=""
if [[ "$RAW" == refactor* ]]; then
  MODE="refactor"
  SELECTOR="$(printf '%s' "${RAW#refactor}" | sed 's/^[[:space:]]*//')"
else
  SELECTOR="$RAW"
  [[ -n "$SELECTOR" ]] || die "'$MARKER' is empty — declare a run selector or 'refactor'."
fi

# ---------------------------------------------------------------------------
# Gate B — test-modification guard (§1).
# ---------------------------------------------------------------------------
if [[ "$MODE" == "refactor" ]]; then
  [[ -z "$staged_tests_any" ]] || die "refactor commit stages test files:
$(printf '  %s\n' $staged_tests_any)
     A refactor keeps tests untouched (agent-discipline.md §1). Split the commit."
else
  [[ -z "$staged_test_dels" ]] || die "cycle commit deletes existing test(s):
$(printf '  %s\n' $staged_test_dels)
     Never remove a test to make code pass (agent-discipline.md §1)."
  # A modified test file is fine only if it purely GROWS (0 lines removed).
  for f in $staged_test_edits; do
    removed=$(git diff --cached --numstat -- "$f" | awk 'NR==1{print $2+0}')
    [[ "${removed:-0}" -eq 0 ]] || die "cycle commit changes existing lines in test '$f' \
($removed removed).
     A cycle may only APPEND a new test; altering existing test lines to make
     code pass is the §1 violation. Revise specs in a separate, reviewed commit."
  done
fi

# ---------------------------------------------------------------------------
# Gate C — RED→GREEN proof. Only when production code actually lands.
# ---------------------------------------------------------------------------
if [[ -z "$staged_src" ]]; then
  info "no production code staged; skipping RED→GREEN proof."
  exit 0
fi

command -v "${TDD_RUN%% *}" >/dev/null 2>&1 || die "runner '${TDD_RUN%% *}' not found on PATH."
git rev-parse --verify -q HEAD >/dev/null || die "no HEAD commit; cannot verify RED against a baseline."

# We only ever mutate the worktree copy of the STAGED src files (to swap between
# HEAD and index content for the RED/GREEN runs). Everything else — untracked
# files, unstaged edits to other files — is never touched, so no stash is needed
# and there is no pop-conflict / data-loss hazard. We back up the exact current
# worktree bytes of each staged src file (which may carry unstaged edits) and
# restore them verbatim on exit.
LOG_RED="$(mktemp)"; LOG_GREEN="$(mktemp)"
BAKDIR="$(mktemp -d)"
declare -a SRC_FILES=() BAK_FILES=()
_i=0
while IFS= read -r _f; do
  [[ -z "$_f" ]] && continue
  SRC_FILES+=("$_f")
  cp -- "$_f" "$BAKDIR/$_i" 2>/dev/null || : > "$BAKDIR/$_i"
  BAK_FILES+=("$BAKDIR/$_i")
  _i=$((_i + 1))
done <<< "$staged_src"

cleanup() {
  local rc=$? j
  for ((j = 0; j < ${#SRC_FILES[@]}; j++)); do
    cp -- "${BAK_FILES[$j]}" "${SRC_FILES[$j]}" 2>/dev/null || true
  done
  rm -rf "$BAKDIR" "$LOG_RED" "$LOG_GREEN"
  return $rc
}
trap cleanup EXIT

run_target() {  # $1=logfile  $2=selector ("" ⇒ whole suite). Templates use $sel.
  local log="$1" sel="$2"
  if [[ -z "$sel" ]]; then
    eval "$TDD_RUN_ALL" >"$log" 2>&1
  else
    eval "$TDD_RUN" >"$log" 2>&1
  fi
}

# Put each staged src file into its HEAD state: restore from HEAD if it existed
# there, otherwise remove it (a brand-new production file is absent at HEAD).
set_red_state() {
  local f
  for f in "${SRC_FILES[@]}"; do
    if git cat-file -e "HEAD:$f" 2>/dev/null; then
      git restore --worktree --source=HEAD -- "$f" \
        || die "could not revert '$f' to HEAD for the RED check."
    else
      rm -f -- "$f"
    fi
  done
}

# Put each staged src file into its index (proposed-commit) state.
set_green_state() {
  git restore --worktree -- "${SRC_FILES[@]}" \
    || git checkout -- "${SRC_FILES[@]}" \
    || die "could not restore staged src for the GREEN check."
}

if [[ "$MODE" == "cycle" ]]; then
  set_red_state

  # RED must fail. We do NOT classify *why*: a missing-symbol ImportError
  # (Python) or a package that no longer compiles (Go) is a legitimate RED.
  # Real wiring breakage persists into GREEN and is caught there.
  if run_target "$LOG_RED" "$SELECTOR"; then
    die "RED check FAILED: target '$SELECTOR' PASSES without the new production code.
     Either the behavior already existed, or the test asserts nothing real
     (agent-discipline.md §2 — perpetually-green). STOP and investigate.
$(tail -n 15 "$LOG_RED")"
  fi
  info "RED confirmed (target fails without the new code)."

  set_green_state
fi

if run_target "$LOG_GREEN" "$SELECTOR"; then
  info "GREEN confirmed. Cycle proven RED→GREEN. ✔"
  exit 0
fi

# GREEN failed. If it looks like infrastructure rather than an assertion, the
# RED a moment ago was for the WRONG reason (§5): say so explicitly.
if grep -Eq '(ModuleNotFoundError|ImportError|SyntaxError|fixture .* not found|no tests ran|collected 0 items|errors during collection|Cannot find module|build failed|undefined:|no test files|No test files found|Failed to load|TS[0-9]+:)' "$LOG_GREEN"; then
  die "GREEN check FAILED for an infrastructure reason (not an assertion) — §5.
     The earlier RED was therefore not a real behavioural failure. Fix the test
     wiring (imports, fixtures, build, selector) so it fails on its assertion.
$(tail -n 20 "$LOG_GREEN")"
fi
die "GREEN check FAILED: with the staged code in place, the target does not pass.
$(tail -n 20 "$LOG_GREEN")"
