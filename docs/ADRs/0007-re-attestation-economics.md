# ADR-0007: Re-attestation economics — liveness is a subscription

- Status: Accepted (v0.3.0)
- Date: 2026-10-31
- Deciders: build session three; independent convergence by live panel round 001

## Context

The WHY conservation law (ADR-0002) pins the four-state semantics and the
never-delete invariant. But play-testing and live panel round 001 converged
on the same hole from two directions: **liveness attested once stays valid
forever**. `last_beat` was written by `heartbeat()` and never read by
anything. Consequences:

- "Never deleted" degenerates into "never questioned" — an organism can
  carry purposes nobody has served for ten thousand ticks, all scoring
  full justification, all bidding at full strength.
- Purpose becomes a **purchase** (assert once, own forever) instead of a
  **subscription** (maintain or lose). Real organizations do not work that
  way; an organism that persists for years should not either.
- The attention economy's justification factor loses all dynamics: it is
  1.0 for every alive chain, so it never differentiates anything.

## Decision

An **opt-in `attestation_horizon`** (default `None` = exact v0.2 semantics)
turns liveness into a subscription with four mechanics:

1. **Use it.** When a component wins the market and acts, the runtime
   stamps heartbeats along its ENTIRE WHY chain (`stamp_chain`) — serving
   a purpose maintains its whole lineage, transitively to the root.
2. **Lose it.** `justification()` multiplies the alive-fraction by the
   chain's **weakest-link freshness**: full through the first third of the
   horizon (grace window), then linear decay to zero. A stale purpose bids
   progressively weaker — it loses contention long before anything formal
   happens to it. The market squeezes unserved purposes; the kernel only
   records the outcome.
3. **Lapse.** An ALIVE node unattested for longer than the horizon flips
   to UNKNOWN ("lapsed") by the reaper, which runs at the periodic
   conservation audit. Lapse is per-node — it says "nobody served THIS",
   whereas a kill cascade says "this lineage is wrong". Both land in the
   necrology; neither deletes anything.
4. **Revive.** A lapsed purpose returns only by explicit `revive(reason)`
   — a conscious re-justification that stamps a fresh horizon. The lapse
   itself stays in the necrology forever.

## Consequences

- **The economics close the loop**: purposes that get served stay strong,
  purposes that stop being served decay, lose market share, lapse to
  questionable, and can only return through deliberate re-justification.
- **The trap question** ("stale chains can't run, so how do they
  re-attest themselves?") is resolved by design: they cannot. Economic
  death precedes formal lapse; revival is always a conscious act.
- **Transitive attestation** means a thriving leaf keeps its whole
  lineage fresh: subsystems justify their parents by working.
- **Determinism preserved**: freshness is a pure function of
  `(last_beat, now, horizon)`; no wall-clock, no randomness.
- **Backward compatible**: `attestation_horizon=None` reproduces v0.2
  behavior bit-for-bit (pinned by `test_no_horizon_keeps_v02_semantics_forever`).
- **The audit is the reaper's cadence** (every 25 ticks): lapses are
  batched into the periodic conservation audit, so the reaper costs
  nothing extra on the hot path.

## Alternatives considered

- **TTL-based hard deletion** — rejected: violates the conservation law.
- **Reaping cascades like kills** — rejected: conflates "wrong lineage"
  with "unserved purpose"; per-node lapse is the honest reading.
- **Freshness on every chain node including non-ALIVE** — rejected:
  double-punishes UNKNOWN links already discounted by the alive-fraction.
- **Wall-clock attestation** — rejected: breaks reproducibility; ticks are
  the organism's time.

## Amendments from live red-team round 004 (same day)

`tencent/Hy4-preview` attacked this design in four escalating iterations
(gated by jev; transcript in `library/rounds/004`; $0.009, 38% cache hit).
Findings and dispositions:

1. **"Heartbeat laundering / ancestral piggybacking"** — a parasite child
   rides a high-traffic ancestor's stamps. *Disposition: partially
   mistaken (stamps go leaf→root; a sibling's win never stamps the
   parasite, whose own staleness decays its chain) — but the underlying
   demand is right: attestation needs provenance.* **Adopted**: every
   stamp now records `last_attested_by` (the winning component), pinned
   by test and persisted.
2. **"UNKNOWN-washing"** — kill a lineage, revive the descendants: each
   revival bought a fresh horizon without service, making mass
   kill-and-revive cheaper than honest service. *Disposition: real.*
   **Adopted**: revival is now **parole, not pardon** — revived nodes
   carry `probation` and their chain's justification is capped at 0.5
   until a genuine winning act re-attests them. Resurrect and cascaded
   revivals land on parole too.
3. **"UNKNOWN is operationally DEAD in bids"** — *Disposition: factually
   wrong.* UNKNOWN contributes `alive/len` (a proportional discount),
   not a zero; only DEAD is a hard veto. The questionable-vs-dead
   distinction (ADR-0002) survives the economics intact.
4. **"Discrete audits as a scheduling primitive"** — *Disposition:
   rebutted.* Freshness decays **continuously** — `justification()` is
   evaluated from `last_beat` on every tick; the 25-tick audit only
   *formalizes* the lapse into UNKNOWN. There is no window in which a
   stale purpose bids at full strength.
