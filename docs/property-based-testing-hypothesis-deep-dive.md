---
date: 2026-05-20
context: Deep-dive on property-based testing (PBT), with Hypothesis as the primary implementation
scope: fundamentals, patterns, stateful, IA workflow, pitfalls, cross-language equivalents
prerequisites: have read test-quality-tools-survey.md (axis 4) and tdd-skill/SKILL.md
---

# Property-based testing — deep dive (Hypothesis)

## Why PBT deserves its own file

Axes 1–3 (coverage, mutation, smells) measure the quality **of test code**.
PBT tackles a different hole: the quality **of oracles**. Its thesis:
*"humans and AIs think of the same examples; PBT thinks of the examples they forget."*

Calibration data (collected 2024–2026):

- Hypothesis discovered a Unicode bug in a production JSON parser that had **95% line coverage** in example-based tests.
- The **Agentic PBT** agent (arxiv 2510.09907, 2025) found **984 bug reports across 100 Python packages**, including bugs validated and merged into **NumPy, AWS Lambda Powertools, Huggingface Tokenizers, CloudFormation CLI, python-dateutil**. Cost: 9.93 USD per validated bug. 56% of reports were valid.
- Anthropic Red (2026) confirms: *"agentic property-based testing could become an increasingly valuable complement to human-written testing"*, and emphasizes the **reflection loop** to filter false positives.

PBT is not a substitute for example-based tests — it's a **second orthogonal safety net**, which catches a specific class of bugs (numeric boundaries, encoding, operation sequences, combined invariants).

---

## 1. Fundamentals

### Example-based vs Property-based

```python
# Example-based — one case, one oracle.
def test_reverse_concrete():
    assert reverse([1, 2, 3]) == [3, 2, 1]

# Property-based — a property that must hold for all x.
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_reverse_involution(xs):
    assert reverse(reverse(xs)) == xs
```

The difference is not "more cases" — it's **another level of abstraction**.
The example-based oracle is *"output = 5"*. The PBT oracle is *"reverse is its own inverse"*. The latter does not depend on a one-off computation — it's exactly what sidesteps the oracle problem (cf. `tdd-skill/agent-discipline.md` §6).

### Shrinking — the killer argument

When Hypothesis finds a failure, it doesn't stop at the first counterexample. It **shrinks** to the smallest possible counterexample. An assertion that fails on `[42, -7, 9999, 0, ...]` will be reduced to `[0]` or a minimal case. This is what makes diagnosis feasible — without shrinking, a random tester is useless in practice.

### The PBT cycle

```
1. Choose a strategy (input space)
2. Formulate a property (an invariant or a relation)
3. Hypothesis generates N examples, executes the property
4. If failure: shrink → minimal counterexample → report
5. If success: records in database → retests on next run
```

---

## 2. Anatomy of a Hypothesis property

```python
from hypothesis import given, assume, settings, strategies as st

@given(
    x=st.integers(min_value=0, max_value=10_000),
    y=st.integers(min_value=1, max_value=100),  # avoid division by 0
)
@settings(max_examples=500, deadline=200)
def test_div_mod_consistency(x, y):
    assume(y != 0)  # filter in addition to the bound; rejected samples
    q, r = divmod(x, y)
    assert q * y + r == x
    assert 0 <= r < y
```

Three things to note:

- **`@given`** defines the input space via composable strategies.
- **`assume`** filters invalid examples after generation (use sparingly — prefer refining the strategy).
- **`@settings`** adjusts the number of examples, deadline, database, profile.

---

## 3. The six canonical patterns (learn by heart)

### 3.1 Universal invariants

A property that must always hold, regardless of input.

```python
@given(st.lists(st.integers()))
def test_sort_preserves_length(xs):
    assert len(sorted(xs)) == len(xs)

@given(st.lists(st.integers()))
def test_sort_is_monotonic(xs):
    s = sorted(xs)
    assert all(s[i] <= s[i+1] for i in range(len(s) - 1))
```

### 3.2 Round-trip (encode/decode)

`decode(encode(x)) == x`. The most powerful for parsers, serializers, codecs.

```python
@given(st.dictionaries(st.text(), st.integers()))
def test_json_roundtrip(d):
    assert json.loads(json.dumps(d)) == d
```

This is exactly what revealed the Unicode/encoding bugs cited above. In your telecom context: `parse_sip_header(format_sip_header(h)) == h`, same for SDP, RTP, MGCP, etc.

