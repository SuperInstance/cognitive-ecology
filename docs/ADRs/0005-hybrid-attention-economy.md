# ADR 0005 — attention is a hybrid economy, and the reserve rolls over

Date: 2026-10-31 · Status: accepted (Open Question #1, now runnable)

## Context

Market or government? Markets scale and adapt but leave identity-level
concerns starving at the wrong moment; central allocation is debuggable but
bottlenecks. The manifesto suspects "markets locally, governance globally."

## Decision

Three policies, one default: `MarketPolicy` (proportional to the manifesto
formula), `CentralPolicy` (fixed priority), and `HybridPolicy` (default) —
a governance share (30%) reserved for identity-level bidders, the rest
allocated by score. The reserve **rolls over to the market when no
governed bidder claims it**: a reserved slice nobody can claim is waste,
and the first implementation learned this by failing a test that expected
a market bidder to receive its full request.

## Consequences

- The question stopped being an opinion and became a runnable experiment:
  swap the policy in one constructor argument and re-run the week.
- Bids are multiplied by the WHY weight of the bidder's justification chain
  (ADR 0002's numbers), which is Open Question #5 answered in code: reason
  reachability → attention weight → scheduler priority.
- The multiplicative formula has a sharp edge — one zero factor zeroes the
  bid — deliberately kept (it is the spec) and deliberately bypassed only
  by `Bid.keepalive`, whose score collapses to the justification alone.
