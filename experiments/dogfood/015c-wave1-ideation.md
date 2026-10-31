<!-- dogfood: model=tencent/Hy4-preview | prompt_tokens=812 completion_tokens=1436 cached_tokens=384 latency_s=29.06 | date=2026-10-31 | tool=scripts/ideate.py -->

Q4 VERDICT (max 120 words):

The finding that is actually a symptom of a deeper design gap is **3: invisible organism**.

It is not a UI or logging request. It reveals that the kernel has no first-class **observation boundary**: the organism’s living tree, attention market, WHY DAG, script population, and necrology are addressable internally but have no stable external projection. A host cannot ask what exists, why it ran, or what died without ad hoc peeking. That forces every later request—persistence trust, attach rite, host story, safe seam, lossy example—to be bolted on as features instead of falling out of one contract. The gap is the missing **read model**: one deterministic, cache-friendly introspection surface over state, biography, and receipts. Fix that and the organism stops being invisible by construction.

Q5 (max 250 words):

**Pick: snapshot+delta.**

Why: a ring buffer silently discards causality; receipted truncation still loses replay unless every delta is anchored. Snapshot+delta matches the proof-carrying replay basis already in L6: the snapshot is a compacted state root under receipts, and deltas are the ordered event stream since that root. It binds retention explicitly, keeps journals reproducible, and lets L8 sleep compact history without lying about birth-to-now.

1. Emit `snapshot{root_tick, digest, state_root}` at sleep/compaction.
2. Retain deltas from `root_tick` forward; older events are recoverable only via replay equivalence, not by resurrection.
3. Truncation is receipted: old ranges are dropped only after the snapshot proves exact replay equivalence.

Single test that must pin it:

**`test_snapshot_delta_replay_equivalence_is_bit_identical`**
- Build an organism; run N ticks; take snapshot at tick K.
- Truncate events `< K` with a receipt.
- Replay genesis + necrology + journal from snapshot at K.
- Assert final living tree, WHY states, script weights, and introspection string are bit-for-bit equal to the un-truncated run.
- Assert any tampered delta or missing receipt fails loudly.

This pins retention, compaction, and trust in one place.
