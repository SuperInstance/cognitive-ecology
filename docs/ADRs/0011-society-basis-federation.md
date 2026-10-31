# ADR-0011 — Society-basis: WHY federation across organisms

- status: accepted (v0.4 round 10)
- date: 2026-11-01
- adopted from: live ideation round 009 (Hy4-preview, cache-first, ranked #1 of the v0.4 frontier)

## Context

Until now an organism's purpose basis has been entirely local: every WHY
node in A's tree is served (or neglected) by A's own components. The
moment two organisms exist, a new kind of purpose appears — **delegated
purpose**: A's purpose whose service happens inside B. A research
assistant that leans on an external archive; an agent whose "keep the
shared index fresh" purpose is only ever served by a teammate.

OPEN_QUESTIONS #5 asked what a society of organisms needs. Round 9's
live ideation proposed the sharp pinning test that forced the design:

> A's purpose served only by B lapses when B dies, with an exchange
> receipt on A's books.

The society must inherit the kernel's first law: **purpose is never
deleted — across organisms, not just within one.** When B dies, A's
delegated purpose must become *questionable* (UNKNOWN), never gone.

## Decision

### 1. Treaties route attestation; the existing economics enforces

A **Treaty** is the foreign purpose reference: a recorded, append-only
relationship

```
beneficiary A, node a  <-- served by --  provider B, node b
```

The society does NOT reach into justification() with a cross-organism
term. Instead, treaties **route service**: when B's runtime stamps B's
provider chain (a component under `b` won), the society re-stamps A's
beneficiary chain on A's own books, with provenance `treaty:<id>`.

This one rule composes with everything v0.3 already enforces:

- **Freshness** — A's chain stays fresh exactly as long as B actually
  serves. Sparse service → weakest-link freshness decay → weaker bids →
  the attention market reallocates away from neglected delegations
  *before anything formally breaks*.
- **Lapse** — with an attestation horizon, a delegation B stops serving
  lapses to UNKNOWN on A's own books, by A's own reaper. The soft path.
- **Provenance** — every routed stamp is journaled on A with the treaty
  id; nothing flows silently.

Chain-stamping composes with treaties for free: any descendant of `b`
that wins stamps `b` itself, so "a stamp landed on `b`" is exactly
"the provider purpose was served," no matter which child did it.

### 2. Death propagates hard; neglect propagates soft

Two distinct failure modes, two distinct propagations:

- **Hard (event-driven):** B's provider node transitions to DEAD or
  UNKNOWN (killed, cascaded, or lapsed in B). The delegation is *known
  broken*: the society breaks the treaty and — if the treaty is the
  node's sole basis — **questions** A's beneficiary node
  (ALIVE → UNKNOWN, recorded in A's necrology, exchange receipt on A's
  books). Immediate, explicit, revivable by A's own `revive()` ceremony.
- **Soft (economic):** B's node stays ALIVE but stops serving (B's
  attention moved on). No event fires; A's stamps simply stop, and A's
  own re-attestation economics strangulates the delegation at A's own
  pace. *Doubtful* is not *broken* — the distinction mirrors
  ALIVE-vs-UNKNOWN epistemology.

### 3. `question()` — the external-doubt transition

New public WhyTree transition: `question(nid, reason, tick)` —
ALIVE → UNKNOWN, recorded in the necrology, no cascade (like a lapse:
the node itself is questioned; descendants stay formally alive but
verdict-blocked, and `contradictions()` will find them). The runtime
itself never calls it; it is the transition society-level organs use to
record that doubt arrived from outside the organism. It replays under
the conservation auditor like any other (from, to) pair — no auditor
change needed.

### 4. Treaties are active only while both endpoints are ALIVE

The exchange watches both books: B's provider death breaks the treaty
(and questions A's node if sole-basis); A's beneficiary death (killed,
lapsed, or archived to cold storage) breaks the treaty too — a treaty
whose purpose is dead is dead weight. Broken treaties stay in the
ledger forever (append-only, like everything else). A may revive its
node and establish a *new* treaty; it may also start serving the
purpose locally — the node was always A's.

`sole_basis=True` (default) declares the node is served only by this
treaty; at most one active sole treaty may name a beneficiary node
(validated at establishment). Non-sole treaties stack — a node with a
local component AND a treaty survives the treaty's death on its local
service alone.

### 5. EXCHANGE events; the federation auditor

New `EventKind.EXCHANGE` (11) — payload tuples of scalars, emitted on
the affected members' buses: `established`, `service`, `broken`,
`revoked`.

`FederationAuditor.audit(society)` lifts the ADR-0008 philosophy one
level — from "do these books replay" to "do these books agree":

- `ledger_append_only` — treaty ids contiguous, records never removed;
- `endpoints_alive_while_active` — no treaty still active whose
  endpoint node is DEAD/UNKNOWN/absent/archived (a missed or late
  propagation is a bug);
- `service_derivable` — every treaty-provenance stamp on A's journal
  (A's node, A's chain) matches a real stamp on B's provider node at
  the same tick. **Forged service is detectable**: A cannot claim
  service B never gave;
- `break_receipts_present` — every sole-basis provider-side break has
  its question() record on A's necrology;
- `member_conservation` — every member's own books still balance.

Plus a hash chain over the treaty ledger (pin the head, detect any edit
of society history offline).

## What is deliberately NOT here (yet)

- **Cross-organism attention markets** — members bid only in their own
  markets; treaties move attestation, not bids.
- **Society replay basis** — the auditor checks agreement
  directionally, not full replay equivalence of the whole society (the
  v0.4 direction: recompute the exchange deterministically from both
  bases and compare).
- **Heterogeneous clocks** — `Society.step()` ticks members in
  lockstep; `exchange()` is exposed for manual drivers at their own
  risk.
- **WHY-DAG** — a beneficiary node still has exactly one parent;
  multi-parent purposes are the next round (ADR-0012, anticipated).
- **Foreign references on the WhyNode itself** — the treaty ledger IS
  the foreign reference registry; keeping the node rows unchanged
  keeps the v0.3 conservation auditor bit-compatible (basis field
  churn would break every existing receipt for no semantic gain).

## Consequences

- The kernel change is minimal and surgical: one transition
  (`question`), one event kind (`EXCHANGE`). Everything else is a new
  composing module (`society.py`), zero new dependencies.
- Delegation latency is one society step per hop — treaty-routed stamps
  become visible to downstream treaties on the *next* exchange. This
  is cycle-safe (A→B→A cannot loop within one exchange) and honest
  (influence propagates at the speed of society, not instantly).
- An organism in a society carries exchange receipts it cannot produce
  alone — proof, on its own books, that somebody else served its
  purpose (and that it noticed when they stopped).
