# Architecture — the stack as built

The manifesto (`library/originals/MANIFESTO-persistent-cognitive-ecology.md`)
specifies the law; this document maps the law onto this repository, layer by
layer, marking what is real code today and what is deliberately still
unbuilt.

```
        WORLD            L2 world.py       — typed objects, SQLite, memory graduation
          ↑
      ATTENTION          attention.py      — market / central / hybrid policies
          ↑
       TENSION           tension.py        — expectation vs reality, pressure grows with age
          ↑
        WHY              why/ (kernel)     — the conservation law, v0.2 semantics
          ↑
      IDENTITY           identity.py       — persistent preference as a stable attractor
```

## Layer map

| Layer | Manifesto role | Module | Status | Notes |
|---|---|---|---|---|
| L0 | Runtime: processes, ticks, budgets | `ecology.runtime` | **built** | processes bid; funded ones tick; starved ones wait — never killed |
| L1 | Event Fabric: tiny messages, publish-only | `ecology.events` | **built** | synchronous pub/sub, bounded history = the observation stream |
| L2 | World State Graph: typed, addressable objects | `ecology.world` | **built** | SQLite; memory maturity ladder (observation→episode→pattern→routine→policy) |
| L3 | Simulated Futures: budgeted what-ifs | `ecology.sim` | **built (minimal)** | priority = novelty × importance × uncertainty; scenarios are pure functions |
| L4 | Script Ecology: deterministic skills | `ecology.scripts` | **built** | trigger/conditions/cost/utility; candidate→active→retired by learned utility |
| L5 | Agent Organisms: scripts + memory + goals | `ecology.demo` (processes) | **partial** | the tiny MUD's five processes are the first organisms |
| L6 | WHY: justification as conservation law | `ecology.why` | **built (v0.2 port)** | golden-corpus-equivalent to the Rust reference; drives the scheduler via `JustificationWatch` |
| — | Attention economy | `ecology.attention` | **built** | manifesto formula; hybrid policy = "markets locally, governance globally" |
| — | Tension field | `ecology.tension` | **built** | pressure compounds with age; feeds briefings and bids |
| L7 | Sleep: consolidation | `ecology.sleep` | **built (mechanical v1)** | observations→episodes→patterns→candidate scripts→replay validation→promotion; zero LLMs |
| — | Identity | `ecology.identity` | **built (minimal)** | value distribution as attractor; stability measurable |
| — | Morning briefing | `ecology.briefing` | **built (minimal)** | changed things, urgent tensions, retirement recommendations, necessity census |
| — | LLM teachers | `ecology.llm`, `ecology.research` | **built** | DeepInfra (7 models), TypeSafe Jev decisions, cache-first protocol, cost ledger; MiniMax blocked (key rejected, see PROVIDERS) |
| — | Developmental biology (cell differentiation) | — | unbuilt | the sleeper should spawn specialist cells when patterns justify them |
| — | Exocortex evolution (self-writing routines via teachers) | — | unbuilt | teachers propose better handlers for compiled routines |

## The two WHY bodies

The Rust [`why`](https://github.com/SuperInstance/why) stays the reference
implementation and the CI flashlight: stateless, git-as-store, exit codes.
This repo's `ecology.why` is the same law as a pure in-process function,
consulted by the scheduler every tick (`JustificationWatch` multiplies bids
by justification weight: alive 1.0, questionable 0.25, dead 0.0). Both are
pinned to the same golden corpus, so they cannot drift apart silently.

## Semantic note: "questionable" vs "dead"

The manifesto says dependents of a dying root become *questionable, not
deleted*. The kernel (correctly) distinguishes two strengths of that
statement:

- **root attested dead** → explicit dependents are `dead` (certainty; the
  conservation law fully withdrawn; removal is justified);
- **root's liveness unknown** (attestation removed, stale past grace, or
  reached only via inferred edges) → dependents are `unknown` =
  *questionable*: they keep running at a discounted bid (0.25), starving
  only under contention.

Both behaviors are pinned by tests in `tests/test_runtime.py`.

## The experiment

`ecology week` (see `examples/week_in_a_box.py`) is the manifesto's core
question made executable: the smallest persistent world that improves itself
while nobody is watching. Current result (seed 42, 7 days × 30 ticks):
sleep compiled 4 routines from 332 observations, 4 were promoted by their
own success, 5 seeded scripts retired by their own utility, killing a root
goal on day 4 broke 8 justifications without deleting anything, and the
script ecology accumulated 10.88 learned utility — with zero LLM calls.
