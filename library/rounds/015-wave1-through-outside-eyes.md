# Round 15 — ideation: the wave-1 ledger through outside eyes

*Run: 2026-11-01 — tencent/Hy4-preview, cache-first, three slices
(~$0.019 total; spec bumped to v0.4 so the first call re-primes the
cache). Stable prefix: scripts/ideate.py SPEC (v0.4). Full texts:
experiments/dogfood/015{,b,c}-wave1-ideation.md.*

## The seventh engineer (the persona we did not cast)

Cast as the operator/SRE keeping one organism alive for weeks on a real
host, the model's verdict: *"a correct organism with no physiology — it
can think, remember, and justify, but it cannot survive contact with a
real host."* What the six personas missed:

- **No resource envelope** — no memory/CPU/disk/token ceilings, no
  eviction priority, no backpressure; graph, events, necrology, journals
  and script population grow until OOM / disk-full / bill spike.
- **Sleep is a feature, not a governor** — pruning only runs when idle;
  an always-busy production organism never sleeps. The safety valve
  exists only when there is no pressure — exactly backwards.
- **No liveness/health surface** — no health endpoint, no tick-latency
  SLO, no "am I behind?" signal.
- **No tick-duration contract** — hosts sleep, laptops wake 20k ticks
  behind; no fast-forward vs. dream policy.
- **No multi-process guard** — two writers race the journal/checkpoint
  even with atomic rename.
- **No export hatch** — `save()` is a checkpoint, not a transferable
  organism (no freeze/clone/fork/archive).

## Ranking of the four planned build rounds

**A (persistence) > C (host integration) > B (measurable) > D (safe
seam)** — "a torn save destroys *state*; a missing cron bridge only
blocks *adoption*"; A and C are close enough to build as one
"trustworthy + runnable" milestone.

## Riskiest hidden assumptions (per round)

- **A**: a valid receipt does not prove the checkpoint is *semantically
  resumable* — you can load a valid receipt into an unbootable organism.
- **B**: "logging the factors is a pure side-effect" is false twice:
  the log can become a second source of truth operators trust over the
  receipts, and rounding/clamping to make the log stable mutates the
  multiplicative attention arithmetic. The logged values must be the
  EXACT values used in selection, or the log is a lie that still looks
  authoritative.
- **C**: recipes make the missing physiology load-bearing — a FastAPI
  lifespan driving 10k ticks/s has no declared cost model, no saturation
  signal; the driver works locally and exhausts real hosts.
- **D**: rejection counted only at the seam returns one layer inward —
  a rejected duplicate is a demotion in the ecology (L4), and a
  NaN-clamp can still propagate into bids and confidences.

## Q4: the finding that is a symptom, not a feature request

**Finding 3 (the invisible organism).** The kernel has no first-class
observation boundary: no stable external projection of what exists, why
it ran, what died. Every later request — persistence trust, attach,
host story, safe seam — gets bolted on as a feature instead of falling
out of one contract. The gap is the missing **read model**: one
deterministic, cache-friendly introspection surface over state,
biography, and receipts. Fix that and the organism stops being
invisible by construction.

## Q5: the event-retention verdict

**Ship snapshot+delta.** A ring buffer silently discards causality;
receipted truncation still loses replay unless every delta is anchored.
Snapshot+delta matches the proof-carrying replay basis already in L6:
the snapshot is a compacted state root under receipts; deltas are the
ordered event stream since that root; truncation of pre-snapshot
ranges happens only after the snapshot proves exact replay equivalence.

The pinning test:
`test_snapshot_delta_replay_equivalence_is_bit_identical` — build, run
N ticks, snapshot at K, truncate events < K with a receipt, replay from
the snapshot, assert the living tree / WHY states / script weights /
introspection are bit-for-bit equal to the un-truncated run, and that
any tampered delta or missing receipt fails loudly.

---
*Triage: see JOURNAL round 19 (ranking accepted; round 20 reshaped to
snapshot+delta; round 21 must log the exact values the market used — a
read model, never a second source of truth; the physiology gap opened
as OPEN_QUESTIONS #15).*
