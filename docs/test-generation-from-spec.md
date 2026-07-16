---
date: 2026-05-20
context: Three linked questions — AI agent + Gherkin = quality tests? multi-agent writer+verifier workflow? deterministic programs to generate tests from a spec?
scope: state of the art 2024-2026, mature deterministic tools, recent academic papers
filter: anti-marketing, practical focus
---

# Test generation from spec — state of the art

## TL;DR

1. **Yes, an AI agent produces qualifiable tests from precise Gherkin** — industrial study 2025 (arxiv 2504.07244): 95% acceptance by product owners on the user-story → Gherkin step, 60% of tests directly correct and 92% after minor fix on the Gherkin → Cypress step. The bottleneck is no longer generation but **spec precision upstream**.

2. **Yes, the multi-agent writer+verifier pattern exists and works** — active research: Agent-as-a-Judge (Meta 2024), Multi-Agent Verification / MAV (arxiv 2502.20379), Multi-Agent Debate (arxiv 2510.12697). Debate amplifies correctness compared to static ensembles. Industrial maturity: emerging, few off-the-shelf tools yet.

3. **Yes, several mature deterministic programs exist** — four distinct families: search-based (EvoSuite, Pynguin, Randoop), symbolic execution (KLEE, CREST, angr), model-based (GraphWalker, ModelJUnit, SpecExplorer), spec-driven PBT (Hypothesis ghostwriter, icontract-hypothesis). None are AI. All have 10–25 years of maturity.

4. **But a critical nuance**: deterministic tools optimize mostly for **coverage** (branches, paths, mutants). They are blind to **business semantics**. AI does the opposite: strong on meaning, weak on systematics. The winning pattern 2025+ is **hybrid**.

---

## The question reformulated precisely

The user poses three sub-questions that reinforce each other:

- Q1 — If the human provides a **precise description** (Gherkin, examples, constraints), can the AI produce quality tests?
- Q2 — If the AI can write tests but with an error rate, can a **second verifier agent** filter them? Does the workflow user→writer-agent→verifier-agent hold?
- Q3 — Do **deterministic tools** (non-AI, reproducible) exist that do this? And if so, why are they talked about less?

Detailed answers below, sourced.

---

## 1. AI agent from Gherkin/spec — state of the art

### 1.1 Reference industrial study (2025)

Arxiv 2504.07244 — *Acceptance Test Generation with Large Language Models: An Industrial Case Study* — describes the real workflow used in production:

```
User story (free text)
    ↓ AutoUAT (LLM, GPT-4 Turbo)
Gherkin scenarios
    ↓ Test Flow (LLM + HTML context)
Executable Cypress scripts
    ↓ mandatory human review
Tests in CI
```

**Measured results**:

| Step | Metric | Value |
|---|---|---|
| AutoUAT (user story → Gherkin) | Product owner acceptance | 95% (62/65 positive respondents) |
| AutoUAT | Average quality score | 8/10 |
| AutoUAT | Usage volume over 2 months | 166 uses |
| Test Flow (Gherkin → Cypress) | Tests correct on first generation | 60% |
| Test Flow | Tests correct after minor fix (8%) or additional context (24%) | 92% |

**Main pitfall identified**: "insufficient context in user stories and Gherkin scenarios" — causes 12 of 20 problematic cases. **The bottleneck is spec precision, not generation**.

**Important**: no multi-agent in this study. Single-model + mandatory human review before deployment.

### 1.2 The AutoGen multi-agent pattern

ACM AST 2024 — *First Experiments on Automated Execution of Gherkin Test Specifications with Collaborating LLM Agents* — proposes a multi-agent architecture (AutoGen framework) that:
- Reads Gherkin scenarios.
- Autonomously explores the System Under Test.
- Generates test code on the fly.
- Evaluates execution results.

This is no longer just "write a test" — it's **executing a declarative spec**. Promising direction for E2E testing where test code becomes secondary.

### 1.3 Comparative studies 2025

- *Automated Test Generation Using LLM Based on BDD: A Comparative Study* (SciTePress 2025) — compares multiple LLMs on their ability to generate from BDD. Significant variability between models.
- *Baseline Evaluation of LLM-Facilitated UI Test-Case Generation from Gherkin Specifications* (Springer 2025) — baseline for UI testing, similar workflow.
- *LLM-as-a-Judge for Scalable Test Coverage Evaluation* (arxiv 2512.01232, 2025-12) — using an LLM as an evaluator of coverage of generated tests. First building block of multi-agent verifier.

### 1.4 Synthesis Q1