### 3.3 Idempotence

`f(f(x)) == f(x)`. True for `sorted`, `normalize`, `dedupe`, `lower`, many operations idempotent by construction.

```python
@given(st.lists(st.integers()))
def test_sort_idempotent(xs):
    assert sorted(sorted(xs)) == sorted(xs)
```

Typical bug caught: a function "idempotent" that isn't on already-sorted inputs due to a side effect.

### 3.4 Metamorphic (relation between executions)

Invented by T.Y. Chen (1998). Instead of predicting the output for a given input, we relate the outputs of two executions.

```python
# "adding an element does not decrease the length"
@given(st.lists(st.integers()), st.integers())
def test_append_metamorphic(xs, x):
    assert len(xs + [x]) == len(xs) + 1

# "sort then filter = filter then sort"
@given(st.lists(st.integers()))
def test_sort_filter_commute(xs):
    keep = lambda v: v >= 0
    assert sorted(filter(keep, xs)) == list(filter(keep, sorted(xs)))
```

This is **the pattern to know when you can't compute the direct oracle**. Domain of application: ML/inference, numerical simulations, complex parsers, optimizers.

### 3.5 Alternative oracle (model-based)

Compare the tested implementation to a **simple known-correct model**, usually slower.

```python
def my_sort(xs):
    # fast implementation to test
    ...

@given(st.lists(st.integers()))
def test_sort_against_python(xs):
    assert my_sort(xs) == sorted(xs)
```

Powerful variant: abstract model (set, dict, list) to validate a complex data structure (skiplist, B-tree, trie).

### 3.6 Commutativity / associativity

```python
@given(st.integers(), st.integers())
def test_add_commutative(a, b):
    assert add(a, b) == add(b, a)

@given(st.integers(), st.integers(), st.integers())
def test_add_associative(a, b, c):
    assert add(add(a, b), c) == add(a, add(b, c))
```

Useful for: aggregations, structure merges, distributed reductions.

---

## 4. Strategies — the generation DSL

Strategies are half of PBT. Choosing poorly = either no bugs found (space too thin) or excessive slowness (space too large).

### Primitives

```python
st.integers()                          # any int (with bias toward edges)
st.integers(min_value=0, max_value=100)
st.floats(allow_nan=False, allow_infinity=False)
st.text()                              # any Unicode text (including surrogates)
st.text(alphabet=st.characters(whitelist_categories=("L", "N")))
st.binary()
st.booleans()
st.none()
st.datetimes(timezones=st.timezones())
st.uuids()
```

### Composition

```python
st.lists(st.integers(), min_size=1, max_size=10)
st.tuples(st.integers(), st.text())
st.dictionaries(keys=st.text(min_size=1), values=st.integers())
st.sets(st.integers())
st.one_of(st.integers(), st.text())    # union
st.fixed_dictionaries({                # typed dict key/value
    "id": st.uuids(),
    "name": st.text(min_size=1),
    "age": st.integers(min_value=0, max_value=150),
})
```

### `@composite` — building complex strategies

```python
from hypothesis.strategies import composite

@composite
def valid_sip_uri(draw):
    user = draw(st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=20))
    host = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=10))
    return f"sip:{user}@{host}.example.com"

@given(valid_sip_uri())
def test_sip_parser(uri):
    parsed = parse_sip_uri(uri)
    assert parsed.scheme == "sip"
```

### Recursive

```python
json_strategy = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=20,
)
```

### Mapping / filtering

```python
# transform
st.integers().map(lambda x: x * 2)

# filter (expensive — prefer a strategy that doesn't generate the invalid)
st.integers().filter(lambda x: x % 2 == 0)
```

**Golden rule**: prefer a strategy that directly generates the right space rather than filtering. `filter` is slow and can exhaust the generator ("too few examples found"). `assume()` has the same problem.

---

## 5. Stateful testing — the most powerful, least known

Classical PBT tests **functions**. Stateful PBT tests **sequences of operations** on a system that maintains state. This is where subtle bugs hide: state corruption, combined invariants, operation order.

### Canonical structure

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle, precondition
from hypothesis import strategies as st

