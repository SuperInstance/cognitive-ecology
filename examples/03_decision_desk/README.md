# Example 03 — The Decision Desk (decision models + commitments)

**What this teaches:** how **decision models** (typed outputs with
calibrated confidence — e.g. typesafe.ai's Jev, or OpenAI's decision
APIs) plug into the ecology as a second citizen class. A small portfolio
organism holds *assumptions as WHY nodes*, feels *tensions* (assumption
rot, drawdown anxiety), and each tick a **decision policy** chooses among
candidate actions. Every choice becomes a **hash-chained commitment** in
the organism's identity — an auditable trail of what it decided and why.

**Run it:**

```bash
# keyless: the built-in heuristic policy (calibrated scores, no network)
python examples/03_decision_desk/main.py

# with a decision model through any OpenAI-compatible endpoint
# (endpoint + model are env-driven; see docs/08_decision_models.md):
export TYPESAFE_BASE_URL=https://openrouter.ai/api/v1
export TYPESAFE_API_KEY=...
export TYPESAFE_MODEL=<current typesafe model id on your provider>
python examples/03_decision_desk/main.py
```

**What you should see:** a decisions table (tick, market state, action,
confidence, tension relief), then the commitment chain with `verify() ==
True`, and the organism's self-model. Kill the "regime holds" assumption
and watch rebalancing become questionable rather than quietly continuing
on a dead premise.

**The point:** the market proposes, the decision model *chooses with a
confidence*, the WHY tree decides whether the choice may even be
considered, and identity remembers the choice forever. Four layers, one
clean pipeline.