**Answer**: yes, an AI agent produces quality tests from precise Gherkin, with a correctness rate on the order of 60–95% depending on the step, **provided that**:

- The upstream spec is precise and self-sufficient (app context included).
- Human review persists for the remaining 5–40% of cases.
- Known pitfalls (oracle problem, over-mocking, test suppression) are mitigated by hooks/discipline (cf. the blog series article 1, "AI didn't kill tests, it made them indispensable").

The **bottleneck has moved up**: it was on test generation, it is now on spec formalization.

---

## 2. Multi-agent writer + verifier workflow

A domain of **very active** research since 2024.

### 2.1 Agent-as-a-Judge (Meta, 2024)

Core idea: one agent evaluates another by examining **the complete chain of actions and decisions**, not just the final result. Particularly suited to coding assistants because the "how and why" of success/failure is crucial.

When applied to test generation:
- Writer-agent produces a test suite from the spec.
- Judge-agent examines: spec conformance, non-tautological oracles, justified mocks, assertions present, case independence.
- Iteration until approval or quality threshold.

### 2.2 Multi-Agent Verification (MAV)

Arxiv 2502.20379 (2025) — *Multi-Agent Verification: Scaling Test-Time Compute with Multiple Verifiers*. Introduces **Aspect Verifiers (AVs)**: off-the-shelf LLMs, no additional training, each specialized on one aspect (security, performance, semantics, style). Combination via voting.

Direct application: one AV verifies coverage, another the oracle, another Gherkin conformance, another business semantics. Final vote.

### 2.3 Multi-Agent Debate

Arxiv 2510.12697 (2025) — *Multi-Agent Debate for LLM Judges with Adaptive Stability Detection*. Agents with opposing stances debate, iteratively refine their answers. **Debate amplifies correctness** compared to static ensembles (theorem formalized).

ChatEval, MADISSE: reference frameworks — one agent plays "general public", another "critic", another "domain expert". Structured deliberation.

### 2.4 Concrete pattern for test generation

Conceptual 3-agent workflow:

```
SPEC (Gherkin, examples, properties)
    ↓
[ Writer-Agent ]  ←──┐
    ↓                │
TEST SUITE          │ revisions
    ↓                │
[ Critic-Agent ]  ───┘   ← detects: tautologies, over-mocking, oracle
    ↓                       from impl, tests without assertion
APPROVAL or FEEDBACK
    ↓
[ Judge-Agent ]  ← final vote: approval, spec conformance validation
    ↓
TESTS IN CI
```

This is **exactly what the user intuited**. Research confirms its relevance and is beginning to provide frameworks (Agent-as-a-Judge, MAV, AutoGen).

### 2.5 Industrial maturity

State: **emerging**. Many papers, few off-the-shelf tools. Watch:

- **CodiumAI Cover-Agent** (open-source) — dedicated AI agent for test generation, with internal validation loop.
- **AutoGen** (Microsoft) — generic multi-agent framework, test support demonstrated (ACM AST 2024 paper).
- **CrewAI**, **LangGraph** — other multi-agent orchestrators applicable.

### 2.6 Synthesis Q2

**Answer**: yes, the multi-agent writer+verifier pattern is viable, documented academically, and beginning to industrialize. 2024–2025 research converges on:

- Distinct roles (writer / critic / judge) **significantly improve quality** over single-agent.
- Debate between agents with opposing stances **amplifies correctness** (result formalized).
- Aspect Verifiers specialized (semantics, security, performance) > generalist judge.

Practically: start with a 2-agent workflow (writer + critic), evolve to 3+ if measurable benefit. No mature off-the-shelf tool — to assemble via AutoGen / LangGraph / Claude Code with sub-agents.

---

## 3. Deterministic programs to generate tests

**This is the least-known angle in the current debate around AI, but it is rich and mature.** Four families, 10–25 years of R&D, production tools.

### 3.1 Search-based test generation (evolutionary / random)

| Tool | Language | Approach | Maturity |
|---|---|---|---|
| **EvoSuite** | Java | Evolutionary algorithms, optimize coverage | "State-of-the-art" since ~2011 |
| **Randoop** | Java | Feedback-directed random | Stable, IDE integrated |
| **Pynguin** | Python | GA + random (EvoSuite port) | Active, arxiv 2202.05218 |
| **AgitarOne** | Java | Proprietary, similar EvoSuite | Commercial |
| **Squaretest** | Java | Template-based + analysis | Commercial |

**Principle**: explore input space via mutation/evolution to maximize coverage (branches, paths, mutation score). Generate assertions from observed outputs.

**Strength**: reproducible (fixed seed), no LLM dependency, works on any code.

