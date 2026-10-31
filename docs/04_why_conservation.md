# The WHY Conservation Law

*The crown of the stack, explained completely.*

## The law

> 1. A WHY node is **never deleted**. There is no API for it.
> 2. Purpose has four states: **ALIVE, DEAD, UNKNOWN, ABSENT**.
> 3. Killing a node cascades its living descendants to **UNKNOWN** —
>    *questionable*, not gone. They can be revived.
> 4. Every transition is recorded in an **append-only necrology**.

In one line: **purpose is a conserved quantity.** An organism can lose
its purpose, doubt its purpose, even contradict its purpose — but it can
never *erase* its purpose.

## Why this law exists

Agents die for a boring reason: their purpose is deletable. It lives in
a prompt someone edits, a ticket someone closes, a context window that
evaporates at the end of a session. Every "why are we doing this?" that
can be answered with "it got deleted" is an organism that will eventually
be deleted.

Conserve the WHY and three things become possible that were not before:

- **Auditability** — "why did the agent do that?" always has an answer,
  with tick numbers and a causal chain. Nothing was quietly dropped.
- **Revival** — a questioned purpose (UNKNOWN) can come back when new
  evidence arrives. A deleted purpose cannot come back at all.
- **Honest death** — an organism whose root purpose is DEAD *stops*. It
  does not keep foraging on momentum. Stopping on dead purpose is the
  integrity condition of the whole system.

## The four states

| State | Meaning | Entered by | Left by |
|---|---|---|---|
| `ALIVE` | asserting life; heartbeats accepted | `declare` (default), `revive`, `resurrect`, `activate` | `kill`, `park` |
| `DEAD` | explicitly killed; terminal | `kill` | `resurrect` (requires evidence) |
| `UNKNOWN` | *questionable* — an ancestor died | cascade from `kill` | `revive`, cascade from ancestor revival |
| `ABSENT` | declared but parked/draft | `declare(state=ABSENT)`, `park` | `activate` |

## Cascade semantics, precisely

```
kill(A):
    A                     -> DEAD      (recorded)
    every ALIVE descendant -> UNKNOWN  (recorded, reason names A)

revive(X)  [X is UNKNOWN]:
    X                      -> ALIVE    (recorded)
    every UNKNOWN descendant -> ALIVE   (recorded, "cascade: X revived")

resurrect(D)  [D is DEAD, requires a substantive reason]:
    D                      -> ALIVE    (recorded, with the evidence)
    then cascades like revive
```

DEAD children stay DEAD through a parent's revival: an explicit kill is a
stronger signal than a cascade question. UNKNOWN is the only state that
cascades both ways.

## The heartbeat question

Every tick, every component must answer:

```python
rt.why.why_should_this_run(component.why_node)   # -> bool
```

The verdict walks the chain leaf → root. All ALIVE: run. Otherwise: the
most proximate non-ALIVE node is named as the blocker:

```python
rt.why.verdict("why:map")
# WhyVerdict(ok=False, reason='unknown:why:learn', blocked_at='why:learn',
#            blocked_state=WhyState.UNKNOWN, path=['why:map', 'why:learn', 'why:root'])
```

A blocked component is not deleted, not unregistered, not "cleaned up".
It waits — questionable, revivable. The next section shows what that
looks like.

## Worked example (from experiments/minimal_world.py)

```python
rt.declare_why("the field is worth inhabiting", node_id="why:root")
rt.declare_why("the critter stays alive and learns the field",
               parent="why:root", node_id="why:critter")

rt.why.kill("why:root", reason="the mandate was withdrawn", tick=60)
# why.conservation() -> {'alive': 0, 'dead': 1, 'unknown': 2,
#                        'ever_declared': 3, 'invariant_ok': True}
#
# ten ticks pass: NOTHING runs. No error, no cleanup — silence.
# rt.why.verdict('why:critter') -> blocked, reason 'unknown:why:critter'

rt.why.resurrect("why:root", reason="a new mandate arrived with evidence",
                 tick=70)
# cascade: why:critter returns to ALIVE; the critter forages again.
```

The necrology after this sequence has five lines: the kill, two cascades
to UNKNOWN, the resurrection, one cascade back to ALIVE. History grew;
nothing shrank.

## Contradictions are allowed (and detectable)

A node can be ALIVE while an ancestor is DEAD — the tree does not force
consistency, it *records* dissonance:

```python
rt.why.kill("why:root", reason="...")
rt.why.revive("why:critter")            # local re-justification
rt.why.contradictions()                 # -> [why:critter]  (alive over dead)
```

This is deliberate. An organism that silently re-justifies itself is
lying to itself. Contradictions are surfaced, not suppressed; resolving
them (kill the child, or resurrect the parent with evidence) is a
deliberate act with a record.

## The audit

```python
rt.why.conservation()
# {'ever_declared': N, 'alive': a, 'dead': d, 'unknown': u, 'absent': b,
#  'invariant_ok': a + d + u + b == N}
```

The runtime asserts `invariant_ok` every 25 ticks and raises on
violation — a kernel bug, not a usage error. The test suite additionally
hammer-checks it: 500 random kill/revive/park/activate operations across
a 31-node tree must never lose a node (`tests/test_why.py`).

## FAQ

**Why never delete? Isn't that a memory leak?**
A WHY node is a few hundred bytes of statement and state. Ten thousand
purposes is a rounding error. The necrology is the cheapest part of any
real agent system — and the only part that cannot be reconstructed after
the fact. If scale ever demands it, the honest downgrade is archiving
DEAD-with-no-live-descendants nodes to cold storage *with their
necrology*, not deletion. (Open question: when is archival honest?)

**Why is UNKNOWN the cascade state and not DEAD?**
Because a child's purpose was *justified by* the parent, not *identical
to* it. The parent dying does not prove the child wrong; it removes the
child's warrant. Warrant-loss is a question (UNKNOWN), not a verdict
(DEAD). Questions are cheap to re-answer; verdicts need evidence.

**What about multi-parent WHY (a DAG)?**
Deliberately deferred. A tree gives every component exactly one chain to
audit. When shared purpose becomes necessary, the verdict semantics need
rethinking (any-alive-parent? majority? weighted?). See
OPEN_QUESTIONS.md.

**Who is allowed to kill?**
Anyone with a reference to the tree — by design. The law is not about
permission, it is about *consequences being permanent and visible*. If
you want policy on top (e.g. only the identity layer may kill roots),
write it as a component that owns the reference.

**How does this interact with LLM agents?**
Directly: an LLM's spawned scripts carry `why_node` references. If the
WHY chain behind an agent breaks, its scripts stop bidding — the model
keeps talking but the organism stops *acting*. Models propose; the WHY
tree disposes.
