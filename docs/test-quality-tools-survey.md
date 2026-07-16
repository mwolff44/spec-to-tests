---
date: 2026-05-20
context: Survey of tools measuring actual test quality (beyond coverage)
scope: Python, TypeScript, Go as priority; mentions Java/Rust for reference
hypothesis: Test quality is a problem independent of the author (human or AI)
---

# Measuring actual test quality — tools survey

## Starting point

> "100 % line coverage" proves nothing about the **strength** of a test suite.
> Both humans and AI can write tests that pass without verifying anything.
> The right tool measures the **test's ability to detect a regression**, not its existence.

The paper *A Brief Survey on Oracle-based Test Adequacy Metrics* (arxiv 2212.06118) summarizes:
> "Code coverage only measures the degree to which structural code elements are
> executed; it does not measure the extent to which test oracles check the results.
> Using code coverage as a test adequacy metric overestimates the thoroughness."

Hence the need for complementary tools: mutation testing, test smell detectors, property-based testing, flakiness detectors.

## Reference taxonomy

Garousi & Felderer (Journal of Systems and Software 2018) established the canonical taxonomy of *test smells* — anti-patterns in test code. Definition: "a problem in test code which, if left to worsen, will cause problems in the future". This work was adopted by Bavota et al. (tsDetect, Java) and extended to Python (PyNose), JS, etc.

Reference smells to know (common vocabulary across tools below):

| Smell | Short definition |
|---|---|
| Assertion Roulette | Multiple assertions without messages → on failure, you don't know which one failed |
| Eager Test | One test verifies multiple methods/behaviors |
| Mystery Guest | Test depends on external resources not visible in the test |
| Resource Optimism | Test assumes an external resource exists |
| Conditional Test Logic | `if`/`for`/`try` in the test → untested branch |
| Empty Test | Test with no assertion or useful body |
| Sensitive Equality | `toString()`-based assertions |
| Sleepy Test | `sleep()` to synchronize |
| Magic Number Test | Unexplained constants |
| Default Test | Test left at its default name |
| Duplicate Assert | Same assertions repeated |
| Unknown Test | Test with no explicit assertion |
| Lazy Test | Multiple tests test the same method in the same way |
| Mocking smells (over-mocking) | Mocks for code you control |

---

## Four measurement axes

| Axis | Question answered | Main tools |
|---|---|---|
| **1. Coverage** | What code is executed by tests? | coverage.py, c8/istanbul, go cover |
| **2. Mutation testing** | Do tests detect behavior changes? | mutmut, Stryker, gremlins, PIT, cargo-mutants |
| **3. Test smells** | Is test code healthy? | PyNose, pytest-smell, ESLint plugins, golangci-lint |
| **4. Robustness** | Are tests stable? Do they cover the input space? | DeFlaker, iDFlakies, Hypothesis, fast-check, rapid |

None of these axes is sufficient alone. A strong suite checks all four.

---

## 1. Coverage — useful but insufficient

### Well-documented limitations

- **Line coverage** = the line executes, nothing about internal conditions.
- **Branch coverage** = both branches execute, nothing about condition combinations.
- **MC/DC** (Modified Condition/Decision Coverage) = each condition affects the decision independently. **Required in avionics (DO-178C) and automotive (ISO 26262, ASIL D)**. Costly but strong.
- **Path coverage** = combinatorial explosion, rarely used.

None measures the quality of **assertions** — a test without an assert having 100 % line coverage counts as "covered".

### Tools by language

| Language | Tool | Branch | MC/DC |
|---|---|---|---|
| Python | `coverage.py` + `pytest-cov` | yes (`branch=True`) | no |
| TS / JS | `c8` / `istanbul` (V8 native) | yes | no |
| Go | `go test -cover` + `-covermode=atomic` | partial (statements) | no |
| C/C++ | `gcov`, `llvm-cov` | yes | yes (clang `--mcdc`) |
| Java | JaCoCo | yes | partial |
| Rust | `cargo-llvm-cov` | yes | no |

**Recommendation**: enable branch coverage by default, target a **non-absolute** threshold (60–80 % depending on module criticality). Never use coverage as the sole metric.

---

## 2. Mutation testing — testing the test

