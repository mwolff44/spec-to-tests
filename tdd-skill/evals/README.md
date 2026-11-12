# Evaluation protocol — old doctrine vs. revised doctrine

Status: **protocol only**. No agentic benchmark has been executed for this
revision. Running it requires a model, credentials and a harness; none was used
here, and no result is claimed.

## Question

Does the revised TDD skill change agent behavior in the intended direction,
without merely producing more tests or a higher cost?

The comparison is paired:

- **Baseline**: commit `2203103cfa4bb52ee9ab5890184bbd0291042cb4` (old doctrine).
- **Candidate**: a commit selected at run time by a full 40-character SHA.
  `cases.json` stores `"ref": null` deliberately: a revision cannot embed the
  SHA of the commit that contains it. Resolve the chosen commit once, create a
  worktree at that SHA, and record the SHA plus tree/file hashes in the results
  manifest. Never use `working-tree` as the candidate.

Both sides receive the same prompt, repository snapshot, model and decoding
settings. Order is randomized and the scorer is blind to the side.

## Three separate dimensions

Do not collapse these into one score.

### 1. Doctrine conformity

Did the agent follow the revised rules?

- It selected a mode and a public seam; it did not impose a quota of functions or
  lines.
- It did not modify or delete an existing test to make code pass.
- It interpreted a first-run green by mode instead of treating it as an automatic
  failure or an automatic success.
- It treated a missing API as a legitimate structural RED and an unrelated
  import/fixture error as not-RED.
- It did not copy the oracle from the subject under test.
- It used real collaborators when practical; any internal double was justified
  and never replaced the SUT.
- It did not claim a semantic correction without independent evidence, a rerun
  and a renewed RED, or it stated the gap.
- It reported commands actually run, scope, results and limits.
- It treated hooks, the FSM and the strict script as optional/opt-in.

### 2. Real test quality

Judge the produced tests, not the prose:

- Does each test fail for the claimed reason?
- Is the oracle independent of the implementation?
- Would the test catch the behavior change it claims to pin?
- Are the cases discriminating rather than numerous?
- Do the tests survive a behavior-preserving refactor?
- For characterization, did the agent record observed behavior instead of
  silently correcting business behavior?
- For bug regression, does the test fail on the old baseline?

### 3. Cost

Measure, separately: wall time, tokens, tool calls, number of tests added, and
number of production lines changed. Report the numbers; do not impose a universal
budget. A higher cost is justified only by a measurable quality or doctrine gain.

## Activation and near-miss

Each prompt is classified before scoring:

- **activation**: the skill should trigger (for example a new feature with TDD, a
  bug fix with a regression test, characterization before refactor).
- **near-miss**: the skill should not impose TDD ceremony (for example "run the
  suite and summarize failures", or "explain what mutation testing is").
- **scenario**: a concrete task used to observe doctrine and test quality.

A near-miss that triggers the full workflow is a false positive, even if the
resulting tests are good.

## Procedure

1. Resolve the chosen candidate commit **once** to a full 40-character SHA and
   create worktrees at the two SHAs — never at `working-tree`:

   ```bash
   BASE=2203103cfa4bb52ee9ab5890184bbd0291042cb4
   CAND=$(git rev-parse --verify "$CHOSEN_COMMIT^{commit}")
   test "${#CAND}" -eq 40
   git worktree add /tmp/tdd-eval/base "$BASE"
   git worktree add /tmp/tdd-eval/cand "$CAND"
   ```

2. Run each case in a fresh session with the same model, temperature, seed and
   tool policy. Record the full transcript and commands, and keep the raw
   transcript private.
3. Randomize baseline/candidate order per case; hide the side from the scorer.
4. Score each dimension independently. For doctrine, record pass/fail per check
   and quote the evidence. For quality, inspect the diff and run the tests. For
   cost, record the metrics.
5. Report per-case results and aggregate counts; do not report a single blended
   score as if it measured one thing.
6. Keep raw transcripts private. Do not write credentials into them. Before any
   sharing explicitly authorized by the data owner, sanitize secrets,
   environment dumps and personal data. A secret scan is a complementary check,
   never a certification, and there is **no automatic publication**. Retain the
   SHA/hash manifest with the scoring sheet.

## Results manifest

Record at least: `baseline_commit`, `candidate_commit` (full SHA),
`baseline_tree`, `candidate_tree`, `skill_sha256`, `cases_sha256`, `model`,
`temperature`, `seed`, `transcript_paths`. `cases.json` lists the required
fields. The candidate SHA is recorded at run time, not stored in the files
under evaluation.

## Cases

`cases.json` contains eight cases collectively: one **activation** probe (TDD
new feature), one **near-miss** probe (run the suite; the exact data value is
`"kind": "near_miss"`), and six **scenarios** — bug regression,
characterization, tests-only, internal doubles, first-run green/semantic
correction, and the opt-in strict profile.

## Honest limits

- This protocol does not establish that the old doctrine was wrong or that the
  new one is empirically better. It measures observable behavior under one
  model and one prompt set.
- Doctrine conformity is not the same as test quality: an agent can follow every
  rule and still write a weak oracle.
- Cost depends on the harness and is not comparable across different tool
  budgets.
- The strict script is not exercised as a default; it is scored only as an
  opt-in behavior. The repository's hermetic script tests are separate.
