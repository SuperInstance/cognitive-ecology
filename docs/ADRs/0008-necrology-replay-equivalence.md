# ADR-0008: Necrology replay equivalence — conservation becomes proof-carrying

- Status: Accepted (v0.3.0)
- Date: 2026-10-31
- Origin: adopted from live ideation round 004b (tencent/Hy4-preview
  proposal #1, triaged and reshaped by the build session)

## Context

The conservation law was *tested* (random storms, invariant counts) but a
specific organism could not *prove* its own history. "Nothing was deleted"
was a claim about code, not a property of a saved state file. OPEN_QUESTIONS
#12 asked for a formal statement an external checker could verify.

## Decision

Every WhyTree now carries a complete **replay basis**:

1. **genesis** — every declaration as born: `(id, parent, statement,
   tick, state, last_beat)`.
2. **necrology** — every state transition, append-only (unchanged since
   v0.2).
3. **attestation journal** — every heartbeat stamp: `(tick, node, by)`.

`ConservationAuditor.verify(tree)` replays that basis from nothing —
chronologically merged (at equal ticks, stamps before transitions,
matching the runtime's act→stamp→reap order) — and requires the
reconstruction to equal the living tree bit for bit: states, `last_beat`,
`last_attested_by`, `probation`. The replay semantics are fully determined
by `(from_state, to_state)` pairs, so no schema change to NecroRecord was
needed.

The **receipt** carries: per-check results (genesis present, accounting,
log consistency, state equivalence), the live and replayed digests, and a
**hash chain** over necrology + journal — pin the chain head anywhere
(a commit message, a paper, another organism) and any later edit of
history breaks it. `Runtime.save()` embeds the receipt in `state.json`:
every saved organism carries its own proof.

## What each tamper vector teaches

| Tamper | Caught by |
|---|---|
| Flip a state directly (off the books) | `state_equivalence` |
| Edit a statement | `state_equivalence` |
| Remove a transition record | `log_internally_consistent` / `state_equivalence` |
| Reorder records across ticks | `log_order` (an append-only log is chronological) |
| Forge a transition with a plausible from-state | `state_equivalence` (replay ≠ live) |
| Forge a stamp on a non-ALIVE node | `stamp_validity` |
| Drop the last stamp of a node | `state_equivalence` |
| Drop/edit a *superseded* stamp | the **chain** (state equivalence alone cannot see it) |

Two honest limits, learned from the tests themselves:

- **Same-tick reorders of independent records are absorbed** by the
  chronological replay — and rightly so: they are outcome-equivalent
  histories. The receipt proves outcome equivalence, not byte-order.
- **A superseded stamp is semantically invisible** to state equivalence;
  only the chain head pins the journal completely.

## Consequences

- The formal statement of conservation (OPEN_QUESTIONS #12) now exists in
  executable form: *the live state is in the image of the replay
  function applied to the append-only basis.*
- State files are self-vouching; an external auditor needs no kernel
  internals beyond `audit.py`.
- Old (pre-v0.3) saves have no genesis block and receive an honest
  "no receipt can be issued" rather than a fabricated pass.
- The journal grows with every stamp (a long-lived organism accumulates
  one entry per stamped node per winning act). Acceptable for v0.3;
  compaction (rolling stamps into per-epoch digests) is future work.

## Alternatives considered

- **Record declarations in the necrology** — rejected: breaks every
  existing necrology-length assertion and muddies "transition" semantics;
  genesis is a cleaner first block.
- **Per-tick signed receipts** (the proposal's original shape) — rejected:
  O(records) hashing every tick; receipts at save/audit boundaries and on
  demand are enough.
- **Cryptographic signatures** — rejected: no key management belongs in a
  zero-dependency kernel; a hash chain is tamper-*evident*, which is the
  honest claim.
