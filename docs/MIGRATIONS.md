# Migrations — upgrading organisms across versions

*State files are designed to outlive the code that wrote them. This
page is what changes, release by release, and what an old organism
needs (usually: nothing) to keep living.*

## The compatibility law

`Runtime.load()` is **backward compatible by absence**: newer readers
accept older state files, filling in defaults for keys that did not
exist when they were written. No organism has ever needed a migration
*script*; the door checks what is there and only demands what the
saved format actually claims. When a save carries proofs (receipts,
chain heads), `load()` re-derives them at the door rather than
trusting them — trust is for the verified, not the stored.

## v0.2.0 → v0.3.0 — the economics of persistence

**What changed:** re-attestation economics (ADR-0007), the
conservation auditor + receipts (ADR-0008), decision arbiters +
calibration (ADR-0009), honest archival (ADR-0010).

**Old organisms:** load unchanged. `attestation_horizon` defaults to
`None` (purpose stays timeless until you opt in); pre-receipt state
files carry no receipt and are covered by the conservation check at
the door. Cold storage is opt-in (`ColdStorage.sweep`), never
automatic — an untouched organism simply keeps growing its journals,
exactly as before.

**If you want the economics:** construct new runs with
`Runtime(attestation_horizon=...)` and expect served purposes to be
stamped by winning attention (see `docs/04` § re-attestation).

## v0.3.0 → v0.4.0 — purposes that cross organisms

**What changed:** society-basis federation (ADR-0011), the WHY DAG
(ADR-0012 — a node may carry several parents; verdict semantics are
best-path), the outcome-arbiter (ADR-0013), journal compaction
(ADR-0014).

**Old organisms:** load unchanged. Single-parent nodes are a DAG
special case; `parent=` keeps working; `parents=` is additive.
Federation and arbiters are opt-in objects, not state-format changes.

**Journals growing?** `rt.compact_events(path, keep=N)` truncates the
event log under a snapshot + chain anchor (round 20b) — storage-only,
never behavioral: a compacted life replays bit-identically (pinned).

## v0.4.0 point releases — persistence trust (rounds 20a/20b)

- `save()` is atomic (temp + rename) and `events.jsonl` is append-only
  per save; `state.json` now carries `chain_head` / `watermark`.
  **Pre-20a saves still load** — their states carry no head, and the
  conservation door covers them.
- `load()` verifies at the door: a tampered state raises with the
  failing check named; a truncated or edited event log fails the chain
  fold by name.
- Sleeper stats, `idle_window`, and adopted-script birth ticks now
  persist. **Pre-20a saves** default these (idle_window 5) rather than
  refusing.

## What is NOT organism state (and never rides in state.json)

- **The market log** (round 21): observation, not state. A loaded
  organism starts a fresh `rt.market_log`; your durable copy is the
  `market.jsonl` you chose to write (see `run_rounds.py`).
- **Driver reports, run manifests, sweeps** (round 22): host receipts.
- **Duplicate-rejection counters** (round 23): economics telemetry,
  counted fresh per process.

## The attach rite, de-rited (round 23)

If your `attach()` predates round 23, it guards every call:

```python
# the old rite                                        # the new rite
if not rt.why.has("why:desk"):                        rt.ensure_why(
    rt.declare_why("...", node_id="why:desk")             "...", node_id="why:desk")
if "energy" not in rt.tensions.names():              rt.ensure_tension(
    rt.tensions.add("energy", growth=0.03)                "energy", growth=0.03)
if rt.component("desk") is None:                     rt.ensure_component(desk)
    rt.register(desk)                                 rt.ensure_script(script)
if rt.ecology.get("answer") is None:
    rt.ecology.adopt(answer_script, tick=rt.tick_no)
```

Both forms still work; the new one is idempotent by contract (pinned
by test: the rite runs twice, painlessly). One honesty rule: an
existing `node_id` re-ensured with a *different statement* raises —
an id means one purpose, forever.

## Checking what you have

```python
import json
state = json.load(open("runs/organism/state.json"))
print(state["version"], state["tick"])   # e.g. 0.4.0 4217
```

The version is informational; the door decides by content, not by
number. When in doubt, just `load()` — a broken organism tells you
which check failed, by name.
