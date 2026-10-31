# Round 5 — the decision model as the market's tie-breaker

*Run: 2026-10-31T09:47:05Z — 50 ticks, 2 slots; arbiter live (typesafe/jev).*

## Arbitration

- arbiter calls: **50**  divergences from deterministic shadow: **50**
- adapter calls: 50; errors: 0; last choice: forager:forager (confidence 0.64)

## Calibration (success_p claims vs seeded outcomes)

| component | claims | claimed p | true rate | Brier | verdict |
|---|---|---|---|---|---|
| forager | 28 | 0.90 | 0.82 | 0.153 | calibrated |
| scout | 27 | 0.90 | 0.52 | 0.395 | MISCALIBRATED |
| archivist | 31 | 0.40 | 0.39 | 0.237 | calibrated |
| wanderer | 14 | 0.60 | 0.86 | 0.189 | calibrated |

Overall Brier: **0.250** (0 = perfect foresight, 0.25 = honest coin flip)

## Reading

- The scout (claims 0.90, truly 0.40) should land MISCALIBRATED —
  that is the immune system working: confident-and-wrong is now
  measurable, per component, from the organism's own receipts.
- Divergence between the jev arbiter and the deterministic shadow
  is not a failure metric; it is the measurement of judgment.
  The shadow is what you get for free; the question is whether the
  paid divergence correlates with better outcomes.
