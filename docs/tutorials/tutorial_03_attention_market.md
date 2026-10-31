# Tutorial 03 — Tuning the Attention Market

*Goal: develop a feel for the five factors — and the vetoes. Time: ~25
minutes. Builds on [Tutorial 02](tutorial_02_script_ecology.md).*

The market is the organism's character. Same scripts, different factors:
a different animal. This tutorial is a series of controlled experiments —
one variable each — on a tiny lab organism.

## The lab

```python
# tutorial03.py
from cognitive_ecology import Outcome, Runtime, Script

def build(urgency_src="hunger",        # what the script relieves
          novelty_focus=("patch:a",),  # what it watches
          when=None,                   # opportunity gate
          top_k=1):
    rt = Runtime(seed=3, top_k=top_k)
    rt.declare_why("study attention", node_id="why:root")
    rt.tensions.add("hunger", growth=0.05)
    rt.tensions.add("curiosity", growth=0.02)
    rt.graph.upsert("patch:a", "patch", {}, tick=0)
    rt.graph.upsert("patch:b", "patch", {}, tick=0)

    fired = []
    def act(ctx):
        fired.append((ctx.tick, "act"))
        ctx.tensions.relieve(urgency_src, 0.4)
        ctx.graph.seen(list(novelty_focus), tick=ctx.tick)
        return Outcome(True, "did the thing")

    class Lab:
        id, why_node = "lab", "why:root"
        def __init__(self):
            rt.ecology.spawn(Script(
                name="act", why_node="why:root", owner="lab",
                relieves=(urgency_src,), focus=novelty_focus,
                when=when, act=act), tick=0)
        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="lab")
        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt.register(Lab())
    return rt, fired
```

## Experiment 1 — watch urgency and justification multiply

```python
rt, fired = build()
for report in rt.run(6):
    print(report.tick, report.ran, report.tensions)
```

The script fires when hunger is high enough that `urgency × 1.0 × 1.0 ×
novelty × EV` beats zero — which is always true here, so it fires every
tick and hunger oscillates. Now break the WHY *without* touching the
market:

```python
rt.why.kill("why:root", reason="study interrupted", tick=7)
print([r.ran for r in rt.run(3)])    # [[], [], []]
```

**No market setting can outrank a dead purpose.** Urgency keeps growing
(peek at `rt.tensions.snapshot()`); the bids never even enter the
market. That is the multiplicative law being useful, not decorative.

## Experiment 2 — opportunity: the politeness factor

```python
rt, fired = build(when=lambda ctx: ctx.tensions.level("hunger") > 0.4)
print([r.ran for r in rt.run(12)])
```

The trigger gates *when the bid may exist*. The organism now eats in
bursts: hungry → eat → sated → wait. Triggers are where you encode
etiquette ("only nag above 0.2") and preconditions ("only when the door
is open"). See `examples/05_personal_journal` for the nag-with-manners
pattern in full.

## Experiment 3 — novelty: attention to change

```python
rt, fired = build(novelty_focus=("patch:b",))   # a patch nothing refreshes
print([r.ran for r in rt.run(8)])
```

Wait — it still fires every tick? Look closer at `act`: it calls
`ctx.graph.seen(...)` on its own focus, refreshing the novelty it is
judged by. Self-refreshing focus is the "pond is always drinkable"
pattern — often correct, sometimes a tyranny (a script that always finds
itself interesting). To make novelty actually gate:

```python
def act(ctx):                     # does NOT touch its own focus
    ctx.tensions.relieve("hunger", 0.4)
    return Outcome(True, "checked the news")
```

Now novelty decays (patch:b is never refreshed) and attention falls
toward zero: the organism looks once, then stops looking at a patch that
never changes. **Design rule: a script should not refresh the novelty it
is judged by — unless "being available" is genuinely part of its job.**

## Experiment 4 — expected_value: the learning factor

```python
rt, fired = build()
rt.ecology.get("act").success_rate = 0.05   # a hopeless track record
rt.run(4)
```

EV enters the product directly: with everything else at 1.0 and hunger
at 0.5, attention is `0.5 × 0.05 = 0.025` — it still clears (nothing
else bids), but watch what happens when you add a competitor with EV
0.8. EV is also where `Simulator` rollouts plug in
(`simulations.py`) when you want forward-looking estimates instead of
track records.

## Experiment 5 — the veto law (do not skip)

```python
rt, fired = build()
rt.tensions.relieve("hunger", 1.0)          # hunger exactly 0
print([r.ran for r in rt.run(3)])           # [[], [], []] — nothing runs
```

Urgency 0 → attention 0 → the bid never clears — **not even though the
market is completely empty**. The organism would rather idle toward
sleep than spend budget on a vetoed action. Before this law existed, a
sated drink script drank forever (found by play-testing example 01; see
`docs/07_playbook.md`). Scarcity is not desperation.

## Experiment 6 — resource conflicts and yielding

```python
rt, fired = build(top_k=3)
from cognitive_ecology import Script
rt.tensions.add("boredom", growth=0.05)
rt.ecology.spawn(Script(
    name="sing", why_node="why:root", owner="lab", relieves=("boredom",),
    resource="voice", act=lambda ctx: Outcome(True, "sang")), tick=0)
rt.ecology.spawn(Script(
    name="announce", why_node="why:root", owner="lab", relieves=("boredom",),
    resource="voice", act=lambda ctx: Outcome(True, "announced")), tick=0)
for report in rt.run(4):
    print(report.tick, "ran:", report.ran, "yielded:", report.yielded)
```

Two scripts, one `voice`. The higher-attention bid runs; the loser
**yields** — recorded in the tick report and the DECISION events, never
punished. Yielding is how organisms with one mouth coordinate many
impulses.

## The tuning cheat-sheet

| You want | Turn this |
|---|---|
| more urgency → | tension `growth` up, or relief amounts down |
| less obsessive → | relief *above* net growth, so drives actually reach zero |
| politeness → | `when` thresholds (`tension_above:name:x`) |
| curiosity about a patch → | `focus` on it, and let someone else refresh it |
| an organ that wins ties → | give it a fresher focus (novelty) — or accept the alphabetical tie-break |
| ruthless ecology → | `ScriptEcology(starve_limit=...)` down |
| calm organism → | `top_k` down; let sleep happen |

## Exercises

1. Build an organism where two scripts relieve the *same* tension but
   one watches a fast-changing patch and the other a slow one. Describe
   the division of labor that emerges.
2. Make a script whose `when` requires a *contradiction* (a graph node
   in a state it shouldn't be). Congratulations: you've built a tripwire
   that only attention economics could need.
3. Set `top_k=5` with only two scripts, then read
   `market.stats()["clear_rate"]`. What does a permanently-clearing
   market tell you about your scarcity?

Next: [Tutorial 04 — LLM agents and the caching game](tutorial_04_llm_agents_and_caching.md).
