# Decision Models & the Ecology — the Synergy

*What changes when a citizen returns typed choices with calibrated
confidence instead of free text.*

## What "decision model" means here

A decision model (typesafe.ai's "System One Models" such as Jev, or
OpenAI's Decisions API) is a model trained to return a **typed decision**
— a choice among options, a score, a yes/no — **with a calibrated
confidence**, at high speed and low cost, rather than prose. The pitch is
reliability: outputs match a schema, uncertainty is explicit, and your
software can act on both.

An ecology of scripts under an attention market is a *natural host* for
such citizens, because the market already speaks the language decision
models output: options, scores, thresholds, uncertainty budgets.

## Five concrete synergy points

### 1. Market clearing as constrained allocation
The attention market is a per-tick allocation problem: scarce action
budget (`top_k`), competing bids, exclusive resources. A decision model
can *assist or replace* the greedy clear — e.g. choosing the portfolio of
winners that maximizes joint expected value under constraints, with a
confidence on the allocation. The kernel's default stays deterministic
(greedy + tie-breaks); a decision model is an injectable policy.

### 2. Script selection under uncertainty
When several scripts can relieve the same tension, the heuristic
`expected_value = success_rate` ignores *variance* and *context*. A
decision model chooses among the eligible bids with calibrated
confidence; low-confidence choices can be routed to a slower path (an
LLM rollout, or a human) — exactly the "act autonomously or ask for
review" threshold decision models advertise.

### 3. Simulation policies
`simulations.py` ships a transparent heuristic forecaster and a seam for
LLM-backed rollouts. Decision models slot in between: cheap enough to
run per-tick, typed enough to feed `expected_value` directly
(`{"choice": "forage", "confidence": 0.72}` → EV 0.72 with the
confidence available for tie-breaking).

### 4. Tension prioritization as multi-objective decision
When three drives are all at 0.9, "which relief matters most *now*" is a
judgment call — currently resolved implicitly by factor arithmetic. That
is a typed decision (choice among tensions, calibrated), and it is where
a decision model can encode priorities your growth rates can't express.

### 5. WHY as hard constraints, decisions as soft choice
The cleanest division of labor in the whole design: the WHY tree is a
*constraint system* (veto/allow — never a score to be outbid), the
market is *scarcity*, and the decision model is *choice under
uncertainty within what the constraints allow*. A dead assumption
removes options before the decision model ever sees them — see
`examples/03_decision_desk`, where killing the "regime holds" assumption
makes the desk *stand down* rather than trade on a dead premise.

## The integration seam (already in the kernel)

```python
from cognitive_ecology.agents import OpenAICompatProvider

# Any OpenAI-compatible decision endpoint; keys env-only.
provider = OpenAICompatProvider.from_env("TYPESAFE")   # TYPESAFE_API_KEY etc.
```

`examples/03_decision_desk/main.py` defines the `DecisionPolicy`
protocol — `choose(options, context) -> {"choice", "confidence"}` — with
two implementations: a keyless heuristic, and an OpenAI-compatible
client for decision endpoints (marked EXPERIMENTAL: endpoint schemas and
model ids vary by provider; check your provider's current docs — e.g.
the typesafe models served through OpenRouter — before relying on it).
The protocol is deliberately tiny so the ecosystem of decision APIs can
grow around it.

## The experiment plan (how we'll know it's useful)

Three play-tests, in order, each with a falsifiable hypothesis:

| # | Experiment | Hypothesis | Measure |
|---|---|---|---|
| 1 | **Selection quality**: same organism, heuristic EV vs decision-model EV on script selection | decision-model selection relieves more total tension per 100 ticks, at equivalent action count | total tension discharged; action count; decision-model spend |
| 2 | **Calibration honesty**: do stated confidences match observed outcomes? | confidence correlates with realized success (bins within ±0.15) | reliability diagram over 200 decisions |
| 3 | **Cost/benefit at the margin**: heuristic vs decision-model vs LLM at each choice point | decision models dominate LLMs on cost per unit of selection quality for high-frequency, low-nuance choices; LLMs win on rare, high-nuance proposals | quality per $ per 1k decisions |

If (2) fails — confidences don't track outcomes — the right response is
to *stop using them as probabilities* and treat them as rankings only,
and to say so in the docs. Calibration claims are empirical, not
marketing.

## Honest unknowns

- **Schema churn**: decision-model APIs are young; request/response
  shapes will move. The kernel keeps a protocol + one thin client and
  refuses to hardcode more.
- **Latency in the tick loop**: a 150ms decision inside a tick that is
  otherwise microseconds matters only if you call it every tick; the
  design favors calling decision models at *choice points*
  (conflicts, ties, prioritization), not per tick.
- **Whose calibration?** Calibrated on whose distribution? An organism's
  world drifts; confidences calibrated on yesterday's world need
  re-checking — which is itself a tension the organism can feel
  (an "assumption rot" drive, as in example 03).
