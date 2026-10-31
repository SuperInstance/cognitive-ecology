# ADR-0009: Decision models as the market's tie-breaker, calibration as its immune system

- Status: Accepted (v0.3.0)
- Date: 2026-10-31
- Origin: OPEN_QUESTIONS #3 + docs/08 experiment plan, reshaped by live
  ideation round 004b (calibrated estimators) and validated by live
  round 005 (typesafe/jev).

## Context

Typed, calibrated decision models (typesafe.ai Jev style) answer
probabilistic and choice questions with confidences. The open question
was where they enter the kernel: market clearing? script selection?
tension prioritization? Clearing the WHOLE market through a model would
make the organism non-deterministic, non-keyless, and provider-coupled.

## Decision

Two narrow, honest integration points:

1. **The arbiter hook (executive.py).** The executive delegates exactly
   ONE bounded decision: when there are more live contenders than
   clearable slots, an optional `arbiter` callable may reorder the live
   contenders. Contract, enforced in code: the veto law is applied
   BEFORE the arbiter sees anything (vetoed bids never reach it); it may
   only select among live bids; any failure degrades silently to the
   deterministic top-k. `DecisionArbiter` (agents/decision.py) adapts a
   typed choice question to the hook — state is a cache-stable digest of
   the contention; the question shape (`criteria` field) is pinned by the
   typesafe OpenAPI spec. Default: no arbiter — keyless, reproducible.

2. **The calibration log (calibration.py).** Bids may carry `success_p`
   — a claimed probability the action succeeds. The runtime scores every
   claim against the realized outcome and keeps per-component Brier
   scores and reliability bins. This is the immune system: an estimator
   that is confident and wrong (Brier > 0.25) is *measurably* dishonest,
   from the organism's own receipts. Per docs/08: if provider
   confidences do not track outcomes, they get demoted to rankings — and
   now the kernel has the instrument that decides.

## Evidence (live round 005, 50 ticks, jev arbiter)

- 50 arbiter calls, 0 errors; **50/50 divergences** from the
  deterministic shadow — the paid judgment is visible and countable,
  not a silent override.
- Four components with seeded self-models: the scout (claims 0.90,
  truly 0.52) landed **MISCALIBRATED (Brier 0.395)**; the humble
  archivist (claims 0.40, truly 0.39) landed calibrated (0.237).
  Overall Brier exactly 0.250 — the honest coin-flip line, because one
  overconfident component cancels three calibrated ones.

## Consequences

- The organism stays zero-dependency and deterministic by default; both
  integrations are opt-in and fail safe.
- Divergence is telemetry, not error: `last_divergence` counts how often
  the arbiter overrode the shadow — the price and the point of
  judgment. Whether paid divergence correlates with better outcomes is
  the next experiment (needs outcome-weighted arbiter scoring).
- Calibration claims are per-component and append-only; a component that
  wants market trust must buy it with an honest self-model.
- The arbiter sees only the current tick's contention — no history, no
  cross-tick state — which keeps the delegation bounded and the
  question cache-stable.

## Alternatives considered

- **Model-cleared market** — rejected: breaks determinism and keylessness.
- **Confidence-weighted attention (multiply factors by confidences)** —
  deferred: makes bids non-comparable unless ALL bidders emit
  confidences; the calibration log measures first, and pricing follows
  evidence.
- **LLM-as-arbiter (chat models)** — rejected for this hook: the point
  of the experiment is *calibrated* judgment; chat fluency is not
  calibration.