**Weakness**: generate tests that **verify the code as it is**, not as it should be. If prod has a bug, the generated test tests the bug. Tests often "brittle" and hard to read.

**Verdict**: useful for regressions on legacy code (lock the behavior), poorly suited to verifying spec conformance.

### 3.2 Symbolic / concolic execution

| Tool | Language | Approach |
|---|---|---|
| **KLEE** | LLVM bitcode (C/C++) | Symbolic, systematic path exploration |
| **CREST** | C | Concolic (symbolic + concrete) |
| **angr** | Binary | Symbolic at binary level |
| **SAGE** | x86 (Microsoft, proprietary) | Whitebox fuzzing |
| **JBSE** | Java bytecode | Symbolic |

**Principle**: execute code symbolically, generate constraints by path, solve via SMT solver (Z3, etc.). Produce one concrete input per path.

**Strength**: **formal guarantees of coverage** — each reachable path has a generated test. Deterministic, reproducible. Very useful in security (vulnerabilities) and critical systems.

**Weakness**: combinatorial explosion (path explosion), limited to simple types, barely practicable on large application codebases, oracle = absence of crash most often (oracle problem persists).

**Verdict**: excellent for identifying hard-to-reach paths and pathological inputs. Combine with human oracles or contracts.

### 3.3 Model-based testing (MBT)

| Tool | Language | Model |
|---|---|---|
| **GraphWalker** | Java, multi-binding | FSM via graphs |
| **ModelJUnit** | Java | FSM/EFSM in code |
| **SpecExplorer** | .NET (Microsoft) | Spec# / FSM |
| **fMBT** | Multi-language (Python frontend) | AAL/Python state |
| **Spec Explorer** | .NET | Spec# models |

**Principle**: human describes a **model** of the system (FSM, states + transitions). Tool automatically generates test sequences covering states, transitions, or objectives (random walk, all-paths, all-edges).

**Strength**: deterministic at the coverage strategy level, explicitly formalizes expected behavior (the model IS the spec). Historically very used in telecom (Ericsson on telephone switches).

