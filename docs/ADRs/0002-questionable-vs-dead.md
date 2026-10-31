# ADR 0002 — questionable ≠ dead: the two strengths of losing a root

Date: 2026-10-31 · Status: accepted (after a test taught me the semantics)

## Context

The manifesto says dependents of a dying root become *questionable, not
deleted*. My first runtime test expected exactly that: attest a root dead →
its dependents keep running at a discount. The kernel disagreed, and the
kernel is right.

## Decision

Two distinct strengths, both pinned by tests:

- **Root attested dead** → explicit dependents are `dead` (certainty at any
  depth, the audit's Finding 2 fix). The conservation law is fully
  withdrawn: weight 0.0, the process starves, removal is justified.
- **Root's liveness unknown** — attestation removed, `review-by` stale past
  grace, or reachable only via inferred edges — → dependents are `unknown`
  = *questionable*: weight 0.25, the process keeps running, starving only
  under contention (pinned as a 4:1 energy ratio test).

## Consequences

- The manifesto's "questionable, not deleted" is implemented as the
  kernel's `unknown` paths (dangling / stale / inferred), not as a new
  fifth status. Format compatibility with the Rust tool is preserved.
- The attention weights (alive 1.0, unknown 0.25, dead 0.0) are the bridge
  between the kernel's statuses and the economy's bids — the one place the
  law becomes a number, and therefore the one place to watch for gaming.
