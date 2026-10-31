# ADR 0006 — provenance is mandatory; transcripts are receipts

Date: 2026-10-31 · Status: accepted

## Context

Multi-model discussion is easy to fake and easy to waste: a polished
summary tells you nothing about who actually said what, at what cost, or
whether the cache earned its keep. The owner explicitly wants the process
treated as a product.

## Decision

Every panel turn records provider, model, latency, prompt/completion
tokens, cached tokens, and provider-reported cost, and is written to
`library/rounds/` with the full context embedded. Decision gates record
their typed questions and calibrated answers. The usage ledger
(`data/usage.db`, `ecology usage`) aggregates per model. Round documents
are receipts, not prose.

## Consequences

- Any claim in a round document can be traced to its model and price.
  Falsification is cheap: re-run the round with a different seed of
  panelists and compare.
- Costs stay honest: this session's entire live panel program (33 turns,
  5 gates, 7 models) cost ~$0.116 — a number you can only trust because
  every call logged itself.
- A vacant seat is recorded as vacant (the MiniMax 401 became a transcript
  line, not a silent omission).