Principle: mutate production (operator change, line removal, condition inversion), rerun tests, count how many mutants are **killed** (test fails) vs **survived** (test passes when it should fail).

### Tools

| Language | Tool | Status |
|---|---|---|
| Python | **mutmut** | active, dominant |
| Python | **cosmic-ray** | active, more configurable |
| JS / TS | **StrykerJS** | active, dominant, incremental mode |
| Java / Kotlin | **PIT (pitest)** | active, industry standard |
| Go | **gremlins** (go-gremlins) | active, recommended |
| Go | **ooze**, **go-mutesting** | less maintained |
| Rust | **cargo-mutants** | active |
| C / C++ | **mull** | active (LLVM-based) |
| Ruby | **mutant** | active |
| .NET | **Stryker.NET** | active |
| PHP | **Infection** | active |

### Mutation testing limitations

- **CPU cost** significant (each mutant = one full run). Mitigations: scope changed-files, incremental mode, parallelism.
- **Equivalent mutants**: some mutations are semantically equivalent (false survivors).
- **Operator set**: coverage depends on activated mutators.
- Does not detect **unimplemented behaviors** (if production lacks a feature, no mutant reveals it).

### Indicator

Mutation score = `killed / (killed + survived)`. Typical thresholds: ≥ 70 % critical, ≥ 60 % general. **Configure per module, not globally.**

---

## 3. Test smells — static quality of test code

### Python

| Tool | Maturity | Particularity |
|---|---|---|
| **PyNose** (JetBrains Research, arxiv 2108.04639) | Stable | PyCharm plugin. Detects 17 smells. Python reference. |
| **pytest-smell** (ACM ISSTA 2022) | Research | Pytest-specific. CSV export, CI-friendly. |
| **TEMPY** (BSSE 2022) | Research | Different AST approach. |
| **PyExamine** (arxiv 2501.18327, January 2025) | Recent | Comprehensive, architectural + code + test smells. |
| **ruff** (general linter) | Stable, dominant | Rules PT (flake8-pytest-style), B (bugbear), S (bandit). No dedicated smell detector but covers frequent cases. |

**Practical Python recommendation**: `ruff` in CI (covers 60% of need for free) + `PyNose` or `pytest-smell` in periodic review on critical modules.

### TypeScript / JavaScript

| Tool | Particularity |
|---|---|
| **ESLint** + `eslint-plugin-vitest` or `eslint-plugin-jest` | Standard. Rules: `expect-expect`, `valid-expect`, `no-conditional-expect`, `no-disabled-tests`, `no-focused-tests`. |
| **ESLint** + `eslint-plugin-testing-library` | React Testing Library-specific. |
| **SniffTSX** (ScienceDirect 2025) | Detects code smells in React + TypeScript. Extends ReactSniffer. |
| **SonarQube / SonarCloud** | Cross-language test rules, paid for organizations. |
| **TypeScript ESLint** targeted rules | `@typescript-eslint/no-explicit-any` (often abused in tests), etc. |

**No dedicated test smell detector for TS at the PyNose level.** State of the art in JS/TS is to **stack multiple ESLint plugins**. Active research but no dominant tool — see mcp-zen-of-languages issue #126 for an ongoing attempt.

**Practical TS recommendation**: ESLint with vitest/jest plugins and their `recommended` configs + strict rules enabled (`expect-expect` notably).

### Go

| Tool | Particularity |
|---|---|
| **golangci-lint** | Reference meta-linter (50+ linters). For tests: `thelper`, `paralleltest`, `tparallel`, `testifylint`, `testpackage`. |
| **staticcheck** | Included in golangci-lint. Detects many test smells indirectly. |
| **gocritic** | Detects suspicious patterns. |
| **errcheck** | Detects ignored errors (relevant for tests too). |

**No dedicated test smell detector for Go at the PyNose level.** Well-configured `golangci-lint` covers the essentials, but remains indirect.

**Practical Go recommendation**: `golangci-lint` with specialized test linters enabled (see `hooks-go.md` in `tdd-skill/`). Complement with mutation testing (gremlins) because Go smell detectors miss tests "empty of useful assertions".

---

## 4. Robustness — flakiness and input exploration

### Flaky test detection

