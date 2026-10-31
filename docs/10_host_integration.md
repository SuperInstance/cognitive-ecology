# Host Integration: Making an Organism Live in Your App

*Wave-1's finding 4: "`rt.bus.emit` is undiscoverable; wall-clock and
schedulers are everyone's first build; the cron/game-loop/FastAPI
patterns are folklore, not docs." This guide is the folklore, upgraded
to law.*

## The contract

> **A driver owns WHEN. It must never influence WHAT.**

The kernel's time is ticks — an integer the organism advances itself.
Same seed + same code + same ingested events = the same life, whether
it ran in two seconds or two weeks (pinned by test: a driven run and a
plain `rt.run(n)` produce byte-identical event streams). Wall-clock
time never enters the organism — not in events, not in decisions, not
in seeds. If you find yourself passing a timestamp into `tick()`, stop:
persist the fact into the world graph and let the organism perceive it
like any other fact.

## The host surface (everything you need, one table)

| Need | API | Notes |
|---|---|---|
| advance time | `rt.tick()` / `rt.run(n)` | the only way time moves |
| pace it | `WallClockDriver(interval).run(rt, ...)` | drift-free, graceful Ctrl-C, checkpoint cadence, `DriverReport` receipt |
| say something happened | `rt.bus.emit(EventKind.SIGNAL, (target, text), src="host", ts=rt.tick_no)` | events are what HAPPENED — volatile, windowed |
| make something true | `rt.graph.upsert(node_id, kind, props, tick=rt.tick_no)` | the graph is what IS — durable, walkable |
| ask the organism anything | `rt.market_log.summary()`, `rt.why.verdict(...)`, `rt.tensions.snapshot()` | read models; never perturb |
| persist / restore | `rt.save(path)` / `Runtime.load(path, attach=...)` | atomic writes; `load` verifies the receipt at the door |
| observe every decision | `rt.market_log` | the read model (docs/09) |

## The world-not-bus ingest law

The wave-1 play-test found example 04 teaching a lossy pattern: player
asks were emitted on the event bus and read back through a 10-event
window — racing the top-k scheduler. An ask Merle didn't answer within
ten events was forgotten forever, even by the remember-everything NPC
after a restart. The law that fixes it:

> **Ingest facts into the WORLD GRAPH at the moment you learn them.
> The bus is for what happened; the graph is for what is.**

```python
def player_visit(rt, asks):
    for ask in asks:
        qid = f"question:{slug(ask)}"
        rt.graph.upsert(qid, "question", {"text": ask}, tick=rt.tick_no)
        rt.graph.link("player:you", qid, "asked", tick=rt.tick_no)
        rt.bus.emit(EventKind.SIGNAL, ("npc", ask), src="player:you",
                    ts=rt.tick_no)   # the bus may still narrate
    rt.run(4)
```

The ask is now durable (survives restarts), walkable (`edges_of`), and
answerable whenever the organism gets to it — attention decides WHEN
the answer happens; ingest decides WHETHER it is remembered.

## Recipe 1 — the game loop (fixed-timestep accumulator)

```python
TICK_DT = 1.0 / 5      # five organism ticks per simulated second
EPS = 1e-9             # float undershoot guard — not decoration

acc = 0.0
for dt in frame_deltas:            # whatever the render loop gives you
    acc += dt
    while acc + EPS >= TICK_DT:
        rt.tick()
        acc -= TICK_DT
```

Frame-rate independent: 300 fps or 30 fps, the organism sees the same
tick stream. **The accumulator's epsilon**: summing `1/30` ninety
times gives `2.9999999999999994` — an epsilon-free accumulator
silently drops the third tick. Example 09 shipped without the epsilon
and its own 30 fps twin failed its identity check in the demo's first
run; the epsilon is the scar, kept visible.

## Recipe 2 — the wall-clock session

```python
from cognitive_ecology import WallClockDriver

driver = WallClockDriver(interval=0.1)          # seconds per tick
report = driver.run(
    rt,
    seconds=3600,                                # any subset of stop
    max_ticks=36_000,                            # conditions may be
    save_every=500, save_path="runs/organism",   # given; first wins
    on_tick=lambda r: None,                      # False stops ("player quit")
)
# report: ticks, wall_seconds, stopped_by (duration|max_ticks|keyboard|
#         host|error), saves, mean_tps() — the host's receipt
```

Scheduling is against a monotonic `next_at` (absolute slots, not
relative sleeps), so a 10 Hz driver does 600 ticks a minute, not
600-minus-sleep-jitter. Ctrl-C is graceful: the report says
`keyboard`, and the organism is checkpointed. `sleep_fn` /
`monotonic_fn` are injectable — tests drive a "one-hour session" in
microseconds (see `tests/test_drivers.py`).

