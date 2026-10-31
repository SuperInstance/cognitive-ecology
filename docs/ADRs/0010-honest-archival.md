# ADR-0010: Honest archival — cold storage that is not deletion

- Status: Accepted (v0.3.0)
- Date: 2026-10-31
- Closes: OPEN_QUESTIONS #6

## Context

A ten-year organism accumulates DEAD purposes. The conservation law
forbids deletion — but a hot tree of ten thousand dead nodes is slow to
walk, noisy to prompt, and dishonest about what the organism still
considers live. The question was whether an archival exists that is
*honest*: not deletion wearing a different name.

## Decision

`ColdStorage` moves ancient DEAD subtrees out of the hot tree, under four
honesty requirements:

1. **Conservative eligibility.** A node is archivable only if DEAD for
   longer than `min_age` ticks AND no ALIVE descendant exists anywhere in
   its subtree (nothing living depends on the lineage) — and it archives
   together with its whole eligible subtree, so parent references never
   dangle. A DEAD node with a living descendant (a contradiction) is
   never archived: the dissonance stays visible in the hot set.
2. **The books stay balanced.** `conservation()` counts hot + archived ==
   ever_declared. Archival never touches the invariant.
3. **The biography travels.** The archive manifest carries each node's
   full row (statement, lineage, states, last heartbeat, provenance,
   archived_at). The conservation auditor (ADR-0008) replays the full
   basis and checks the manifest against the reconstruction — cold nodes
   are exactly as verifiable as hot ones, and a tampered manifest fails
   `archive_manifest_equivalence`.
4. **Restoration is a recorded two-act ceremony.** `restore(nid, reason)`
   returns the whole cold subtree to the hot tree *still DEAD*, with a
   DEAD→DEAD necrology record naming the reason (a storage transition
   made visible); from there the normal `resurrect(reason)` applies —
   with parole (ADR-0007). Coming back from the cold is two conscious
   acts, both on the books.

Archival itself is deliberately NOT a necrology record: nothing about
the node's purpose changed, only where it sleeps. The manifest and the
auditor carry that load.

## Consequences

- The hot tree stays small and prompt-friendly; `digest()` shows only
  living concerns; the dead rest verifiably cold.
- Persistence round-trips the archive (`to_json`/`from_json`), so saved
  organisms keep their cold storage.
- The restore record (DEAD→DEAD) is replay-safe: the auditor applies it
  as a no-op state change while still counting it in the chain.
- OPEN_QUESTIONS #6 closes with an answer, not a shrug: honest archival
  is conservative eligibility + balanced books + traveling biographies +
  a recorded ceremony.

## Alternatives considered

- **Hard deletion of old DEAD nodes** — rejected: violates the law.
- **Archiving single nodes (not subtrees)** — rejected: orphans children
  and breaks chain walks.
- **Archival as a WHY state (a fifth state)** — rejected: COLD is a
  storage fact, not a purpose fact; mixing them muddies the state
  machine the necrology pins.
- **Archival recorded in the necrology** — rejected for the sweep (it is
  not a state transition), accepted for the RESTORE (returning to the
  hot set deserves visibility in the purpose's history).
