# ADR 0003 — sleep is mechanical first; teachers are a later organ

Date: 2026-10-31 · Status: accepted

## Context

Open Question #8 ("can we learn without models?") and the manifesto's
insistence that the runtime work with zero LLMs pull one way; the obvious
richness of LLM-proposed routines pulls the other.

## Decision

Sleep v1 is entirely mechanical: signature statistics, replay validation,
utility-seeded candidates, promotion by realized success. No model is
involved anywhere in the loop. Teachers enter later as *proposers of better
handlers* for patterns the mechanical pipeline already validated — they
edit the organism; they are not the organism.

## Consequences

- The week-in-a-box result (4 routines compiled, 5 scripts self-retired,
  332 observations handled, zero LLM calls) is a clean lower bound: this
  much accumulation happens before any model is involved.
- The reversal condition is measurable: if a teacher-proposed handler, run
  through the same promotion pipeline, does not beat the mechanical one on
  learned utility, the teacher adds cost without capability — and the
  experiment says so out loud.
- Replay-validation currently confuses frequency with value (the panel's
  round-002 critique); the fix (utility must come from *consequence*, not
  occurrence) is queued behind the same test-first discipline.
