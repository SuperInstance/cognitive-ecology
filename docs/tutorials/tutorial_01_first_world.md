# Tutorial 01 — Your First World

*Goal: build a working organism from scratch and understand every line.
Time: ~20 minutes. Prerequisites: [Quick Start](../01_quick_start.md).*

We will build a lighthouse keeper whose job is to watch the sea. It has
one purpose, one drive, and two scripts that disagree about how to spend
the day. By the end you will have exercised L0, L2, L4, L5 and L6 — and
you'll know where every number comes from.

## Step 1 — the body and the purpose

```python
# tutorial01.py
from cognitive_ecology import Runtime

rt = Runtime(seed=7, top_k=1)   # a body with a 1-action-per-tick budget
rt.declare_why("the light stays lit and the sea is watched",
               node_id="why:root")
```

Two lines of setup, two laws already active: nothing may run without a
WHY chain, and that WHY can never be deleted. `top_k=1` makes the
economics stark — every tick, exactly one behavior wins.

## Step 2 — a drive

```python
rt.tensions.add("vigilance", growth=0.04,
                description="the sea must be watched")
```

Drives are where urgency comes from. This one grows 0.04 per tick: from
0 to "unbearable" in 25 ticks unless something relieves it. Growth rates
are your organism's temperament — write them down where teammates can
see them.

## Step 3 — the world

```python
rt.graph.upsert("light:main", "light", {"oil": 1.0}, tick=0)
rt.graph.upsert("sea:horizon", "sea", {"ships_seen": 0}, tick=0)
```

The World Graph is the organism's knowledge *with a biography*: every
node remembers when it was born and last seen. For now, two nodes: the
lamp and the horizon.

## Step 4 — two scripts that disagree

```python
from cognitive_ecology import EventKind, Outcome, Script

def act_watch(ctx):
    ctx.tensions.relieve("vigilance", 0.3)
    ctx.graph.seen(["sea:horizon"], tick=ctx.tick)
    ctx.emit(EventKind.STATE, ("sea:horizon", {"watched": 1}), src="keeper")
    return Outcome(True, "scanned the horizon")

def act_trim_wick(ctx):
    light = ctx.graph.get("light:main")
    oil = light.props.get("oil", 1.0)
    if oil < 0.2:
        return Outcome(False, "oil too low")     # honest failure
    ctx.graph.upsert("light:main", "light", {"oil": oil - 0.1}, tick=ctx.tick)
    ctx.tensions.relieve("vigilance", 0.1)       # a little peace of mind
    return Outcome(True, "wick trimmed")

class Keeper:
    id, why_node = "keeper", "why:root"
    def __init__(self, rt_):
        rt_.ecology.spawn(Script(
            name="watch", why_node="why:root", owner="keeper",
            relieves=("vigilance",), focus=("sea:horizon",), act=act_watch), tick=0)
        rt_.ecology.spawn(Script(
            name="trim-wick", why_node="why:root", owner="keeper",
            relieves=("vigilance",), focus=("light:main",), act=act_trim_wick), tick=0)
    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner="keeper")
    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)

rt.register(Keeper(rt))
```

Read `Script(...)` as a sentence: *"watch relieves vigilance by scanning
the horizon it watches."* The ecology turns that sentence into a bid:
urgency = current vigilance, justification = WHY-chain health,
opportunity = trigger (always, here), novelty = how fresh the horizon
is, expected_value = its own track record.

## Step 5 — live

```python
for report in rt.run(40):
    if report.ran:
        print(f"tick {report.tick:3d}: {', '.join(report.ran)}"
              f"  vigilance={report.tensions['vigilance']:.2f}")
print(rt.report())
```

You should see the two behaviors alternate — watch dominates while
vigilance is high; trim-wick sneaks in when the horizon is fresh. When
the oil runs low, `trim-wick` starts *failing honestly*: its
`expected_value` decays, it stops winning, and the organism becomes a
watcher that knows its lamp is dying. Nothing crashed. The economics
adapted.

## Step 6 — kill the purpose (do this, seriously)

```python
rt.why.kill("why:root", reason="the lighthouse is decommissioned", tick=41)
for report in rt.run(5):
    print(report.tick, report.ran)      # [] [] [] [] []
print(rt.why.conservation())            # invariant_ok: True
```

The organism stops. It is not deleted — every script, every record,
every memory is still there, merely *questionable* (UNKNOWN). Bring it
back:

```python
rt.why.resurrect("why:root", reason="the village changed its mind", tick=46)
print(rt.run(5)[-1].ran)                # life resumes
```

## Step 7 — make it survive you

```python
rt.save("runs/tutorial01")
rt2 = Runtime.load("runs/tutorial01",
                   attach=lambda r: r.register(Keeper(r)))
rt2.run(10)
```

Behavior lives in code (you re-declare the Keeper); history lives in
files (the graph, WHY tree, event log, script stats come back). That
split *is* persistence here.

## What you built

A complete organism: a conserved purpose, a homeostatic drive, a world
with memory, two competing behaviors, a market with a budget — and a
death and resurrection with an audit trail. **~70 lines.**

## Exercises

1. Add a `storm` event that burdens vigilance by 0.3 when it hits. Watch
   the market's reaction.
2. Give `watch` a `when` that requires `oil > 0.2` on the lamp. What
   happens to the organism when the oil runs out completely? (Dark. By
   design.)
3. Add a third tension `loneliness` with no reliever and watch it pin at
   1.0 — that's the market telling you a need is unmet. Then add a
   script that relieves it.
4. Change `top_k` to 2. When do the two behaviors stop competing?

Next: [Tutorial 02 — the Script Ecology](tutorial_02_script_ecology.md),
where scripts are born, starve, die and dream.
