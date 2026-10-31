# ADR-0013 — The outcome-arbiter: paid judgment must earn its keep

- status: accepted (v0.4 round 14)
- date: 2026-11-01
- closes: OPEN_QUESTIONS #3 (its last open remainder)
- live evidence: [library/rounds/014-outcome-arbiter.md](../library/rounds/014-outcome-arbiter.md)

## Context

ADR-0009 let decision models into exactly one bounded hook — the
executive's tie-break among live contenders — and counted DIVERGENCES:
how often the arbiter disagreed with the deterministic shadow. Round
005's live run measured 50 divergences in 50 calls. But a divergence
count is not a value: disagreeing badly and disagreeing well look
identical. The open remainder on the ledger: score the arbiter by
realized OUTCOMES.

## Decision

### 1. The arbiter's pick is a probabilistic claim — score it

Every arbiter-mediated selection says "this contender deserves the
slot"; when the client carries a calibrated confidence, that is a
probability, and when the pick acts, the outcome (ok/fail) is the
realized value. The claim lands in the SAME immune system as component
claims (`calibration.CalibrationLog`: Brier, reliability bins) — the
arbiter is a citizen too, measurably honest or dishonest from the
organism's own receipts. A pick without confidence makes no claim but
still counts toward the value comparison.

### 2. Overrides are compared against the base rate

Every DIVERGENT pick (the arbiter overrode the shadow) is compared to
the base rate of all actions on arbiter ticks. If the overrides
succeed below (base − margin) over a window, the delegation is
destroying value, not adding judgment — bench. This is measurable
without counterfactual simulation: we never need to know what the
shadow's pick would have done, only whether the arbiter's picks do
better than the organism's average action.

### 3. Benching: the immune response, with a receipt

Two independent bench conditions, either sufficient after a window
(no snap judgments about judgment):

- **calibration**: Brier > 0.25 (coin-flip baseline) over ≥ window
  scored picks — confident and wrong more often than chance;
- **value**: divergent success < base rate − margin over ≥ window
  divergent picks.

A benched arbiter is never consulted again: the executive silently
degrades to the deterministic shadow (the fail-safe ADR-0009 already
guaranteed), announces the benching exactly once as a DECISION event,
and the scorecard's receipt names the numbers. Benching is permanent
within a run — re-enabling is a human act with a new scorecard, which
is the right gravity for firing your own consultant.

### 4. Wiring

The executive carries an optional `scorecard` and exposes
`last_arbiter_context` (tick, pick, confidence, divergent). The
runtime records outcomes after the pick acts and feeds the base rate
from every action on arbiter ticks. `scorecard=None` (the default)
keeps the exact v0.3 behavior — keyless, deterministic, nothing
scored. The scorecard persists in the organism's state; the arbiter
callable is code, attached like any component.

## Live evidence (round 014)

typesafe/jev arbitrated a 4-contender/2-slot organism for 60 ticks
under a scorecard (window 25): 25 calls, 25 divergences, 0 errors.
**The value test did not fire** — jev's overrides succeeded at 0.72
vs a 0.66 base rate; its judgment was slightly better than the
shadow's ordering. **The calibration test benched it at tick 25**
(Brier 0.307): jev chose decently but could not price its own
choices — confident on picks that failed 28% of the time. The
organism continued deterministically for the remaining 35 ticks.

The nuance is the finding: divergence count (25/25) would have looked
terrible; realized value (0.72 > 0.66) looks fine; calibration exposed
the actual weakness. Three different scores, three different stories —
the receipts keep them all.

## What is deliberately NOT here (yet)

- **Re-promotion** — a benched arbiter stays benched within a run; a
  cooldown/parole path (mirror of the WHY revive ceremony) is a
  natural follow-up if play-testing wants it.
- **Per-criterion attribution** — the scorecard scores the arbiter's
  picks, not WHICH criterion steered them; the decision client's own
  answer metadata would be needed.
- **Arbiter-fed factor estimators** — round 009's suggestion that
  realized-outcome weights feed the market's EV estimators; scripts
  already track success rates, and the scorecard is the arbiter-side
  analogue. Merging them is future work.

## Consequences

- The executive stays a procedure; the scorecard is a separate
  kernel module (zero deps) the runtime consults.
- An organism that delegates judgment can, on its own receipts, take
  it back — the loop from ADR-0009's "bounded, veto-guarded,
  fail-safe" to "measured, priced, and fireable" is closed.
- Bench events are ordinary DECISION events: the causal chain from
  benching to the deterministic clearing that follows is walkable.
