# cognitive-ecology

**A persistent cognitive ecology: a world of long-lived processes where every
asset must continuously answer — *why do you still deserve energy?***

This repo grows directly out of the [`why`](https://github.com/SuperInstance/why)
project (justification reachability, Rust). `why` answered the question for
files and CI gates. This repo answers it for a *living system*: the WHY graph
becomes the conservation law that governs attention, memory, scripts, and
sleep — not a subsystem, the law the whole organism runs under.

> Existing systems maintain truth. They do not maintain necessity.
> Nothing should survive without a live reason.

## The Four Laws

1. **Time is the substrate.** Nothing is event-driven internally; events
   perturb ongoing processes. The world exists before the player logs in.
2. **Attention is the scarce resource.** Not compute. Every process bids for
   budget; the system is an economy, not a hierarchy.
3. **Why precedes memory.** Every asset — memory, project, routine, agent,
   goal — requires a justification chain. When a root dies, dependents become
   *questionable*, not deleted.
4. **LLMs are teachers, not workers.** The runtime must mostly work without
   them. Models edit the organism; they do not impersonate it.

## The stack — as built

| Layer | Module | Status |
|---|---|---|
| L0 Runtime (processes, ticks, budgets) | `ecology.runtime` | built |
| L1 Event Fabric (tiny messages, publish-only) | `ecology.events` | built |
| L2 World State Graph (typed objects, SQLite) | `ecology.world` | built |
| L3 Simulated Futures (budgeted, priority-gated) | `ecology.sim` | built (minimal) |
| L4 Script Ecology (candidate→active→retired) | `ecology.scripts` | built |
| L6 **WHY kernel** (v0.2 semantics) | `ecology.why` | **built — golden-corpus-equivalent to the Rust reference** |
| Attention economy (market/central/hybrid) | `ecology.attention` | built |
| Tension field (prediction error compounds) | `ecology.tension` | built |
| Sleep (mechanical consolidation, zero LLMs) | `ecology.sleep` | built (v1) |
| Identity (persistent preference attractor) | `ecology.identity` | built (minimal) |
| Morning briefing | `ecology.briefing` | built (minimal) |
| LLM teachers (7-model panel + Jev decisions) | `ecology.llm`, `ecology.research` | built |
| Developmental biology / exocortex evolution | — | next |

Full map with semantics notes: `docs/ARCHITECTURE.md`.

## Quickstart

```bash
pip install -e .[dev]
pytest                     # 99 tests, including the 15 golden corpus pairs
ecology week               # the manifesto's core experiment, live
ecology check graph.txt --alive att.txt   # WHY flashlight, Rust-CLI compatible
ecology panel --topic "..." --context doc.md --rounds 2   # live multi-model round
ecology usage              # provider cost report
```

## The week in a box

The manifesto's core question made executable — *the smallest persistent
world that can improve itself while nobody is watching*:

```
observations compiled into routines by sleep: 4 scripts born, 332 observations handled
scripts promoted to active: 4 (cpu, disk, net, anomaly routines)
scripts retired by their own utility: 5
tensions raised (novelty encountered): 8
justifications broken: 8        <- a root goal killed on day 4; nothing deleted
total learned utility: 10.88    <- with ZERO LLM calls
```

## The knowledge library

`library/` holds the cumulative record: the original manifesto, the external
audit this kernel inherits its fixes from, provider research, the crown-question
reflection, the open-questions ledger (all ten manifesto questions now have
probes or running code), and the live panel rounds — every turn a receipt
with provider, model, latency, tokens, cached tokens, and cost.

- `001` — *Is WHY truly the conservation law?* (7 models + jev gates, $0.064)
- `002` — *Does week-in-a-box support or falsify the hypothesis?* ($0.050)
- `003` — *Devil's-advocate loop* (Seed-2.0-mini iterating on itself, jev-steered, $0.002)

## Process as product

`docs/JOURNAL.md` is the build log (what failed and what it taught),
`docs/PROCESS.md` the operating manual, `docs/ADRs/` the decisions with
reversal conditions, `docs/PROVIDERS.md` observed provider behavior
(including the MiniMax key outage, documented honestly).

## Lineage

1. A 24k-line conversation: compiler fork → semantic CRDT → intent compiler → **why**.
2. `why` v0.1 → external audit → v0.2 (format spec, mortality, coverage).
3. **This repo**: WHY as the conservation law of a persistent cognitive ecology.

## Status

v0.1.0 — kernel port verified against the golden corpus; all ecology layers
built and tested; three live panel rounds in the library; the experiment
running. The organism grows layer by layer; every round is documented.
