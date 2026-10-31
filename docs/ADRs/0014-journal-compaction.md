# ADR-0014 — Journal compaction: the replay basis without the ballast

- status: accepted (v0.4 round 15)
- date: 2026-11-01
- closes: OPEN_QUESTIONS #13

## Context

The 10,000-tick soak measured the price of "never deleted": the
attestation journal grows one entry per stamped node per winning act —
60,000 entries — and verification is O(journal), so throughput fell
from 6.4k to 2.3k ticks/s across the run. The ledger asked: when does
compaction become necessary, and what does it cost the replay basis?

## Decision

### 1. Keep the last stamp per (node, ALIVE window, PROVENANCE)

The replay's final state per node needs only the LAST stamp in each
ALIVE window: last_beat, provenance, and probation-clearing are all
decided by it. We keep a deliberate superset — the last stamp per
(node, window, provenance) — because the society's effective-sole
check (round 011) asks "did anything else ever stamp this node?";
per-provenance lasts keep every servant's evidence alive inside the
current window. Measured: a 2-worker organism's journal holds at 4
entries across 10 epochs of 1,000 ticks each, verify ~0 ms — the
O(journal) price stops growing.

### 2. Compaction is receipted, never silent

Compaction is a STORAGE transition (like archival), not a history
edit. Every compaction appends a `CompactionReceipt` to an
append-only list on the tree: entries before/kept/dropped, a digest
over the dropped entries, and the auditor chain head before and
after. The auditor's hash chain covers the receipts — you cannot drop
stamps and pretend nothing happened, and a receipt that lies about
its counts fails the new `compaction_accounting` check.

### 3. The pre-compaction chain head is pinnable

History inside a compacted span is attested by the receipt's
`chain_before`: pin it (or any earlier head) offline and any edit of
the surviving basis still breaks against it. The federation auditor's
service-derivability check therefore spans only the still-uncompacted
history — bounded by BOTH books' last compactions (a beneficiary
stamp at tick T can only be derived if the provider's journal still
holds tick T). Older cross-organism claims ride on the pinned heads.

### 4. The necrology is never compacted

It is the transition record — one line per event, already minimal,
and the replay's authority for ALIVE windows. Compacting it would
change replay semantics, not just storage.

## Mechanics

`JournalCompactor(tree).compact()` → receipt (or None when nothing is
redundant). ALIVE windows are derived from the genesis birth states
plus the necrology transitions. Stamps outside any window (corrupted
journals) are kept, not hidden — the auditor's validity check still
sees them. The only API that removes a journal entry is the
compactor's internal `_replace_journal`, which requires a receipt.

## Consequences

- Long-running organisms keep flat verification cost with receipts
  proving nothing was lost that the replay needed.
- The journal's role sharpens: it exists to carry the replay's
  freshness/provenance state, not to be a full audit log of every
  heartbeat (the event bus already is that, and events are never
  compacted).
- The chain head is now stable only WITHIN an epoch; epoch receipts
  link them. Anything pinning heads across compactions must pin the
  receipt chain too (the receipts are included in `chain()`).
