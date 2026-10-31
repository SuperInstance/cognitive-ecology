# ADR 0001 — one repo, the law and the organism together

Date: 2026-10-31 · Status: accepted

## Context

The ecosystem already has `why` (Rust, the flashlight CLI) and why-lab
(private receipts). The ecology needs WHY in-process, every tick, as the
scheduler's law. Options: extend the Rust repo, or start a new Python repo
that ports the kernel and builds the organism around it.

## Decision

One new repo (`cognitive-ecology`), Python, with the WHY kernel ported
inside it as `ecology.why`. The Rust `why` remains the reference
implementation and the CI tool; the Python port exists so the runtime can
query justification as a function call.

## Consequences

- Two implementations of the same law must never drift silently: both are
  pinned to the same golden corpus (15 pairs, copied verbatim), and the
  corpus is the contract. A pair that changes behavior is a semantic
  decision, not a refactor.
- Python was chosen because the organism's layers (processes, attention,
  sleep) are experimental and iterate fast, and because the provider
  ecosystem (httpx, quick scripts) is a better fit for the teacher layer.
- Reversal condition: if the kernel port and the Rust reference ever
  disagree on a case not covered by the corpus, the case becomes a new
  corpus pair first, then whichever implementation is wrong fixes.