class ShoppingCartMachine(RuleBasedStateMachine):
    """Test the cart via sequences of operations."""

    products = Bundle("products")

    def __init__(self):
        super().__init__()
        self.cart = Cart()
        self.model = {}  # simple oracle: dict product -> qty

    @rule(target=products, name=st.text(min_size=1, max_size=20), price=st.integers(min_value=0))
    def create_product(self, name, price):
        p = Product(name=name, price=price)
        return p

    @rule(product=products, qty=st.integers(min_value=1, max_value=10))
    def add(self, product, qty):
        self.cart.add(product, qty)
        self.model[product.id] = self.model.get(product.id, 0) + qty

    @rule(product=products)
    @precondition(lambda self: len(self.model) > 0)
    def remove(self, product):
        if product.id in self.model:
            self.cart.remove(product)
            del self.model[product.id]

    @invariant()
    def total_matches_model(self):
        expected = sum(p.price * q for p, q in self._lookup_model().items())
        assert self.cart.total() == expected

    @invariant()
    def no_negative_quantities(self):
        for item in self.cart.items():
            assert item.qty >= 0

TestCart = ShoppingCartMachine.TestCase   # pytest discovers it
```

Hypothesis will generate **sequences** of calls to `create_product`, `add`, `remove`, and verify `@invariant()` after each step. If a combination breaks the invariant, it shrinks the sequence to the shortest one that reveals the bug.

### Why it's devastating

- **State corruption sequences**: bugs that only appear after a specific chain of operations.
- **Combined invariants**: each operation is individually correct, but composition violates a property.
- **Subtle interaction bugs**: canonical Hypothesis example — "every heap prior to v7 is balanced, but v7 fails after merging".
- **Concurrency-like patterns**: without true concurrency, but with arbitrary order. PyCon 2024 benchmarks (cited by OneUptime): 92% of subtle race conditions missed by manual tests are caught by stateful.

### Direct application cases in your context

- **Wazo / Asterisk dialplan state**: call transitions (offer/answer, hold/resume, transfer, conference). Invariant: "an active call always has exactly two endpoints" — the kind of bug that appears after a reinvite + transfer + hold sequence.
- **Pyfreebilling routing tables**: adding/removing rates, lookups, modifications. Invariant: "every number has a calculable price" or "total billed = sum of CDRs".
- **SIP/RTP connections**: state transitions (Trying → Ringing → 200 OK → ACK → ...).
- **SBC session state**: INVITE/CANCEL/BYE patterns.

---

## 6. Hypothesis-specific: what you need to know beyond the basics

### Settings and profiles

```python
from hypothesis import settings, HealthCheck

settings.register_profile("ci", max_examples=1000, deadline=500)
settings.register_profile("dev", max_examples=20, deadline=100)
settings.register_profile("nightly", max_examples=10_000, deadline=2000)

# at the start of conftest.py
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
```

Best practice: three profiles (fast dev, medium CI, exhaustive nightly).

### Database

Hypothesis persists found counterexamples in `.hypothesis/examples/`. On the next run, these examples are re-tested first. Effect: automatic regression-testing of already-found bugs. **Commit if the team wants to share knowledge, `.gitignore` otherwise** — there are arguments both ways; current practice leans toward gitignore + shared CI via cache.

### `@example` — pin an example

```python
@given(st.integers())
@example(0)   # always test 0
@example(2**63 - 1)
def test_my_thing(n):
    ...
```

Useful for: historical regressions, known edge values, cases you want to document in the suite.

### `target()` — guide the search

```python
from hypothesis import target

@given(st.lists(st.integers()))
def test_perf(xs):
    t0 = time.perf_counter()
    do_work(xs)
    elapsed = time.perf_counter() - t0
    target(elapsed, label="elapsed")   # Hypothesis maximizes elapsed → finds worst case
    assert elapsed < 1.0
```

This is **objective-oriented fuzzing** built in. Particularly useful for performance bugs, regressions on degenerate cases.

### `find()` and `.example()` — manual exploration

```python
from hypothesis import find

# the smallest case that satisfies a condition
find(st.lists(st.integers()), lambda xs: sum(xs) > 100)
# → [101] or [1, 100], etc.

# a random example (debug only)
st.lists(st.integers()).example()
```

### `HealthCheck` warnings

Hypothesis displays useful warnings:
- `filter_too_much` → poorly scoped strategy, too much filtering.
- `too_slow` → an example exceeds deadline.
- `data_too_large` → examples larger than the limit.

Always listen to them — they signal a suboptimal strategy.

---

## 7. PBT + IA workflow (agentic PBT)

**Agentic PBT** (arxiv 2510.09907) and the Anthropic Red article (2026) converge on a 5–6 step workflow that the agent follows:

```
1. Code analysis        — introspection of the target module/function
2. Evidence gathering   — docstrings, examples, signatures, callers
3. Property inference   — invariants, round-trip, metamorphic, alternative oracle
4. Test synthesis       — writing the Hypothesis test
5. Execution + reflection — run + failure analysis, false-positive filtering
6. Bug reporting        — minimal reproducer + diagnosis
```

### Operational prompts

**Step 3 — Property inference** (the core):

```
You are given a Python function with its docstring and a few callers.
Propose 3–5 property-based test ideas. Each idea must:
- Cite the textual evidence (docstring sentence, type hint, caller usage)
  that justifies the property — NO speculative invariants.
