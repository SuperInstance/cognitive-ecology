# TEMPLATE — a play-test scenario plan

Copy per experiment. A play-test is a question about the kernel asked by
BUILDING a small organism and watching it live — not a unit test (those
are in tests/) and not a benchmark. Fill every section; "we'll see" is
not a measure.

---

## Scenario name
<!-- e.g. "Tavern Keeper's Faction Ecology" -->

## Hypothesis
<!-- One sentence, falsifiable: "If X, then the organism will Y by tick N." -->

## Domain & organism
- Domain:
- WHY root (exact statement):
- Sub-purposes:
- Tensions (name / growth / what relieves them):
- Scripts (name / trigger / action / what it relieves):
- What persists between sessions:

## Layers exercised
<!-- check the ones this scenario deliberately stresses -->
- [ ] L0 runtime (tick budget / determinism)
- [ ] L1 events (causal chains, size budget)
- [ ] L2 world graph (traversal recall, decay)
- [ ] L3 memory (Hebbian consolidation, replay)
- [ ] L4 script ecology (starvation, death, mutation)
- [ ] L5 attention market (factor tuning, veto law, resource conflicts)
- [ ] L6 WHY (kill / cascade / revive / contradictions)
- [ ] L7 identity (commitments, stable prefix)
- [ ] L8 sleep (replay / prune / dream)
- [ ] agents (LLM proposals / decision models / cache session)

## Measures
<!-- What you will actually read out. Use scripts/run_rounds.py telemetry. -->
- Primary:
- Secondary:
- Where to look (telemetry field / report / graph digest):

## Setup
```bash
# exact commands to reproduce
```

## Observations
<!-- What actually happened, with tick numbers. Surprises are the point. -->

## Verdict
- Hypothesis: supported / refuted / needs another round
- What to change in the kernel (if anything):
- What to change in the scenario:

---

## Scenario catalog (seeded by dogfooding tencent/Hy4-preview)

These eight were generated during the 2026-10-31 dogfooding session
(see experiments/dogfood/) and are free plays waiting to be run:

| # | Domain | Organism | Root WHY | Interesting failure mode to watch |
|---|--------|----------|----------|-----------------------------------|
| 1 | Games | Tavern Keeper's Faction Ecology (persistent GM) | "Keep the shared fiction coherent while no human GM is present." | WHY ossification: unkillable old obligations |
| 2 | Health | Chronic Signal Steward (non-diagnostic tracker) | "Preserve a trustworthy longitudinal record; surface only actionable patterns." | Urgency gaming: a script inflating its own drive |
| 3 | Finance | Personal Portfolio Steward (advisory, non-custodial) | "Maintain an auditable, assumption-tracked view of exposures." | Assumption rot: refreshing one belief silently questioning its children |
| 4 | Education | Language Apprentice (spaced, narrative) | "Schedule practice against forgetting, not against a syllabus." | Interference: similar items forming false Hebbian links |
| 5 | Science | Lab Notebook Protocol-steward | "Preserve reproducible provenance." | Deviation clusters consolidating into false patterns |
| 6 | DevOps | Incident Responder organism | "Minimize time-to-mitigation without hiding risk." | Justification collapse when the owner-ack node goes stale |
| 7 | Smart home | Household Energy/Comfort Steward | "Maintain comfort within energy budget." | Comfort conflicts reinforcing the wrong automation |
| 8 | Agriculture | Greenhouse Crop-steward | "Maximize yield per resource unit." | Missing sensor data zeroing justification silently |

Pick one, copy this template, and run it. The failure modes above are
the most interesting part — an ecology proves itself by how it degrades.
