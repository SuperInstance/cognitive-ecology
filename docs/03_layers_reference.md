# Layers Reference

One page per layer: purpose, API, invariants, gotchas. File links point
at the source of truth — every module docstring carries the same
information with more context.

---

## L0 — Runtime (`src/cognitive_ecology/runtime.py`)

**Purpose:** the organism's body. Advances a clock, wires the organs
together, and enforces the two laws (nothing runs without a living WHY;
nothing is ever deleted). Never calls a model.

```python
rt = Runtime(seed=7, top_k=3, idle_window=5)
rt.declare_why("statement"[, parent, node_id])   # helper over why.declare
rt.register(component)                            # WHY node must exist
reports = rt.run(100, on_tick=my_callback)        # list[TickReport]
rt.save("runs/x"); rt2 = Runtime.load("runs/x", attach=fn)
```

**Key objects**

| Object | What it is |
|---|---|
| `Runtime` | the body: bus, why, graph, tensions, market, executive, ecology, memory, sleeper, identity |
| `WorldSnapshot` | the per-tick view handed to components (`tick`, `why`, `graph`, `tensions`, `ecology`, `emit()`, `recent()`, `novelty()`, `digest()`) |
| `Component` (Protocol) | anything with `id`, `why_node`, `bid(ctx)`, `act(ctx, label)` |
| `TickReport` | per-tick telemetry: `ran`, `yielded`, `starved`, `slept`, `events`, `tensions`, `conservation_ok` |

**Invariants:** a component referencing an unknown WHY node cannot be
registered (hard error). A misbehaving component is contained, never
fatal: a raising `bid()`/`act()` — or a bid returning junk — is
recorded as an `ERROR` event (with the reason), the tick goes on, and
the broken component starves on its own economics. A failed action's
`Outcome.note` reaches the log as an `ERROR` event, so on-call can see
*why*, not just *that*. The body survives its organs.

**Persistence (rounds 20a + 20b):** `save()` is atomic (temp + rename —
a torn write cannot come from us) and append-mode for events (each save
appends only the delta; the file is never rewritten whole). The state
records an event chain head and a watermark; `load()` verifies at the
door — corrupt JSON, a tampered event log (any edit changes the fold),
an interrupted save (watermark mismatch), or an edited WHY state (the
conservation receipt is recomputed, never trusted) all raise by name
instead of booting a silently-wrong organism. For bounded retention,
`rt.compact_events(path, keep=N)` truncates the log to the most recent
N events under a receipt — only after a full snapshot proves the state
first — with the dropped prefix folded into an anchor the door can
verify; a compacted life is bit-identical to an un-compacted twin
(pinned).

**Gotchas:** `run()` is not resumed automatically across processes —
`save()`/`load()` is the persistence path; `attach()` must re-register
components in code and call `ecology.adopt()` for script stats.

---

## L1 — Events (`events.py`)

**Purpose:** the nervous system. MIDI-inspired: tiny, immutable,
append-only, causally chained.

```python
bus.emit(EventKind.STATE, ("berry:1", {"food": 0}), src="critter",
         ts=t, cause=decision_seq)      # -> Event (with .seq)
bus.subscribe(fn, kinds=[EventKind.WHY])  # best-effort fan-out
bus.window(10); bus.since(seq); bus.to_jsonl()
```

**Payload conventions**

| Kind | Payload |
|---|---|
| `STATE` | `(entity_id, props_dict)` |
| `SIGNAL` | `(target, text)` |
| `TENSION` | `(name, level)` |
| `DECISION` | `(label, src, status, attention)` |
| `WHY` | `(node_id, from, to, reason)` |
| `BIRTH`/`DEATH` | `(script_name, why_node, detail)` |

**Invariants:** events are frozen (`AttributeError` on mutation); the
log only grows; a typical event serializes under ~160 bytes (tested).

---

## L2 — World Graph (`graph.py`)

**Purpose:** anti-RAG knowledge. A typed graph the organism *inhabits*,
where every node has a biography and recall is traversal, not search.