| Tool | Approach | Language |
|---|---|---|
| **DeFlaker** (ICSE 2018) | Differential coverage (without rerun) | Java (extensible) |
| **iDFlakies** | Randomized execution order | Java, framework generalizable |
| **NonDex** | Randomizes Java non-deterministic implementations | Java |
| **FlakeFlagger** (ICSE 2021) | ML, prediction without rerun | Java |
| **FlaKat** (arxiv 2403.01003, 2024) | ML-based categorization | Multi |
| **pytest-rerunfailures** | Rerun + flag | Python |
| **jest --runInBand --testSequencer** | Detection by order | JS/TS |
| **gotestsum**, `go test -count=N` | Manual rerun | Go |

**Notable commercial solutions**: Trunk Flaky Tests, Buildkite Test Engine, BuildPulse, Datadog Test Optimization, Launchable. All offer detection + quarantine + reporting. Datadog Test Optimization integrates natively with runners.

**Atlassian Insight 2025**: 150,000 dev hours/year lost to flaky tests. Enough to justify tooling investment.

### Property-based testing — strengthen oracles

The idea: instead of writing `assert add(2, 3) == 5`, write `for all a, b: add(a, b) == a + b`. The framework generates inputs (including edge cases) and attempts to refute the property.

| Language | Tool | Maturity |
|---|---|---|
| Python | **Hypothesis** | Excellent, standard |
| JS / TS | **fast-check** | Excellent |
| Go | **rapid**, **gopter** | Stable |
| Rust | **proptest**, **quickcheck** | Stable |
| Java | **jqwik**, **junit-quickcheck** | Stable |
| Haskell | **QuickCheck** (the original) | Stable |

**Calibrating anecdote**: Hypothesis discovered a Unicode bug in a production JSON parser that had 95 % line coverage in example-based tests. Bugs often live where examples don't think to look.

**Limitations**: PBT works best on pure functions. On side-effects, the oracle is harder to formulate. PBT does not replace targeted regression tests — it's a **complement**, not a substitute.

---

## Recommended stack by language (synthesis)

### Python

```
Cheap & critical:
  - coverage.py --branch in CI                    (threshold per module)
  - ruff with PT, S, B enabled                    (lint-time)
  - check_assertion_density.py custom             (CI grep guard)

Strong signal:
  - mutmut in CI on changed files                 (mutation score ≥ 70%)
  - Hypothesis on pure critical functions         (augmented oracle)

Quality audit (periodic):
  - PyNose or pytest-smell                        (monthly report)
```

### TypeScript / JavaScript

```
Cheap & critical:
  - c8 / istanbul --branches in CI
  - ESLint + plugin-vitest|jest (strict rules)
  - eslint-plugin-testing-library if React

Strong signal:
  - StrykerJS in CI, incremental                  (thresholds.break: 60)
  - fast-check on business domain                 (augmented oracle)

Quality audit:
  - SonarCloud test smell rules (if licensed)
```

### Go

```
Cheap & critical:
  - go test -cover -covermode=atomic
  - golangci-lint with thelper, paralleltest, tparallel, testifylint, errcheck
  - check_assertion_density.sh custom

Strong signal:
  - gremlins in CI on changed packages            (efficacy ≥ 70%, mcover ≥ 60%)
  - rapid or gopter on pure functions
```

### For all three

- **Flakiness**: pytest-rerunfailures / Jest retry / `go test -count` in CI, with automatic quarantine above a threshold. Consider Trunk Flaky Tests or Datadog Test Optimization if team is ≥ 5 devs.
- **Mutation testing**: non-negotiable on critical modules. Costs CI CPU but is the only tool that directly measures **assertion strength**.
- **Property-based testing**: adopt by pilot modules, not globally. Pure functions in the domain are the best candidates.

---

## What doesn't exist (yet)

- **No dominant test smell detector for TS** at the PyNose level for Python.
- **No standardized tool for measuring oracle quality** beyond mutation testing.
- **No unified cross-language tool** measuring all four axes together — SonarQube approaches this commercially but remains partial on mutation and robustness.
- **No dedicated "test generated by AI" detector** — although patterns are documented (arxiv 2602.00409 on over-mocking), no tool flags it specifically.

---

