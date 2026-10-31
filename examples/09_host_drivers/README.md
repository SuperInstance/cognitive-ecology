# Example 09 — Hosting an Organism

**Three hosting shapes, one contract: the driver owns WHEN, never WHAT.**

```bash
python examples/09_host_drivers/main.py   # keyless, offline, ~2s
```

| Shape | What it shows |
|---|---|
| **1 · game loop** | fixed-timestep accumulator — frame-rate independent (60 fps and 30 fps produce a byte-identical life), with the float-undershoot epsilon every accumulator needs |
| **2 · wall-clock session** | `WallClockDriver`: drift-free pacing against a monotonic schedule, checkpoint cadence (`save_every`), host-initiated stop, and a `DriverReport` receipt |
| **3 · cron tick** | the load → tick a budget → save → exit shape behind every scheduler entry and systemd timer, including the attach rite (rebuild behavior in code, `adopt()` the saved track records) |
| **recipe** | rotating checkpoints — keep the last K saves so a corrupt `current` costs one session, not the organism |

The demo injects a fake clock into the driver (`sleep_fn`/`monotonic_fn`
are injectable) so a "3-second session" runs in microseconds — the same
seam tests use, and the reason driving is deterministic by construction.

Docs: `docs/10_host_integration.md` — the contract, the host surface
(`tick`/`run`/`bus.emit`/`graph.upsert`/`save`/`load`/`market_log`),
the world-not-bus ingest law, and the FastAPI lifespan recipe.