- Be one of: invariant, round-trip, idempotence, metamorphic, model-based,
  algebraic (commute/assoc).
- Be expressible in Hypothesis with a clear strategy.

Output as a numbered list with: evidence | property statement | strategy sketch.
Stop. Wait for me to pick which one to implement.
```

**Step 5 — Reflection**:

```
A property failed with this counterexample. Before writing a bug report:
1. Re-read the property — is it actually claimed by the docs, or did I
   over-specify?
2. Is the counterexample at a boundary the docs explicitly exclude?
3. Is there exception-handling masking a different error?
4. Could the property be too strong (e.g., asserting strict equality
   on floats, or ordering on a set)?
Decide: real bug, weak property, or invalid assumption. Justify in 3 lines.
```

### Why PBT + LLM works particularly well

- LLMs are **excellent at proposing properties** from documentation and naming. Anthropic Red: *"language models excel at identifying semantic guarantees from context clues."*
- LLMs are **mediocre at choosing the correct one-off oracle** (arxiv 2602.07900). In PBT, the oracle is a **relation**, not a value — far less ambiguous for an LLM.
- The **reflection loop** filters false positives. Anthropic Red: on 50 manually reviewed reports, **56% were valid; the best-scored reports reached 81% validity**.

### Articulation with `tdd-skill/`

- `agent-discipline.md` §6 (oracle from spec, not code): PBT shifts the oracle from a value to a relation — mechanically mitigates the risk.
- `agent-discipline.md` §4 (no internal mocks): properties express themselves on observable outputs, not internal calls — converges.
- PBT is a **good task to delegate to AI**: strategy generation, enumeration of property candidates. But **validation of counterexamples** remains human (oracle problem persists on survivors).

---

## 8. Pitfalls — where PBT derails

### 8.1 Tautological properties

```python
# BAD — tests nothing
@given(st.integers())
def test_add_zero(x):
    assert add(x, 0) == x + 0   # true by construction of +
```

The oracle is the operation itself. This is the most frequent error. **Remedy**: the property must be derivable from the **spec**, not the tested code.

### 8.2 Properties too strong

```python
# BAD — float equality
@given(st.floats(), st.floats())
def test_add_commutative(a, b):
    assert a + b == b + a   # NaN + x ≠ x + NaN, and other subtleties
```

**Remedy**: `math.isclose`, exclude NaN/inf in the strategy (`allow_nan=False`), be explicit about domains.

### 8.3 Properties too complex

A property combining 4 operations becomes unreadable and shrinking becomes inefficient. **Remedy**: decompose into several small focused properties.

### 8.4 Excessive filtering

```python
# BAD — Hypothesis will give up
@given(st.integers())
def test_prime(n):
    assume(is_prime(n))   # 1 in ~ln(n); too rare
    ...
```

**Remedy**: dedicated strategy that directly generates the target space.

### 8.5 Ignoring shrinking / the counterexample

Shrinking is the **true product of PBT**. A dev who sees a failure and only looks at the error message without studying the minimal counterexample misses the point. **Remedy**: discipline in reading.

### 8.6 Slow tests

Too many examples × tight deadline → slow CI, temptation to lower `max_examples` → reduced effectiveness. **Remedy**: tiered profiles (dev/ci/nightly), parallelism via `pytest-xdist`, scoping to critical modules.

### 8.7 Pure functions only?

PBT works best on pure functions. Side effects (DB, network, files) remain **testable**, but with harder oracles and heavier setup. **Remedy**: isolate pure logic (parsing, computation, transformation) from I/O; test each layer with the appropriate tool.

### 8.8 Stateful explodes

A state machine with 20 rules generates a huge, slow space. **Remedy**: start small (3–5 rules), `precondition` to limit the tree, tiered profiles.

---

## 9. Concrete use cases — telecom / VoIP (your context)

Telecom domains where PBT has strong ROI, in order of obviousness:

### 9.1 Protocol parsers (SIP, SDP, RTP, MGCP)

```python
@given(valid_sip_message())
def test_sip_roundtrip(msg_text):
    parsed = SipMessage.parse(msg_text)
    assert SipMessage.parse(str(parsed)) == parsed

