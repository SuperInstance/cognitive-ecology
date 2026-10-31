# Round 14 — the outcome-arbiter, live

*Run: 2026-10-31T19:25:05Z — 60 ticks, 2 slots; arbiter live (typesafe/jev) under an ArbiterScorecard (window 25).*

## The scorecard

```
arbiter scorecard [jev]: 25 calls, 25 divergences
  calibration : MISCALIBRATED (Brier 0.307 > 0.25: confident and wrong more often than a coin flip, 25 claims)
  divergent   : 18/25 overrides succeeded (base rate 0.66)
  BENCHED at tick 25: miscalibrated: Brier 0.307 > 0.25 over 25 scored picks — confident and wrong more often than a coin flip
```

- arbiter calls: 25; divergences: 25
- calibration: MISCALIBRATED (Brier 0.307 > 0.25: confident and wrong more often than a coin flip, 25 claims)
- divergent picks: 18/25 succeeded (base rate 0.660)
- BENCHED at tick 25: miscalibrated: Brier 0.307 > 0.25 over 25 scored picks — confident and wrong more often than a coin flip

---
*Triage: see JOURNAL round 14.*