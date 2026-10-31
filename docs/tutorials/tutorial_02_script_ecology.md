# Tutorial 02 — The Script Ecology: Birth, Starvation, Death, Dreams

*Goal: watch a population of scripts live and die, and read a necrology.
Time: ~25 minutes. Builds on [Tutorial 01](tutorial_01_first_world.md).*

An agent in this kernel is not a prompt — it is a **population**. This
tutorial makes population dynamics visible: scripts compete, the losers
starve, the hopeless die (recorded forever), and dreams spawn variants
nobody designed.

## Step 1 — a world with too many behaviors

```python
# tutorial02.py
from cognitive_ecology import Outcome, Runtime, Script

rt = Runtime(seed=11, top_k=1)          # ONE winner per tick: scarcity
rt.declare_why("survive the winter", node_id="why:root")
rt.tensions.add("hunger", growth=0.04)
rt.graph.upsert("cache:acorns", "cache", {"acorns": 12}, tick=0)

def make_forager(n, efficiency):
    def act(ctx, eff=efficiency):
        cache = ctx.graph.get("cache:acorns")
        acorns = cache.props.get("acorns", 0)
        if acorns <= 0:
            return Outcome(False, "cache empty")
        ctx.graph.upsert("cache:acorns", "cache", {"acorns": acorns - 1}, tick=ctx.tick)
        ctx.tensions.relieve("hunger", eff)
        return Outcome(True, f"ate one (eff {eff})")
    return Script(name=f"forage-{n}", why_node="why:root", owner="squirrel",
                  relieves=("hunger",), focus=("cache:acorns",), act=act)

class Squirrel:
    id, why_node = "squirrel", "why:root"
    def __init__(self, rt_):
        for n, eff in [(1, 0.5), (2, 0.3), (3, 0.4), (4, 0.2)]:
            rt_.ecology.spawn(make_forager(n, eff), tick=0)
    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner="squirrel")
    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)

rt.register(Squirrel(rt))
```

Four foragers, one cache, one winner per tick. `forage-1` is the most
efficient (relieves 0.5 hunger); the others are objectively worse. What
should happen?

## Step 2 — run it and read the market

```python
for report in rt.run(60):
    pass  # let it live; we'll read the summary
for s in rt.ecology.alive():
    print(f"{s.name:10s} fires={s.fires:3d} success={s.success_rate:.2f} "
          f"starve={s.starve}")
print("market:", rt.market.stats())
```

Expected shape: `forage-1` wins early and often; the others starve in
proportion to their efficiency. When the cache empties, *everybody*
starts failing honestly — success rates fall together, and the organism
goes hungry no matter who wins. The market can only choose among the
scripts that exist; it cannot conjure food.

## Step 3 — death, and the record that outlives it

Scripts that never win and never fire, starving past the ecology's
limits, die:

```python
deaths = rt.ecology.necrology()
for d in deaths:
    print(f"{d.name:12s} died@{d.tick:3d} fires={d.fires} "
          f"reason={d.reason}")
```

A death is a **record**, not an erasure: name, tick, reason, lifetime
fires, lineage (`parent`, `generation`). This is the necrology, and it
is the difference between an agent that forgets its failures and an
organism that *mourns* them. When you ask "why doesn't this organism
forage anymore?", the necrology answers with evidence.

## Step 4 — dreams (parameter mutations)

Sleep is where the population explores. Let's force a quiet moment and
watch dreams:

```python
# empty the cache so nothing is worth doing
rt.graph.upsert("cache:acorns", "cache", {"acorns": 0}, tick=rt.tick_no)
quiet = rt.run(20)                     # market clears nothing -> idle -> sleep
print("slept on ticks:", [r.tick for r in quiet if r.slept])
print("sleeper stats:", rt.sleeper.stats)
for s in rt.ecology.alive():
    print(f"{s.name:14s} gen={s.generation} parent={s.parent} "
          f"params={s.params}")
```

Every sleep cycle can mutate up to two live scripts: a **dream** is a
newborn variant with jittered numeric `params` and `success_rate` reset
to 0.5 — the benefit of the doubt. The dream must then *earn* its place
in tomorrow's market. Most die. The ones that survive are the closest
thing this kernel has to invention.

Note what dreams are *not*: not generated code, not prompt rewrites.
Mutation explores the parameter space; only LLM proposals (Tutorial 04)
explore the behavior space — and even those are confined to the audited
action library.

## Step 5 — adoption: resurrecting a population from disk

```python
rt.save("runs/tutorial02")

def rebuild(r):
    class S2(Squirrel):
        def __init__(self, rt_):
            for n, eff in [(1, 0.5), (2, 0.3), (3, 0.4), (4, 0.2)]:
                r.ecology.adopt(make_forager(n, eff), tick=rt_.tick_no)
    r.register(S2(r))

rt2 = Runtime.load("runs/tutorial02", attach=rebuild)
for s in rt2.ecology.alive():
    print(f"{s.name:10s} fires={s.fires:3d} success={s.success_rate:.2f}")
```

`adopt()` re-attaches saved track records to code-defined scripts. The
squirrel you load is the squirrel you saved: same memories, same
success-rate scars, same necrology. **Behavior is code; history is
files.**

## What you learned

- Scarcity (`top_k`) is what makes a population *act like* a population.
- Failure is honest (outcomes record it) and *consequential* (EV decays)
  without any punishment logic.
- Death is a record; the necrology is an audit trail of everything the
  organism stopped being.
- Dreams are cheap experiments: parameter jitter, judged by tomorrow's
  market.
- `adopt()` is the persistence ceremony for populations.

## Exercises

1. Make `forage-4` the only script with access to a *second* cache. Who
   survives now? (Hint: opportunity beats efficiency when the resource
   differs.)
2. Lower `starve_limit` (constructor arg on `ScriptEcology`) to 15 and
   watch the ecology get ruthless.
3. Add a `hoard` script that *adds* acorns to the cache instead of
   eating. Does the market value a provider as much as a consumer?
   (This is the "who funds public goods" question, in squirrel form.)

Next: [Tutorial 03 — tuning the attention market](tutorial_03_attention_market.md).
