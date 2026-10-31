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

## The stack

| Layer | Law / role | Module | Status |
|---|---|---|---|
| L0 Runtime | long-lived processes, ticks, budgets | `ecology.runtime` | planned |
| L1 Event Fabric | tiny typed messages, publish-only | `ecology.events` | planned |
| L2 World State Graph | typed, addressable objects (the MUD) | `ecology.world` | planned |
| L3 Simulated Futures | budgeted scenario projection | `ecology.sim` | planned |
| L4 Script Ecology | deterministic skills with cost/utility | `ecology.scripts` | planned |
| L6 **WHY graph** | **justification as conservation law** | `ecology.why` | **ported, 39 tests green** |
| Attention economy | market + governance hybrid | `ecology.attention` | planned |
| Sleep | consolidation: observation → routine | `ecology.sleep` | planned |
| LLM teachers | multi-provider panel (decision models!) | `ecology.llm` | planned |

## The WHY kernel (done first, deliberately)

`ecology.why` is a faithful Python port of
[why-core v0.2](https://github.com/SuperInstance/why) — same two-file format,
same four statuses, same 15-pair golden corpus (copied verbatim into
`tests/corpus/`), including both external-audit fixes: explicit-only liveness
and full-depth deadness propagation.

```text
graph.txt                          att.txt
role:analyst -> project:active     project:active alive 2024-01-01 casey
workflow:deploy -> project:active (inferred)
```

- `role:analyst` → **alive** (explicit path to a live root)
- `workflow:deploy` → **unknown** (inferred edges are candidates, never verdicts)
- if `project:active` dies → `role:analyst` → **dead** at any depth

`unknown` never fails a build; `dead` always does. Anything that can silently
convert dead into unknown is the dangerous direction and gets golden pairs
first.

```bash
pip install -e .[dev]
pytest                      # 39 tests, 15 golden pairs vs the Rust reference
```

## Why Python here, Rust there

The Rust `why` stays the reference CLI: a stateless flashlight, git-as-store,
exit codes for CI. The ecology needs WHY *in-process*, consulted every tick
by the scheduler — a pure function call, not a subprocess. Two bodies, one
law, one corpus keeping them honest.

## Repository map

- `src/ecology/why/` — the justification kernel (port complete)
- `library/` — the knowledge library: originals, research, discussion rounds,
  reflections, open questions (grows every round)
- `docs/` — manifesto, architecture, ADRs, journal (the process is a product)
- `tests/corpus/` — the golden equivalence pairs shared with the Rust repo

## Lineage

1. A 24k-line conversation: compiler fork → semantic CRDT → intent compiler →
   **why** (see `library/originals/` for the digests).
2. `why` v0.1 → external audit → v0.2 (format spec, mortality, coverage).
3. **This repo**: WHY as the conservation law of a persistent cognitive
   ecology — the architecture in `docs/MANIFESTO.md`.

## Status

v0.1.0 — kernel port complete and verified against the golden corpus. The
organism grows layer by layer; every round is documented in `docs/JOURNAL.md`.
