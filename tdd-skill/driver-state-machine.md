# Driver State Machine — the red-green-refactor loop as an explicit FSM

> **Status: reference / blueprint, not shipped machinery.**
> In **supervised** work the recommended enforcement is the commit-time gate
> `scripts/tdd-verify-cycle.sh` ([hooks-python.md](hooks-python.md) §0). This
> document exists because a state machine is the natural shape of the loop, and
> writing it down (a) makes the intended control flow precise where [SKILL.md](SKILL.md)
> only describes it in prose, and (b) is the blueprint for a future **autonomous**
> driver. Do not build the machinery until you actually go autonomous — until
> then it is an abstraction ahead of its need.

## Why a state machine at all

The hook *proves* one cycle **after the fact**: at commit time it checks the end
state is reconstructible as red→green. It does not stop an agent from writing
code first — it just rejects the commit, costing rework.

A driver *owns the control flow*: it chooses the next transition by observing
test results, so RED-before-GREEN becomes a property of the driver, not of the
agent's goodwill. The strongest consequence is structural: **illegal states are
unrepresentable.** "Never refactor while red" is not a rule you check — there is
simply no edge from RED to REFACTOR.

## Transition table

| State | Event / guard | → State | What the guard enforces |
|---|---|---|---|
| PICK | plan empty | DONE | — |
| PICK | next behavior | RED | — |
| RED | test written, run **fails** | APPROVE | [agent-discipline.md](agent-discipline.md) §2: run **passes** ⇒ HALT (vacuous / pre-existing behavior) |
| APPROVE | reviewer approves | GREEN | supervised blocking gate: spec-as-test validated before any code |
| APPROVE | reviewer rejects | RED | rewrite the test — **code untouched** (§1) |
| APPROVE | reviewer aborts | HALTED | §10 |
| GREEN | code written, run **passes** | REFACTOR | bounded code retries then HALT; **test never edited** to reach green |
| GREEN | retries exhausted | HALTED | do not touch the test — surface to human |
| REFACTOR | full suite stays green | PICK | (a real driver commits here) |
| REFACTOR | suite goes red | HALTED | revert and stop |

Note there is **no RED→REFACTOR edge**: refactoring while red is not forbidden by
a check, it is absent from the graph.

## Where the guarantee actually comes from — and its limit

Two orthogonal properties are both required:

1. **Structural ordering (the edges).** The FSM makes the sequence a property of
   the graph. This is what the table above buys.
2. **Exclusivity of the path (the ports).** The FSM only governs actions that go
   *through it*. Its side effects flow through a small set of ports —
   `write_test`, `write_code`, `refactor`, `run`, `human_gate`. If the actor that
   implements `write_code` can also edit the test file, or can bypass the driver
   and edit the tree directly, the FSM governs nothing.

> The FSM makes ordering structural; **[hooks-python.md](hooks-python.md) §6
> role-split makes the path exclusive** (test-author session vs implementer
> session, each with restricted write paths). Neither alone suffices. The state
> machine does not eliminate the "exclusive path" requirement named elsewhere in
> this skill — it concentrates it into the wiring of the ports.

## Two realizations of the same table

### Supervised — driven by the main agent, turn by turn

`APPROVE` is a **blocking, synchronous** gate. The driver stops, asks the human,
resumes on the next turn. This is why supervised TDD does **not** fit a
fire-and-forget background workflow runner: such a runner cannot pause mid-run
for human input. Supervised = the transition table honored by the main agent,
the gate = a turn boundary. For this mode the hook (§0) already delivers the
enforcement; the FSM is documentation of intent.

### Autonomous — the same table as a workflow script

Transplant the table into a deterministic orchestrator:

```
pipeline(plan,
  redStage,        // agent writes test; assert run() FAILS, else throw (drop item)
  approveStage,    // panel of adversarial verifiers: "refute that this is a real
                   //   failing spec"; majority-refute ⇒ throw
  greenStage,      // agent writes code; bounded while-retry until run() PASSES
  refactorStage)   // agent refactors; assert full suite green, else throw
```

- Guards become assertions between stages that `throw` on violation (the item
  drops out; nothing advances past a failed guard).
- The bounded retry is a `while` inside `greenStage`.
- The human `APPROVE` gate is replaced by an **adversarial verifier panel** —
  independent agents prompted to *refute* that the RED test is a genuine
  behavioral failure. This is the autonomous stand-in for human review.
- Role-split is two agent profiles (test-author vs implementer) with disjoint
  write permissions — the exclusivity property above, mechanized.

## When to build it

- **Supervised interactive work** (the default): don't. Hook §0 +
  [agent-discipline.md](agent-discipline.md) cover it. Building the driver here
  is over-engineering.
- **Autonomous / semi-autonomous runs**: build it — but only together with §6.
  Its marginal value over the hook exists only once no human is in the loop to
  reject a code-first cycle before it wastes work.

## See also

- [hooks-python.md](hooks-python.md) §0 — the commit-time RED→GREEN proof (supervised default).
- [hooks-python.md](hooks-python.md) §6 — role-split (the exclusivity property).
- [agent-discipline.md](agent-discipline.md) — the hard rules the guards encode.
- [SKILL.md](SKILL.md) — the workflow this table formalizes.