**Weakness**: high initial modeling cost, drift between model and code, steep learning curve (Spec#, AAL).

**Verdict**: **under-used** tool in modern application software. Strong fit with stateful domains (FSM SIP, dialplan, protocols) — directly relevant for Wazo / Pyfreebilling.

### 3.4 Spec-driven PBT / contracts → tests

| Tool | Language | Approach |
|---|---|---|
| **Hypothesis ghostwriter** | Python | Type inference + lookup tables, **NOT AI**, generates PBT skeletons |
| **icontract-hypothesis** | Python | Contracts (pre/postconditions) → Hypothesis tests auto |
| **QuickCheck derive Arbitrary** | Haskell | Generate strategies from types |
| **fast-check arbitrary** | TS | Idem |
| **Eiffel AutoTest** | Eiffel | Design-by-Contract contracts → tests |

**Special case — Hypothesis ghostwriter**:

```bash
pip install "hypothesis[cli]"
hypothesis write numpy.add
hypothesis write my_module.parse_sip_uri
```

Ghostwriter inspects the function (signature, types, docstring) and generates a ready-to-complete PBT test file. **No AI**, just introspection + templates. Available functions:

- `fuzz` — tests that no valid input raises unexpected exception.
- `idempotent` — tests `f(f(x)) == f(x)`.
- `roundtrip` — tests `g(f(x)) == x` (encode/decode).
- `equivalent` — tests that two implementations give the same result.
- `binary_operation` — tests commutativity/associativity.
- `ufunc` — tests broadcasting/dtype for NumPy.

This is **exactly** a deterministic program that generates tests from a definition (the typed signature + implicit contract "f is idempotent"). Combine with `icontract` to make contracts explicit:

```python
import icontract

@icontract.require(lambda x: x >= 0)
@icontract.ensure(lambda result: result >= 0)
def sqrt(x: float) -> float:
    ...
```

→ `icontract-hypothesis` automatically generates a PBT test that respects the precondition and verifies the postcondition.

### 3.5 Hybrids — deterministic + AI

| Tool | Approach |
|---|---|
| **DiffBlue Cover** (Java) | Symbolic analysis + pattern learning. Maturity compromise. |
| **CodiumAI Cover-Agent** | LLM + internal feedback loop (tests must pass, coverage must increase). |
| **TestPilot** | LLM + test execution feedback |
| **CAT-LM** | Dedicated test generation model |
| **AutoTestGen** (IJRA 2025) | LLaMA-based framework, multi-language |

The hybrid pattern combines:
- **Deterministic** to generate skeletons / inputs / coverage.
- **LLM** to add business semantics + oracles.
- **Feedback loop** (tests must pass, coverage must rise).

### 3.6 Synthesis Q3

**Answer**: yes, several categories of deterministic tools exist and are mature:

1. **Search-based** (EvoSuite, Pynguin): generate from code, optimize coverage. Good for locking regressions.
2. **Symbolic execution** (KLEE): generate from code, formal guarantees. Excellent for security.
3. **Model-based** (GraphWalker, ModelJUnit): generate from FSM/EFSM model. **Strong fit telecom / stateful protocols**.
4. **Spec/contracts → tests** (Hypothesis ghostwriter, icontract-hypothesis): generate from types + contracts. **Deterministic, no AI**.

**Why they're talked about less**:
- Non-trivial ramp-up cost (modeling, contracts, configuration).
- Generate coverage, not meaning — hence the need for human or LLM complement.
- AI hype has eclipsed these tools even though they often stay superior in their domain.

---

## 4. Honest limits by approach

| Approach | Main strength | Main weakness |
|---|---|---|
| LLM from Gherkin | Understands business semantics | Depends on spec precision; 5–40% of tests to fix |
| Multi-agent writer+verifier | Detects tautologies, over-mocking | High token cost; tools still emerging |
| Search-based (EvoSuite, Pynguin) | Maximum coverage, reproducible | Unreadable tests; lock current behavior (bugs included) |
| Symbolic execution (KLEE) | Formal guarantees | Path explosion; oracle limited to crashes |
| Model-based (GraphWalker) | Explicit executable spec | Modeling cost; drift model/code |
| Ghostwriter / contracts | Deterministic, no AI | Covers predefined patterns only (idempotence, roundtrip…) |

---

## 5. Recommended workflow — practical synthesis

For modern application development, the pipeline that maximizes quality and minimizes human cost looks like:

```
1. Spec
   ├── User stories (text)
   ├── Gherkin (concrete Given/When/Then)
   ├── Types + contracts (icontract / pydantic / TypeScript)
   └── Property candidates (invariants, roundtrip, metamorphic)

2. Multi-source generation
   ├── LLM writer-agent       → acceptance tests from Gherkin
   ├── Hypothesis ghostwriter → PBT skeletons from types/contracts
   ├── Search-based (Pynguin) → coverage tests on existing code (legacy)
   └── (optional) KLEE/angr  → pathological security cases

3. Multi-agent verification
   ├── Critic-agent  → detects tautologies, over-mocking, oracle from code
   ├── Coverage gate → branch + mutation testing
   └── Human review  → non-obvious cases, business semantics

4. CI
   ├── Example-based tests (fast, targeted regression)
   ├── PBT tests (space coverage + invariants)
   ├── Mutation testing nightly
   └── Flaky detection continuous
```

**Key insight**: these are not three separate questions, it's **a single composed system**. The AI does what it does well (business semantics from Gherkin), deterministic does what it does well (systematic coverage, properties), multi-agent does what no single one does (cross-validation of spec conformance).

---

## 6. Updated recommendations for your context

| If your goal is… | Start with |
|---|---|
| E2E acceptance tests on a web app | LLM + Gherkin (study arxiv 2504.07244 replicates the workflow) |
| Robustify a pure lib (parser, codec, computation) | Hypothesis ghostwriter + manual complement |
| Test legacy code without tests | Pynguin (Python) or EvoSuite (Java) to lock regression |
| FSM telecom (SIP dialog, dialplan) | Model-based (GraphWalker) OR Hypothesis stateful (cf. `pbt-sip/`) |
| Security / binary parsing | KLEE / angr on critical functions |
| Validate spec ↔ tests conformance | Multi-agent critic (AutoGen + Claude Code sub-agents) |
| Mix everything | Pipeline section 5 |

For **you** specifically (Wazo, Pyfreebilling):

- **Pyfreebilling / pk-SBC**: Hypothesis ghostwriter + icontract on routing/rating modules. The pair is powerful and has no AI dependency.
- **SIP dialog / dialplan**: RuleBasedStateMachine (already demonstrated in `pbt-sip/`) OR GraphWalker if you want a visual model + exportable spec.
- **Acceptance tests for Wazo internal tools**: Gherkin + LLM writer-agent, with a critic-agent validating conformance (workflow §5). ROI is demonstrated (2025 study).

---

## 7. Limitations of this synthesis

- The field moves fast — multi-agent papers almost all post mid-2024. Mentioned tools may be obsolete in 12 months.
- No longitudinal study on **maintenance** of generated tests (does a generated test drift fast? update cost?).
- No independent benchmark comparing the four deterministic families on the same project.
- Multi-agent writer+verifier remains mostly academic — few large-scale industrialization reports.

---

## Sources

### Industrial studies and academic papers (2024–2026)

- *Acceptance Test Generation with Large Language Models: An Industrial Case Study*. arxiv 2504.07244 (2025). https://arxiv.org/html/2504.07244v1
- *First Experiments on Automated Execution of Gherkin Test Specifications with Collaborating LLM Agents*. ACM AST 2024. https://dl.acm.org/doi/10.1145/3678719.3685692
- *Automated Test Generation Using LLM Based on BDD: A Comparative Study*. SciTePress 2025. https://www.scitepress.org/Papers/2025/136836/136836.pdf
- *Baseline Evaluation of LLM-Facilitated UI Test-Case Generation from Gherkin Specifications*. Springer 2025. https://link.springer.com/chapter/10.1007/978-3-032-04288-0_3
- *LLM-as-a-Judge for Scalable Test Coverage Evaluation*. arxiv 2512.01232 (2025). https://www.arxiv.org/pdf/2512.01232
- *LLM-based Behaviour Driven Development for Hardware Design*. arxiv 2512.17814 (2025). https://arxiv.org/html/2512.17814v2
- *Multi-Agent Verification: Scaling Test-Time Compute with Multiple Verifiers*. arxiv 2502.20379 (2025). https://arxiv.org/pdf/2502.20379
- *Multi-Agent Debate for LLM Judges with Adaptive Stability Detection*. arxiv 2510.12697 (2025). https://arxiv.org/html/2510.12697v1
- *When AIs Judge AIs: The Rise of Agent-as-a-Judge Evaluation for LLMs*. arxiv 2508.02994 (2025). https://arxiv.org/html/2508.02994v1
- *Multi-Agent-as-Judge: Aligning LLM-Agent-Based Automated Evaluation with Multi-Dimensional Human Evaluation*. arxiv 2507.21028 (2025). https://arxiv.org/html/2507.21028v1
- *Pynguin: Automated Unit Test Generation for Python*. arxiv 2202.05218. https://arxiv.org/pdf/2202.05218
- *AutoTestGen: A LLaMA-based Framework for Automated Test Case Generation*. IJRA 2025. https://www.ijraset.com/best-journal/autotestgen-a-llama-based-framework-for-automated-test-case-generation-and-refinement-across-multiple-programming-languages

### Canon reference

- Cadar, C. et al. (2008). *KLEE: Unassisted and Automatic Generation of High-Coverage Tests for Complex Systems Programs*. OSDI.
- Cadar, C., Sen, K. (2013). *Symbolic Execution for Software Testing: Three Decades Later*. CACM. https://people.eecs.berkeley.edu/~ksen/papers/cacm13.pdf
- Fraser, G., Arcuri, A. (2011). *EvoSuite: Automatic test suite generation for object-oriented software*. ESEC/FSE.
- *Model-Based Testing in Practice: An Industrial Case Study using GraphWalker*. ACM 2021. https://dl.acm.org/doi/10.1145/3452383.3452388

### Tools — project pages

- **EvoSuite** — https://www.evosuite.org/
- **Pynguin** — https://pynguin.readthedocs.io/
- **Randoop** — https://randoop.github.io/randoop/
- **DiffBlue Cover** — https://www.diffblue.com/
- **KLEE** — https://klee-se.org/
- **angr** — https://angr.io/
- **GraphWalker** — https://graphwalker.github.io/
- **ModelJUnit** — https://modeljunit.sourceforge.net/
- **Hypothesis ghostwriter** — https://hypothesis.readthedocs.io/en/latest/reference/integrations.html
- **icontract-hypothesis** — https://github.com/mristin/icontract-hypothesis
- **CodiumAI Cover-Agent** — https://github.com/Codium-ai/cover-agent
- **AutoGen (multi-agent)** — https://microsoft.github.io/autogen/
- **LangGraph (multi-agent)** — https://langchain-ai.github.io/langgraph/

### Articulation with other documents in the folder

- See the blog series article 1, "AI didn't kill tests, it made them indispensable" — theoretical analysis of TDD + AI (the pitfalls that the verifier-agent must catch are listed there).
- `property-based-testing-hypothesis-deep-dive.md` — ghostwriter details and stateful (deterministic-for-PBT axis).
- `test-quality-tools-survey.md` — tools to measure quality of generated tests (feedback loop of multi-agent).
- `pbt-sip/` — runnable demo of stateful pattern for your domain.
