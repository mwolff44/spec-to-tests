#!/usr/bin/env bash
# tdd-verify-cycle.sh — hardened pre-commit gate for the red-green-refactor loop.
#
# It replaces the self-reported .tdd-red convention with a proof executed at
# commit time: the RED-before-GREEN ordering is verified by the hook, not
# narrated by the agent. See tdd-skill/hooks-python.md §2 and agent-discipline.md
# §1/§2/§5.
#
# Three gates, one chokepoint (the commit):
#   A. Cycle-declaration guard — production code staged without a declared cycle
#      is REJECTED (closes the `[[ -f marker ]] || exit 0` escape hatch of the
#      old §1 hook: default is now deny, not pass).
#   B. Test-modification guard (§1) — staged changes to any test file other than
#      the declared cycle test are REJECTED.
#   C. RED→GREEN proof (§2, §5) — with production code reverted to HEAD the cycle
#      test MUST fail for an assertion reason (RED); with it restored the test
#      MUST pass (GREEN). Otherwise the commit is rejected.
#
# Marker file `.tdd-cycle` (first line):
#   <pytest node id or path>   → RED→GREEN mode (gate C runs the full proof).
#   refactor [selector]        → GREEN-only mode (no code was reverted; the
#                                selector, or the whole suite, must stay green).
#
# Bypass note: `git commit --no-verify` skips this, as it skips any pre-commit
# hook. This gate is an in-loop auto-correction aid; the *hard* backstop is the
# server-side CI gate (hooks-python.md §4/§5), which --no-verify cannot reach.
#
# Config via env (defaults shown):
#   TDD_SRC_DIR='src'      production code directory (whole subtree, *.py)
#   TDD_TEST_DIR='tests'   test directory
#   TDD_PYTEST='pytest'    test runner command
# Directory pathspecs are used (not globs) so both top-level (tests/test_x.py)
# and nested (tests/unit/test_x.py) files match reliably; the .py filter is
# applied in-shell.
set -euo pipefail

MARKER=".tdd-cycle"
SRC_DIR="${TDD_SRC_DIR:-src}"
TEST_DIR="${TDD_TEST_DIR:-tests}"
PYTEST="${TDD_PYTEST:-pytest}"

die()  { echo "TDD-GATE: $*" >&2; exit 1; }
info() { echo "TDD-GATE: $*" >&2; }

# --- what is being committed (the index), added/modified only for src ---------
staged_src=$(git diff --cached --name-only --diff-filter=AM -- "$SRC_DIR" | grep -E '\.py$' || true)
# tests: also catch deletions/renames (AMD) — modifying/removing a test to go
# green is the failure mode gate B defends against.
staged_tests=$(git diff --cached --name-only --diff-filter=AMD -- "$TEST_DIR" | grep -E '\.py$' || true)

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
       echo 'tests/test_x.py::test_y' > $MARKER   # RED→GREEN cycle
       echo 'refactor' > $MARKER                  # green-only refactor commit
     (agent-discipline.md §1/§2 — no untracked production changes)."
fi

# From here a marker exists (staged_src may still be empty: a refactor/test commit).
RAW="$(head -n1 "$MARKER")"
MODE="cycle"
SELECTOR=""
if [[ "$RAW" == refactor* ]]; then
  MODE="refactor"
  SELECTOR="$(printf '%s' "${RAW#refactor}" | sed 's/^[[:space:]]*//')"
else
  SELECTOR="$RAW"                       # pytest node id or file path
  [[ -n "$SELECTOR" ]] || die "'$MARKER' is empty — declare a test node id or 'refactor'."
fi

# ---------------------------------------------------------------------------
# Gate B — test-modification guard (§1).
# ---------------------------------------------------------------------------
if [[ "$MODE" == "refactor" ]]; then
  # A refactor changes no behavior → it must not touch any test file.
  [[ -z "$staged_tests" ]] || die "refactor commit stages test files:
$(printf '  %s\n' $staged_tests)
     A refactor keeps tests untouched (agent-discipline.md §1). Split the commit."
else
  CYCLE_TEST="${SELECTOR%%::*}"          # strip ::node -> file path
  for f in $staged_tests; do
    [[ "$f" == "$CYCLE_TEST" ]] && continue
    die "test file '$f' staged but the declared cycle test is '$CYCLE_TEST'.
     Never modify/delete another test to make code pass (agent-discipline.md §1).
     If the spec genuinely changed, do it in a separate, reviewed commit."
  done
fi

# ---------------------------------------------------------------------------
# Gate C — RED→GREEN proof. Only when production code actually lands.
# ---------------------------------------------------------------------------
if [[ -z "$staged_src" ]]; then
  info "no production code staged; skipping RED→GREEN proof."
  exit 0
fi

command -v "${PYTEST%% *}" >/dev/null 2>&1 || die "runner '$PYTEST' not found on PATH."
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

run_target() {  # runs the cycle test/selector, quietly, into $1 (logfile)
  local log="$1"
  if [[ "$MODE" == "refactor" && -z "$SELECTOR" ]]; then
    $PYTEST -q --tb=short >"$log" 2>&1        # whole suite must stay green
  else
    $PYTEST "$SELECTOR" -q --tb=short >"$log" 2>&1
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

  # RED must fail. We do NOT try to classify *why* here: a missing-symbol
  # ImportError is a legitimate Python RED (the symbol under test doesn't exist
  # at HEAD yet). Genuine wiring breakage (typo, SyntaxError, unknown node id)
  # persists once the code is restored and is caught by the GREEN check below —
  # so GREEN subsumes the old §5 "wrong reason" grep, without its false rejects.
  if run_target "$LOG_RED"; then
    die "RED check FAILED: target '$SELECTOR' PASSES without the new production code.
     Either the behavior already existed, or the test asserts nothing real
     (agent-discipline.md §2 — perpetually-green). STOP and investigate.
$(tail -n 15 "$LOG_RED")"
  fi
  info "RED confirmed (target fails without the new code)."

  set_green_state
fi

if run_target "$LOG_GREEN"; then
  info "GREEN confirmed. Cycle proven RED→GREEN. ✔"
  exit 0
fi

# GREEN failed. If it looks like infrastructure rather than an assertion, the
# RED a moment ago was for the WRONG reason (§5): say so explicitly.
if grep -Eq '(ModuleNotFoundError|ImportError|SyntaxError|fixture .* not found|no tests ran|collected 0 items|errors during collection)' "$LOG_GREEN"; then
  die "GREEN check FAILED for an infrastructure reason (not an assertion) — §5.
     The earlier RED was therefore not a real behavioural failure. Fix the test
     wiring (imports, fixtures, node id) so it fails on its assertion, then recommit.
$(tail -n 20 "$LOG_GREEN")"
fi
die "GREEN check FAILED: with the staged code in place, the target does not pass.
$(tail -n 20 "$LOG_GREEN")"
