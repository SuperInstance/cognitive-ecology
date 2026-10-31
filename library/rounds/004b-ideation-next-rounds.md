# Round 4b — ideation: the next build rounds

*Run: 2026-10-31T09:36:39Z — tencent/Hy4-preview, cache-first, $0.002649.*

## Proposal

**Round 1 — `why.conservation.audit` (highest value/risk)**  
Build: a tick-scoped invariant checker that proves WHY conservation over the necrology: every transition is append-only, `ALIVE/DEAD/UNKNOWN/ABSENT` counts balance, kills cascade descendants to `UNKNOWN`, and no `DEAD` node is silently resurrected outside parole. Emits a signed `conservation_receipt` per tick.  
Advances/closes: “formal conservation statement” and de-risks “honest archival of ancient DEAD nodes” by making archival provably lossless.  
Sharpest test: “Necrology replay equivalence”: replay the append-only log from genesis and assert final WHY-state digest equals the live kernel’s digest; any divergence fails.  
Falsifier: a legitimate revival or cascade produces a state the auditor cannot reconstruct from the log — conservation is not the real invariant.

**Round 2 — `attention.estimator.calibration`**  
Build: replace hand-set `expected_value`/`novelty` heuristics with a typed calibrated estimator: each bid factor emits a bounded probability or scale plus a confidence interval; the market multiplies lower bounds, so uncalibrated optimism cannot win. Log Brier/calibration error per estimator.  
Advances: “smarter attention estimators” and “decision-model integration boundary (typed calibrated choices).”  
Sharpest test: “veto monotonicity”: inject a factor whose true value is 0; the calibrated lower bound must veto regardless of other factors’ variance.  
Falsifier: estimators stay overconfident under distribution shift and top-k keeps selecting starved purposes — calibration does not bind.

**Round 3 — `sleep.scheduler.trigger`**  
Build: a deterministic scheduler

---
*Triage: see JOURNAL.*