## Recipe 3 — the cron tick (and systemd timers)

One line of cron, six lines of Python:

```cron
* * * * * cd /srv/app && python -m app.tick_organism
```

```python
# app/tick_organism.py — advance the organism 5 ticks per minute, forever
from my_app.organism import build, attach          # YOUR code
from cognitive_ecology import Runtime

rt = Runtime.load("runs/organism", attach=attach) if exists() else build()
rt.run(5)
rt.save("runs/organism")
```

`attach()` is the rite that rebuilds behavior in code and `adopt()`s
each script's saved track record — closures are code, not data. The
ergonomic version (idempotent `ensure_*` builders) is on the roadmap;
until then, copy the pattern from `examples/09` (`_attach_desk`) or
`examples/04` (`attach`).

### Rotating checkpoints

`save()` is atomic (temp + rename), so a crash costs nothing mid-write
— but a corrupt `current` costs everything after it. Rotate:

```python
import shutil
from pathlib import Path

def save_rotated(rt, base: Path, keep: int = 2):
    for k in range(keep, 0, -1):                  # newest -> oldest shift
        src = base / ("current" if k == 1 else f"checkpoint.{k - 1}")
        dst = base / f"checkpoint.{k}"
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            src.rename(dst)
    rt.save(str(base / "current"))
```

A bad `current` now costs one session: the previous checkpoint is one
rename away. Bound the event log too — `rt.compact_events(path, keep=N)`
truncates under a snapshot+receipt (round 20b).

## Recipe 4 — the web app (FastAPI lifespan)

The organism ticks in the event loop itself — a native async loop, one
`await asyncio.sleep(interval)` per tick. **Never put a blocking
`WallClockDriver.run()` inside an asyncio task**: it blocks the whole
event loop (the app never finishes startup, no request is ever served
— this exact bug shipped in the first draft of this recipe and was
caught by the wave-2 live probe). `WallClockDriver` is for threaded
and process hosts; this is its async translation, same contract:

```python
# app/main.py                               pip install fastapi uvicorn
import asyncio, time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from cognitive_ecology import Runtime

rt = build()                                        # your organism
TICK_INTERVAL = 0.05                                # seconds per tick

async def organism_loop(stop_after: float = 3600.0):
    end = time.monotonic() + stop_after
    while time.monotonic() < end:
        rt.tick()                                   # in the loop thread:
        await asyncio.sleep(TICK_INTERVAL)          # requests interleave
                                                    # safely between ticks

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(organism_loop())
    yield                                           # app serves
    task.cancel()                                   # shutdown stops the body

app = FastAPI(lifespan=lifespan)

@app.post("/ask")
def ask(text: str):
    # the world-not-bus law: facts go into the graph at ingest time
    qid = f"question:{abs(hash(text))}"
    rt.graph.upsert(qid, "question", {"text": text}, tick=rt.tick_no)
    rt.graph.link("user:web", qid, "asked", tick=rt.tick_no)
    return {"ok": True, "tick": rt.tick_no}

@app.get("/state")
def state():
    return {"tick": rt.tick_no, "market": rt.market_log.summary(),
            "tensions": rt.tensions.snapshot()}
```

Single-threaded by construction: ticks and request handlers take
turns on the event loop, so a request can never mutate the graph
mid-tick. (The docs' own recipe is executed against a live ASGI
transport in `tests/test_host_recipes.py` — a recipe that has not run
is a rumor, not a recipe.)

For heavier use, run the organism in its own process and let the web
app read its outputs (manifests + market log are files — see
`run_rounds.py`); a web process that dies then costs nothing the
organism cares about.

## Cost and determinism notes (declared, per ideation 015)

- **One tick is cheap and bounded**: O(bids · log bids) for the
  clearing, plus consolidation over the tick's events. The 10k-tick
  soak measured 2.3k–6.4k ticks/s single-threaded on a laptop core
  (degrading as journals grow — compaction restores it; ADR-0014).
- **But the kernel has no resource envelope yet**: no memory ceiling,
  no health surface, no multi-process guard (OPEN_QUESTIONS #15). A
  driver must not make that missing physiology load-bearing: set
  `max_ticks` budgets, rotate checkpoints, and put an external
  watchdog (systemd `Restart=`, k8s liveness) around long-lived
  organisms until the physiology round ships.
- **Reproducibility recipe**: record the seed, the code commit, and
  the ingested events in order (`run_rounds.py` manifests do this) —
  that triple is the complete definition of a life.

## Where to see it all working

`examples/09_host_drivers/` runs all three shapes plus checkpoint
rotation, keyless, in about two seconds — including the byte-identical
frame-rate twin and the host-stop receipt.
