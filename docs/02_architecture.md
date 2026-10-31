# Architecture

## The one-sentence version

**cognitive-ecology is a Python kernel for building agents that persist
like organisms: a body with a heartbeat, a conserved purpose, an economy
of attention, a world they inhabit and remember — where models are
citizens, not kings.**

## Read this first (five misconceptions, fixed upfront)

These are the five things people get wrong on first contact. Each fix is
worth internalizing before reading further.

1. **"L0–L8 is a call stack / pipeline."** No. L0–L8 are not a call stack
   or an OSI-style hierarchy — L0 is a tick scheduler that never calls a
   model, and each layer is a constraint or capability evaluated *every
   tick*. Higher layers do not invoke lower ones; the runtime rotates
   through all of them on every heartbeat.
2. **"The WHY conservation law means WHY nodes are immutable."** No. A
   WHY node is never *deleted* from the log; it absolutely *can* be
   killed, questioned, parked and revived — its history and causal links
   always remain.
3. **"Attention is a weighted score."** No. It is a multiplicative
   market: `urgency × justification × opportunity × novelty ×
   expected_value`. Any factor of zero vetoes the bid entirely — a huge
   urgency can never buy its way past a dead purpose.
4. **"Anti-RAG means no retrieval, or a knowledge graph with vector
   search."** No. Anti-RAG means recall is attention-guided *traversal*
   of a typed graph whose nodes carry biographies (`born`, `last_seen`,
   `weight`). There is no embedding index; relevance comes from
   co-occurrence, repetition, recency and current attention.
5. **"Script ecology is genetic programming."** No. Scripts are small,
   *parameterized* behaviors drawn from a safe, audited action library
   (for LLM-proposed ones). Mutation jitters parameters; nothing evolves
   arbitrary code; and dead scripts are *recorded*, never garbage-collected.

## The stack

```
            ┌────────────────────────────────────────────┐
   L8       │  Sleep & Dreams — replay, prune, mutate     │   sleep.py
            ├────────────────────────────────────────────┤
   L7       │  Identity — the slowly-drifting self        │   identity.py
            ├────────────────────────────────────────────┤
   L6       │  WHY — purpose, conserved forever    ★      │   why.py
            ├────────────────────────────────────────────┤
   L5       │  Attention Market + Executive               │   attention.py
            │                                             │   executive.py
            ├────────────────────────────────────────────┤
   L4       │  Script Ecology — agents are populations    │   scripts.py
            ├────────────────────────────────────────────┤
   L3       │  Memory — events consolidate into world     │   memory.py
            ├────────────────────────────────────────────┤
   L2       │  World Graph — anti-RAG knowledge           │   graph.py
            ├────────────────────────────────────────────┤
   L1       │  Events — MIDI-style, ~100 bytes            │   events.py
            ├────────────────────────────────────────────┤
   L0       │  Runtime — process, not agent (zero-LLM)    │   runtime.py
            └────────────────────────────────────────────┘
                cross-cutting: tension.py (drives)
                               simulations.py (rollouts)
                               agents/ (models as citizens)
```

L6 is called *the crown* deliberately: it is the layer the whole design
defends. Everything below it exists so that purpose can be enforced, and
everything above it exists so that purpose can be *held* coherently over
time.

## One tick, in order

`Runtime.tick()` is the organism's heartbeat. Every tick does exactly
this, in this order (see `runtime.py`):

1. **Drives grow** — each tension rises by its growth rate (`tension.py`).
2. **The heartbeat question** — every component must answer
   `why_should_this_run()`. A broken WHY chain (any ancestor DEAD or
   UNKNOWN) means no bids this tick — but no deletion, ever.
3. **Bids** — eligible components submit attention bids for their
   scripts (the five factors are computed live).
4. **The market clears** — top-k bids win; resource conflicts are
   resolved (the weaker bid *yields*); vetoed bids (attention 0) never
   clear, even in an empty market.
5. **Winners act** — their events are cause-chained to the DECISION
   event that authorized them, so every effect has a walkable chain.
6. **Ecology bookkeeping** — starvation counters; scripts that never win
   and never fire eventually die *into the necrology*.
7. **Memory consolidates** — this tick's events fold into the world
   graph (Hebbian co-occurrence, repetition, recency).
8. **Decay** — unseen graph nodes fade toward a floor. Never deleted.
9. **Sleep check** — if nothing ran for `idle_window` ticks: replay
   (boosted consolidation), prune (harsh starvation death), dream
   (parameter mutations).
10. **Conservation audit** — every 25 ticks the WHY tree is audited;
    a violation raises immediately. The law is enforced, not hoped for.

## Design decisions and their reasons

| Decision | Reason |
|---|---|
| Process, not agent (L0) | The runtime is a *body* — a tick loop that never calls a model. Anything that wants to act must join as a component and survive the same gates as everything else. |
| Ticks, not wall-clock | Reproducibility. The same seed + the same code = the same life. Time in the organism is *ticks*, and every event carries one. |
| MIDI-style events (~100 bytes) | Small, immutable, append-only events keep an auditable causal history at negligible cost, and keep telemetry greppable. |
| Anti-RAG world graph | Retrieval-by-similarity gives you *documents like this one*; traversal gives you *what was going on around this*. Memory needs the second. Nodes carry biographies; forgetting is fading (decay to a floor), never erasure. |
| Scripts compete; agents are populations | A monolithic agent prompt is unmanageable and unkillable. A population of small scripts with track records can starve, die (recorded!), mutate, and be audited one behavior at a time. |
| Multiplicative attention | The factors are vetoes, not bonuses. Urgency without justification is a panic attack; justification without opportunity is a daydream. Only the product of all five deserves budget. |
| WHY is conserved | Agents die when their purpose is deletable. Conserved purpose (never deleted, always auditable, revivable) is the difference between a tool that *has* goals and an organism that *holds* them. |
| Models are citizens | An LLM that can do anything is an unaccountable monarch. An LLM that proposes parameterized scripts from an audited action library is a productive citizen under the same laws as a foraging script. |
| Behavior in code, history in files | `save()`/`load()` serialize everything *except* closures — your scripts are re-declared in code and `adopt()` their saved track records. This split is why restarts, deploys and crashes are survivable. |

## Failure modes, by design

How the organism degrades under stress — and why each degradation is a
feature:

- **Root WHY killed** → nothing runs, nothing is deleted; everything is
  QUESTIONABLE (UNKNOWN), revivable with evidence. (`why.py`)
- **A drive's growth too high** → the organism becomes obsessed with
  relieving it. Check the diet (growth rates) before blaming the market.
  (`tension.py`)
- **A script keeps failing** → its expected_value falls, it stops winning,
  starves, dies — with its record. No punishment logic needed; economics.
- **Nothing is worth doing** → the market clears nothing (veto law),
  idleness accumulates, the organism sleeps: replay, prune, dream.
- **An LLM proposes garbage** → proposals are dropped (fail-soft), its
  accept-rate EMA decays, its attention bid weakens: it loses the
  market's ear. (`agents/orchestrator.py`)
- **Somebody edits history** → the identity commitment hash chain breaks;
  `verify()` returns False. (`identity.py`)

## What this is not

- Not an orchestration framework (no DAGs, no workflow YAML).
- Not a chat framework (no conversation management; build those on top).
- Not a vector database replacement for search-heavy RAG — it is a
  *memory* substrate; if you need corpus search, keep your search and put
  results *into* the world graph as nodes.
- Not a multi-agent communication protocol — one organism, many scripts.
  Multi-organism societies are an open question (see OPEN_QUESTIONS.md).