## Articulation with the `tdd-skill/` skill

This survey complements the TDD skill:

- `tdd-skill/hooks-*.md` §4 (mutation testing) → axis 2 here.
- `tdd-skill/hooks-*.md` §5 (assertion density, forbidden patterns) → axis 3 here.
- `tdd-skill/agent-discipline.md` §4 (mocking restraint) → mitigates "Over-mocking" smells.
- `tdd-skill/agent-discipline.md` §6 (oracle from spec, not code) → addresses the oracle problem covered by PBT.

A test suite whose **four axes are measured and above their threshold** is strong, regardless of the code's author. That's the reasonable objective.

---

## Sources

### Academic references

- Garousi, V., Küçük, B. (2018). *Smells in software test code: A survey of knowledge in industry and academia*. Journal of Systems and Software. https://www.sciencedirect.com/science/article/abs/pii/S0164121217303060
- Bavota, G. et al. (2015). *Are test smells really harmful? An empirical study*. (origin of tsDetect)
- Bell, J. et al. (2018). *DeFlaker: Automatically Detecting Flaky Tests*. ICSE. https://experts.illinois.edu/en/publications/deflaker-automatically-detecting-flaky-tests/
- Lam, W. et al. *iDFlakies: A Framework for Detecting and Partially Classifying Flaky Tests*. https://www.researchgate.net/publication/344743752
- Alshammari, A. et al. *FlakeFlagger: Predicting Flakiness Without Rerunning Tests*. ICSE 2021. https://www.jonbell.net/preprint/icse21-flakeflagger.pdf
- Wang, T. et al. (2021). *PyNose: A Test Smell Detector For Python*. arxiv: https://arxiv.org/abs/2108.04639
- *Pytest-Smell: a smell detection tool for Python unit tests*. ACM ISSTA 2022. https://dl.acm.org/doi/10.1145/3533767.3543290
- *PyExamine: A Comprehensive, Un-Opinionated Smell Detection Tool for Python*. arxiv 2501.18327 (2025). https://arxiv.org/html/2501.18327v1
- *Test Smell Detection Tools: A Systematic Mapping Study*. arxiv 2104.14640. https://arxiv.org/pdf/2104.14640
- *A Brief Survey on Oracle-based Test Adequacy Metrics*. arxiv 2212.06118. https://arxiv.org/pdf/2212.06118
- *FlaKat: A Machine Learning-Based Categorization Framework for Flaky Tests*. arxiv 2403.01003 (2024). https://arxiv.org/html/2403.01003v1
- *Exploring Tools for Flaky Test Detection, Correction, and...* SAST 2024. https://sol.sbc.org.br/index.php/sast/article/download/30211/30018/

### Tools — project pages

- **mutmut** — https://github.com/boxed/mutmut
- **StrykerJS** — https://stryker-mutator.io/
- **gremlins** — https://github.com/go-gremlins/gremlins
- **PIT** — https://pitest.org/
- **cargo-mutants** — https://github.com/sourcefrog/cargo-mutants
- **Hypothesis** — https://hypothesis.readthedocs.io/
- **fast-check** — https://fast-check.dev/
- **rapid** — https://github.com/flyingmutant/rapid
- **PyNose** — https://github.com/JetBrains-Research/PyNose
- **pytest-smell** — https://pypi.org/project/pytest-smell/
- **golangci-lint** — https://golangci-lint.run/
- **ruff** — https://docs.astral.sh/ruff/
- **eslint-plugin-vitest** — https://github.com/veritem/eslint-plugin-vitest
- **eslint-plugin-jest** — https://github.com/jest-community/eslint-plugin-jest
- **Trunk Flaky Tests** — https://trunk.io/flaky-tests
- **Datadog Test Optimization** — https://docs.datadoghq.com/tests/

### Industry / serious blogs

- Atlassian (2025): economic impact of flaky tests (150k h/year).
- Reproto (2025). *How to Fix Flaky Tests in 2025*. https://reproto.com/how-to-fix-flaky-tests-in-2025-a-complete-guide-to-detection-prevention-and-management/
- TestDino (2026). *9 Best Flaky Test Detection Tools QA Teams Should Use in 2026*. https://testdino.com/blog/flaky-test-detection-tools
