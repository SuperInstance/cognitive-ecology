# Open questions — the living ledger

The manifesto arrived with ten open questions. Status below reflects what
the codebase has actually probed (a question with a probe is a different
beast than a question with an opinion). Panel rounds add new questions at
the bottom; nothing is ever removed, only resolved or refined.

| # | Question | Status | Probe |
|---|---|---|---|
| 1 | Attention: market or government? | **probed** — both implemented plus a hybrid (`attention.py`); default policy is hybrid (30% governance reserve that rolls over when unclaimed, rest market) — "markets locally, governance globally" is now runnable, not just suspected |
| 2 | What is identity? | **probed (minimal)** — `identity.py`: persistent preference as a normalized value distribution; stability measurable as concentration; moves only under sustained pressure (EMA attractor) |
| 3 | What gets simulated? | **probed (minimal)** — `sim.py`: budgeted futures ranked by novelty × importance × uncertainty; zero-priority scenarios never run |
| 4 | What is the primitive unit? | open — tension is implemented (`tension.py`) and feeds briefings/bids, but "tension as fundamental" vs "process as fundamental" is unresolved |
| 5 | Could WHY become the scheduler? | **probed — yes** — `JustificationWatch` multiplies every bid by its WHY weight (alive 1.0 / questionable 0.25 / dead 0.0); dead-justified processes starve, questionable ones run discounted. Reason reachability → attention weight → scheduler priority is real code |
| 6 | Do scripts replace memory? | **probed (v1)** — sleep compiles repeated observations into routines (`sleep.py`); memory graduates observation→episode→pattern→routine in the world graph; experts compile, they don't remember |
| 7 | What is sleep? | **probed (mechanical v1)** — infrastructure evolution, not summarization: replay-validated script candidates, WHY rechecks, retirement pruning, tension habituation; zero LLMs involved |
| 8 | Can we learn without models? | **probed — a shocking amount** — the week-in-a-box compiled 4 routines and retired 5 scripts with no model anywhere in the loop |
| 9 | What's the user actually looking at? | **probed (minimal)** — the morning briefing (`briefing.py`): changed things, urgent tensions, retirement recommendations, necessity census. The "map" remains unbuilt |
| 10 | What is success? | **probed (metrics defined)** — the week report measures accumulated capability (routines born/handled), retained usefulness (learned utility), justification efficiency (broken chains), surprise (tensions). Leverage, not automation |

## New questions from the build (2026-10-31)

- When sleep compiles a routine, *who owns its justification*? Currently
  seed scripts hang off capability nodes; sleep-born routines have no WHY
  edges at all — should they be justified by the pattern's world node?
- The attention formula is multiplicative: one zero factor zeroes the bid.
  Should a novel-but-not-urgent claim really starve? (The keepalive bid
  sidesteps this; the deeper question stands.)
- Tension pressure compounds forever in v1. What is habituation *for
  tensions that never resolve* — retire the expectation (the manifesto's
  own suggestion) or decay the pressure?
- The panel runs 7 models but the ecology's runtime uses none of them. What
  is the first *legitimate* runtime use of a teacher — and does it violate
  Law 4 the moment it becomes load-bearing?

## From panel rounds

*(populated by live rounds; see library/rounds/)*