@given(valid_sdp_body())
def test_sdp_codec_extraction_monotone(sdp):
    # If I remove an m=audio block, codec count can only decrease
    parsed = parse_sdp(sdp)
    reduced = remove_first_audio_stream(sdp)
    assert codec_count(parse_sdp(reduced)) <= codec_count(parsed)
```

The MDPI 2025 paper *Property-Based Testing for Cybersecurity: Towards Automated Validation of Security Protocols* covers exactly this domain.

### 9.2 Routing tables / dial plans

Invariants:
- Every number has at most one active route.
- The cost of a call ≥ the minimum cost of matched prefixes.
- Adding a more specific route cannot increase the cost for an already-covered number.

```python
@given(routing_table_strategy(), phone_number_strategy())
def test_more_specific_route_never_increases_cost(table, number):
    base_cost = lookup(table, number).cost
    refined = add_more_specific_route(table, number)
    assert lookup(refined, number).cost <= base_cost
```

### 9.3 Codec / DSP / encoding

Round-trip on encode/decode (G711, G722, Opus, etc.) with numeric tolerance. PBT finds bugs at boundaries (silence, peaks, NaN).

### 9.4 Stateful: SIP session

`RuleBasedStateMachine` modeling a SIP dialog: INVITE / 100 / 180 / 200 / ACK / reINVITE / BYE / CANCEL with invariants "single active dialog", "stable Call-ID", "monotone CSeq".

This is where PBT vastly beats manual tests — the space of sequences is too large to enumerate by hand.

### 9.5 Billing / CDR

- Invariant: `sum(legs.duration) == call.duration` (to epsilon).
- Metamorphic: recalculating a CDR with a rate divided by 2 must produce a cost divided by 2.
- Idempotence: re-rating a CDR yields the same cost.

---

## 10. Cross-language equivalents

| Language | Tool | Maturity | Notes |
|---|---|---|---|
| Python | **Hypothesis** | Excellent | De facto standard. Stateful, sophisticated shrinking, database. |
| TS / JS | **fast-check** | Excellent | API very close to Hypothesis. Stateful via `commands`. Good shrinking. |
| Go | **rapid** | Very good | Maintained, modern API, solid shrinking. Recommended. |
| Go | **gopter** | Stable | Older, more verbose. |
| Go | `testing/quick` (stdlib) | Limited | No shrinking, few strategies. Avoid for serious use. |
| Rust | **proptest** | Excellent | Standard. Stateful via `proptest-state-machine`. |
| Rust | **quickcheck** | Stable | Simpler, no sophisticated shrinking. |
| Java | **jqwik**, **junit-quickcheck** | Stable | jqwik more modern. |
| Haskell | **QuickCheck** | The original (1999) | Still the reference. |
| Erlang | **PropEr**, **QuickCheck (commercial)** | Very mature | Ericsson and the Erlang telecom ecosystem rely on it. |
| Scala | **ScalaCheck** | Stable | |
| Kotlin | **Kotest property** | Good | |

### fast-check (TS) — short example

```typescript
import * as fc from 'fast-check';

test('reverse is involution', () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (xs) => {
      expect(reverse(reverse(xs))).toEqual(xs);
    }),
  );
});
```

API nearly identical to Hypothesis. Stateful via `fc.commands([...])`.

### rapid (Go) — short example

```go
import (
    "pgregory.net/rapid"
    "testing"
)

