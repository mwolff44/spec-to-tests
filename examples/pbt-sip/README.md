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

## Link with the rest of the repository

- The theoretical deep-dive: `../property-based-testing-hypothesis-deep-dive.md`
- The TDD skill: `../tdd-skill/`
- The tools survey: `../test-quality-tools-survey.md`
