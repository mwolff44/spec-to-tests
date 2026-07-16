---
date: 2026-05-20
context: PBT/Hypothesis examples applied to a mini SIP parser and a stateful SIP dialog
purpose: concretely demonstrate that Hypothesis finds subtle bugs in code that "works"
---

# pbt-examples-sip

Two runnable examples that illustrate what PBT brings to your domain (VoIP/SIP):

1. **`sip_message.py` + `test_sip_roundtrip.py`** — simplified SIP parser/formatter.
   Round-trip property: `parse(format(msg)) == msg`. Bug included intentionally, to be discovered.

2. **`dialog.py` + `test_dialog_stateful.py`** — SIP dialog FSM (EARLY → CONFIRMED → TERMINATED) with a `RuleBasedStateMachine`. Bug included intentionally, to be discovered.

The bugs are not hidden maliciously: they are typical errors that humans or AI produce without noticing with example-based tests, and that Hypothesis finds in < 30 seconds.

## Installation

```bash
cd examples/pbt-sip
python -m venv .venv
source .venv/bin/activate   # or .venv/bin/activate.fish for fish
pip install -r requirements.txt
```

## Running the tests

```bash
pytest -v
```

Expected output (spoiler): **both suites find a failure and provide a minimal counter-example**.

To run only the round-trip suite:

```bash
pytest test_sip_roundtrip.py -v
```

To run only the stateful suite:

```bash
pytest test_dialog_stateful.py -v
```

## Seeing what Hypothesis does

```bash
pytest -v --hypothesis-show-statistics
```

Displays: number of examples generated, acceptance rate, shrinking, examples saved to the database.

## Once the bugs are found

To fix and re-test:

1. Read the minimal counter-example that Hypothesis displays.
2. Fix `sip_message.py` or `dialog.py` (the bug is commented `# BUG:` in the code).
3. Re-run — the tests should pass.

Hypothesis saves counter-examples in `.hypothesis/examples/`: found bugs will be re-tested with priority on the next run (automatic regression testing). Commit or .gitignore as you prefer.

## Enforcing the RED→GREEN cycle (§0 gate)

To develop this example test-first with the discipline enforced, wire the
hardened pre-commit gate
[`tdd-skill/scripts/tdd-verify-cycle.sh`](../../tdd-skill/scripts/tdd-verify-cycle.sh)
(here in `TDD_LANG=python` mode). It **proves** the cycle at commit time — the
staged production code is reverted, the test must fail; restored, it must pass —
rather than trusting that the test came first. Full rationale in
[`tdd-skill/hooks-python.md`](../../tdd-skill/hooks-python.md) §0.

```bash
# .git/hooks/pre-commit  (or via pre-commit / lefthook)
TDD_LANG=python /path/to/tdd-skill/scripts/tdd-verify-cycle.sh

# per cycle:
echo 'test_sip_roundtrip.py::test_roundtrip' > .tdd-cycle
git add sip_message.py test_sip_roundtrip.py
git commit -m 'test+feat: round-trip'      # gate proves RED→GREEN
rm .tdd-cycle
```

## Link with the rest of the repository

- The theoretical deep-dive: `../../docs/property-based-testing-hypothesis-deep-dive.md`
- The TDD skill: `../../tdd-skill/`
- The tools survey: `../../docs/test-quality-tools-survey.md`