func TestReverseInvolution(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        xs := rapid.SliceOf(rapid.Int()).Draw(t, "xs")
        if !reflect.DeepEqual(reverse(reverse(xs)), xs) {
            t.Fatalf("not involution")
        }
    })
}
```

---

## 11. Recommended practical stack

### If you start today (Python)

```
1. pip install hypothesis
2. Identify 2–3 pure functions / parsers / computations in the project
3. Write ONE property per function (round-trip or invariant), see what emerges
4. If Hypothesis finds a bug: you've won, continue
5. If nothing: refine the strategies (too-thin space is error #1)
6. Add a CI profile (max_examples=500, deadline=500ms)
7. Later: a RuleBasedStateMachine on the most stateful module
```

### Checklist per property

```
[ ] The property is derivable from the spec, not the tested code
[ ] The strategy covers the target space without excess filter/assume
[ ] The property is ONE thing (not a combo of 3 invariants)
[ ] The oracle doesn't depend on a fragile comparison (float equality, set order)
[ ] At least one @example documents a known case / regression
[ ] The test runs in < 1s at max_examples=100 (else profile)
[ ] If a counterexample is found: commit the @example for regression
```

### Progressive adoption strategy

1. **Month 1**: PBT on parsers and pure calculation functions. Low cost, immediate ROI.
2. **Month 2**: Metamorphic on optimizers, aggregations, normalizations.
3. **Month 3+**: Stateful on stateful components (sessions, queues, FSM).
4. **Continuous**: integrate agentic PBT (Claude / other agent) on critical modules in periodic review, à la NumPy/AWS PowerTools.

---

## 12. Honest limits

- **Bootstrapping effort** non-trivial. Learning to formulate properties is a skill. Allow 2–3 weeks for a team to internalize it.
- **No magic on poorly designed code**. If layers are mixed (logic + I/O), PBT struggles.
- **CPU cost**: a PBT test can take 10×–100× a unit test. Tiered profiles mandatory.
- **False positives in agentic**: ~44% per Anthropic Red 2026. Reflection loop essential.
- **No replacement** for example-based tests for targeted regressions and example documentation.
- **Heavy-I/O domains** (UI, databases, network): PBT is limited there. Stateful helps but isn't enough — complementary tools needed (E2E, integration).

---

## 13. Articulation with the rest of the folder

| Doc | Relevant section | Link |
|---|---|---|
| Blog series article 1: "AI didn't kill tests, it made them indispensable" | Workflow and IA, Oracle problem | PBT mitigates the oracle problem by transforming the oracle from a value to a relation |
| `tdd-skill/SKILL.md` | §Roles, §Spec-first | Properties are the spec's formalization — a human writes the property, AI proposes variants |
| `tdd-skill/agent-discipline.md` | §6 (oracle from spec, not code) | PBT is the concrete tool that makes this rule actionable |
| `test-quality-tools-survey.md` | §4 Robustness | This deep-dive expands the PBT section from the survey |
| `tdd-skill/hooks-python.md` | §4 Mutation | Mutation + PBT are complementary: mutation measures assertion strength; PBT amplifies it by exploring the space |

---

## Sources

### Academic

- Chen, T.Y. et al. (1998). *Metamorphic testing: A new approach for generating next test cases*. Technical Report.
- MacIver, D., Hatfield-Dodds, Z. (2019). *Hypothesis: A new approach to property-based testing*. JOSS. https://www.researchgate.net/publication/337429879
- *An Empirical Evaluation of Property-Based Testing in Python*. OOPSLA 2025. https://cseweb.ucsd.edu/~mcoblenz/assets/pdf/OOPSLA_2025_PBT.pdf
- *Agentic Property-Based Testing: Finding Bugs Across the Python Ecosystem*. arxiv 2510.09907 (2025). https://arxiv.org/html/2510.09907v1
- *Use Property-Based Testing to Bridge LLM Code Generation and Validation*. arxiv 2506.18315 (2025). https://arxiv.org/pdf/2506.18315
- *Property-Based Testing for Cybersecurity: Towards Automated Validation of Security Protocols*. MDPI 2025. https://www.mdpi.com/2073-431X/14/5/179
- *Property-Based Testing in Practice* — Goldstein, H. https://andrewhead.info/assets/pdf/pbt-in-practice.pdf
- *Metamorphic Testing: A Simple Approach to Alleviate the Oracle Problem*. IEEE. https://ieeexplore.ieee.org/document/5569943

### Industry / serious blogs

- Anthropic Red (2026). *Property-Based Testing with Claude*. https://red.anthropic.com/2026/property-based-testing/
- Hypothesis Works. *Rule Based Stateful Testing*. https://hypothesis.works/articles/rule-based-stateful-testing/
- Hypothesis Works. *Evolving toward property-based testing*. https://hypothesis.works/articles/incremental-property-based-testing/

### Tool documentation

- **Hypothesis** — https://hypothesis.readthedocs.io/
- **fast-check** — https://fast-check.dev/
- **rapid (Go)** — https://github.com/flyingmutant/rapid
- **proptest (Rust)** — https://github.com/proptest-rs/proptest
- **PropEr (Erlang)** — https://propertesting.com/
