# Attention Economics

*Cognition is an economy, not a queue.*

## The formula

```
attention = urgency * justification * opportunity * novelty * expected_value
```

All five factors are clamped to [0, 1] and **multiplied**. Any factor at
zero vetoes the bid entirely. This is the single most important design
decision in the kernel, so it deserves the clearest defense:

**Why multiplication and not a weighted sum?** Because the factors are
*veto conditions*, not bonuses. Consider an additive scheme: `score =
w1·urgency + w2·justification + ...`. A dying habit with urgency 1.0 and
justification 0.0 (its WHY root was killed) still scores `w1` — enough
to run whenever the market is quiet. The multiplicative law makes that
arithmetically impossible: no urgency, however extreme, buys past a dead
purpose. The formula encodes the ethics of the organism.

## The five factors

| Factor | Question it answers | Where it comes from |
|---|---|---|
| `urgency` | How much does an unmet drive hurt, right now? | `max(level)` over the tensions the script `relieves` (`tension.py`) |
| `justification` | Is this script's purpose chain alive? | `why.justification(node)`: 0.0 if any DEAD ancestor; else the alive fraction of the chain |
| `opportunity` | Are the preconditions true right now? | the script's `when(ctx)` trigger |
| `novelty` | Has the watched patch of world changed since last look? | fraction of `focus` nodes seen recently (nodes that don't exist yet count as maximally novel — a script that would *create* its focus is not vetoed) |
| `expected_value` | What did this action earn before? | the script's `success_rate` (EMA, α=0.3) — or a `Simulator` rollout if you inject one |

## A worked example, by hand

The critter at tick 40 of `experiments/minimal_world.py`, roughly:

| Script | urgency | justification | opportunity | novelty | expected_value | attention |
|---|---|---|---|---|---|---|
| forage | 0.12 (energy low-ish) | 1.00 | 1.00 (berries ripe) | 1.00 | 0.99 | **0.119** |
| drink  | 0.12 | 1.00 | 1.00 | 1.00 | 1.00 | **0.120** |
| explore| 0.06 (curiosity low) | 1.00 | 1.00 | 1.00 | 1.00 | **0.060** |
| rest   | 0.12 | 1.00 | 1.00 | 0.30 (no focus) | 0.99 | **0.036** |

`top_k = 2` ⇒ drink and forage clear; explore and rest starve this tick.
Nobody is punished; starvation is just counted. If the same scripts keep
starving for dozens of ticks without ever firing, the ecology eventually
lets them die — into the necrology, with their records.

## Market mechanics

- **Clearing:** once per tick, `AttentionMarket.clear(top_k)` ranks all
  submitted bids by `(-attention, src, label)` — the tie-break is
  deterministic, so the same world always produces the same choices.
- **The veto law:** bids with attention ≤ 0 go to the starved list and
  *never* clear — not even when the market is completely empty. An
  organism with nothing worth doing idles toward sleep rather than
  spending budget on vetoed actions. Scarcity is not desperation.
- **Resource conflicts:** bids may name an exclusive `resource` (e.g.
  `"body"`, `"mic"`). Among winners claiming the same resource, the
  higher-attention bid runs and the others **yield** — recorded in a
  DECISION event, not punished.
- **Cause chaining:** every winner's DECISION event becomes the `cause`
  of every event its action emits. The chain from decision to effect is
  always walkable backwards.

## Tuning guide

| Symptom | Diagnosis | Fix |
|---|---|---|
| Organism obsessed with one behavior | that behavior's tension grows faster than anything relieves it | lower the tension `growth` — the market is innocent, the diet is guilty |
| Organism does nothing | every bid vetoed: check each factor | most often `opportunity` (triggers never true) or `justification` (WHY chain broken) |
| One script wins forever | novelty of its focus stays 1.0 because acting refreshes it | that's often correct (a pond is always drinkable); if not, make the action stop refreshing its own focus, or add competition |
| New scripts never get a chance | `expected_value` starts at 0.5 and champions sit at 1.0 | newborns start at 0.5 on purpose; give them a `when` that fires when champions are unavailable, or lower `top_k` pressure by raising it |
| Everything fires at once | `top_k` too high for the world's richness | lower `top_k` — scarcity is the point of the exercise |

## Anti-patterns

- **Urgency-only minds.** If you only ever set urgency and leave the rest
  at 1.0, you have built a priority queue with extra steps. The power is
  in the vetoes.
- **Novelty spam.** A script whose focus is the entire graph gets
  novelty ≈ churn, always. Focus should be the *patch* the script acts
  on, not the world.
- **Fighting the veto.** If a bid keeps getting vetoed, the market is
  telling you something: the drive isn't real (urgency), the purpose is
  dead (justification), the moment is wrong (opportunity), nothing
  changed (novelty), or the action never pays (expected_value). Fix the
  factor; don't bypass the market.

## The staleness term (for LLM agents)

A subtle emergent problem found while dogfooding: a proposer's *spawned
scripts* can outcompete the proposer itself (their success rates rise
above its accept rate), starving the organism of new ideas forever. The
fix is honest homeostasis: the proposer's urgency includes a *staleness*
term — an agent that has not proposed in ~30 ticks gets bored with its
own repertoire (`agents/orchestrator.py`, `LLMAgent.bid`). Watch for the
same pattern in your own organisms: organs that feed the market need
their own drives, or the market will quietly retire them.