```python
g.upsert("berry:1", "berry", {"food": 1}, tick=t)   # create or reinforce
g.link("berry:1", "clearing:1", "grows_in", tick=t) # Hebbian strengthen
g.seen(["berry:1"], tick=t)                          # bump recency+weight
g.walk(["berry:1"], budget=10)                       # -> WalkResult
g.decay(t, horizon=200); g.churn_since(t-20); g.digest(24)
```

**Invariants:** append/decay-only. `forget()` exists and *raises* —
executable documentation that deletion does not exist. `digest()` is
deterministic (same world ⇒ same string) so it is safe to put in prompts.

**Gotchas:** `walk()` scores by `weight × 1/(1+age)`; if your organism
stops finding things, check whether anything still calls `seen()`/emits
`STATE` events — memory does that automatically from events.

---

## L3 — Memory (`memory.py`)

**Purpose:** the organ between the event stream (short-term) and the
world graph (long-term). Consolidation is cheap enough to run every tick.

```python
rt.memory.consolidate(events, tick)          # STATE/SIGNAL/TENSION -> graph
rt.memory.recall(cue_ids, budget=10)         # = graph.walk
rt.memory.replay(events, tick)               # boosted (x2) consolidation
```

**Invariants:** entities co-occurring within a tick get `co` edges
(capped at 8 per tick); actors get wired to what they signal about;
one node per tension tracks its level.

---

## L4 — Script Ecology (`scripts.py`)

**Purpose:** an agent is a *population*. Scripts are trigger + action +
track record; they compete, starve, die (recorded), and mutate.

```python
s = Script(name="forage", why_node="why:critter", owner="critter",
           relieves=("energy",),          # urgencies come from these
           focus=("berry:1",),            # novelty is measured on these
           when=lambda ctx: ...,          # opportunity gate
           act=lambda ctx: Outcome(True))
rt.ecology.spawn(s, tick=t)               # BIRTH event
rt.ecology.bids(ctx, owner="critter")     # AttentionBids for live scripts
rt.ecology.fire("forage", ctx)            # run + EMA update
rt.ecology.bookkeeping(t, ran, starved)   # starvation/death
rt.ecology.mutate(s, tick=t)              # dream variant (params jitter)
rt.ecology.necrology()                    # every death, forever
```

**Invariants:** `fire()` never raises (crashes become failed outcomes);
death moves a script to the necrology — it is never erased; a script
whose WHY chain is broken never even bids.

---

## L5 — Attention Market + Executive (`attention.py`, `executive.py`)

**Purpose:** the economy. Bids compete; the executive clears, resolves
resource conflicts, and cause-chains every action to its decision.

```python
bid = AttentionBid(src="critter", label="forage", urgency=0.7,
                   justification=1.0, opportunity=1.0, novelty=0.4,
                   expected_value=0.9, resource=None)
bid.attention        # the product of all five, clamped
market.clear(top_k)  # -> ClearResult(winners, starved); veto law inside
Executive(market, bus).arbitrate(bids, top_k=3, ts=t)  # -> list[Decision]
```

**Invariants:** any zero factor vetoes (attention 0 bids never clear —
not even in an empty market); ranking ties break deterministically by
`(src, label)`; one winner per exclusive `resource`, the rest *yield*.
An arbiter's answer must be an ordered subset of the live bids it was
shown (by identity) — a malformed return (wrong types, a foreign
look-alike, duplicates) is a failed answer: it degrades to the
deterministic shadow, is counted in `arbiter_malformed`, and is
recorded as an `ERROR` event.

---

## L6 — WHY (`why.py`) — the crown

**Purpose:** conserved purpose. See [04_why_conservation.md](04_why_conservation.md)
for the full treatment; the API surface:

```python
w = WhyTree()
root = w.declare("the field is worth inhabiting", node_id="why:root")
w.declare("the critter stays alive", parent="why:root")
w.kill("why:root", reason="mandate withdrawn")   # cascade: children -> UNKNOWN
w.revive(nid)                # UNKNOWN -> ALIVE (+ cascade revive)
w.resurrect(nid, "evidence") # DEAD -> ALIVE (requires a real reason)
w.heartbeat(nid, tick)       # stamp liveness
w.verdict(nid)               # ok/reason/blocked_at/path
w.why_should_this_run(nid)   # the heartbeat question
w.justification(nid)         # 0.0 if any DEAD ancestor; else alive-fraction
w.contradictions()           # ALIVE nodes over DEAD ancestors
w.conservation()             # the audit dict; invariant_ok must be True
w.necrology()                # every transition, ever
```

**Invariants:** no deletion API exists; every transition is recorded;
`conservation()["invariant_ok"]` is asserted by the runtime every 25
ticks and by the test suite under randomized kill/revive storms.

---

## L7 — Identity (`identity.py`)

**Purpose:** the slowly-drifting self-model: root purposes, hash-chained
commitments, reinforced style. The stable prompt-prefix source.

```python
ident = Identity("elder-merle", why=rt.why)
ident.commit("always leave berries to regrow", tick=t)   # hash-chained
ident.verify()          # False if anybody edited history
ident.observe_style(rt.ecology.alive())
ident.introspect()      # memoized; byte-identical within a session
ident.drift()           # the ONLY way the self-model rewrites
```

**Invariants:** `introspect()` is memoized — new commitments do *not*
rewrite it mid-session (that discipline is what keeps provider prompt
caches hot); `drift()` is the deliberate, counted cache-bust.

---

## L8 — Sleep (`sleep.py`)

**Purpose:** offline consolidation on idleness: replay (boosted memory),
prune (harsh starvation deaths), dream (parameter mutations).

```python
rt.sleeper.should_sleep(idle_streak)   # idle_streak >= idle_window
rt.sleeper.cycle(tick, events=recent)  # -> cumulative SleepStats
```

**Invariants:** sleep is entered from idleness, not from a clock; a
mid-crisis organism does not sleep; every dream is a real spawn (BIRTH
event) that must survive tomorrow's market on its own merits.

---

## L9 — Society (`society.py`, v0.4 / ADR-0011)

**Purpose:** WHY federation across organisms. A **treaty** is a foreign
purpose reference — beneficiary A's node served by provider B's node —
and the **exchange** routes attestation between their books: when B
stamps B's provider chain, the society re-stamps A's beneficiary chain
with provenance `treaty:<id>`. A's own re-attestation economics does
the enforcing (freshness decay → weaker bids → lapse), so a neglected
delegation strangulates *softly* on A's books, while a provider death
propagates *hard* (the `question()` transition + exchange receipts +
treaty broken).

```python
from cognitive_ecology import Society

soc = Society()
soc.join(rt_a, name="A")           # join order = lockstep tick order
soc.join(rt_b, name="B")
soc.establish_treaty("B", "why:serve", "A", "why:index",
                     "A's index freshness is served by B's archive")
soc.run(100)                        # lockstep ticks + exchange each step
receipt = soc.audit()               # do these books agree?
```

**Invariants:** treaties are append-only (active → broken/revoked,
never back, never deleted); a treaty is active only while both
endpoints are ALIVE; at most one active sole treaty per beneficiary
node; every treaty-provenance stamp on a beneficiary's journal must be
derivable from the provider's journal at the same tick (forged service
is detectable); delegation flows one hop per exchange (cycle-safe).

---

## Cross-cutting

- **`tension.py`** — drives: `add(name, growth)`, `tick()` (grow),
  `relieve(name, amount)`, `burden(name, amount)`, `level/urgency(name)`.
- **`simulations.py`** — `Simulator.forecast(script, ctx)` /
  `rollout(script, ctx, horizon)`: heuristic expected-value estimates,
  zero-LLM by design; LLM rollouts layer on top in your app.
- **`agents/providers.py`** — `OpenAICompatProvider.from_env("DEEPINFRA")`,
  `MockProvider`, `StablePrefixSession` (see
  [06_agents_and_providers.md](06_agents_and_providers.md)).
- **`agents/orchestrator.py`** — `LLMAgent` (proposes scripts from the
  safe action library), `parse_proposals`, `build_when`.
