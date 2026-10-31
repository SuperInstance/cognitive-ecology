"""L4 — the Script Ecology. An agent is a population, not a monolith.

A conventional agent is one big prompt-oracle: everything it can do is
welded into a single context. A cognitive-ecology agent is a POPULATION of
small scripts. Each script is a trigger, an action, and a track record:

    Script(
        name="forage",
        relieves=("energy",),            # which tensions it discharges
        focus=("berry:1", "berry:2"),    # which graph nodes it watches
        when=lambda ctx: ...,            # opportunity: preconditions
        act=lambda ctx: Outcome(...),    # the deed itself
    )

Scripts compete in the attention market. Winners fire and their success
rate updates by EMA. Losers starve; starvation is counted; scripts that
never win and never fire eventually DIE — and death here, like everywhere
in this kernel, is a RECORD, not an erasure. The necrology keeps every
dead script with its stats. Nothing is learned and then lost.

Mutation (``mutate``) is how the ecology explores: a variant script with
jittered numeric parameters, spawned mostly during sleep (dreams). LLM
agents (agents/orchestrator.py) extend this the safe way: they propose NEW
scripts parameterized from a fixed action library — never arbitrary code.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from .attention import AttentionBid
from .events import EventBus, EventKind
from .util import ema


@dataclass
class Outcome:
    """What running a script produced. Small on purpose."""

    ok: bool
    note: str = ""


@dataclass
class Script:
    """One behavior: trigger + action + track record."""

    id: str = ""
    name: str = ""
    why_node: str = ""                  # the WHY node that justifies this script
    owner: str = "critter"              # component that fires it
    relieves: tuple = ()                # tension names it discharges
    focus: tuple = ()                   # graph node ids it watches (novelty)
    when: Optional[Callable] = None     # (ctx) -> bool  : opportunity
    act: Optional[Callable] = None      # (ctx) -> Outcome : the deed
    resource: Optional[str] = None      # exclusive resource for the executive
    params: dict = field(default_factory=dict)  # numeric knobs (mutable by dreams)
    # track record
    success_rate: float = 0.5
    fires: int = 0
    born: int = 0
    last_fire: int = -1
    parent: Optional[str] = None
    generation: int = 0
    starve: int = 0

    def fire(self, ctx) -> Outcome:
        """Run the action, learn from the result.

        This is the organism's learning loop in miniature: act, observe
        success or failure, and let the success rate drift toward reality
        (EMA, alpha=0.3). A failing script is not punished by decree — it
        simply stops winning the attention market as its expected_value
        falls, starves, and eventually dies with its record intact.
        """
        try:
            out = self.act(ctx) if self.act is not None else Outcome(False, "no action bound")
        except Exception as exc:  # a crashing script must not kill the organism
            out = Outcome(False, f"error: {exc.__class__.__name__}: {exc}")
        self.success_rate = ema(self.success_rate, 1.0 if out.ok else 0.0)
        self.fires += 1
        self.last_fire = ctx.tick
        self.starve = 0
        return out


@dataclass
class ScriptDeath:
    """Necrology entry: a script died. Its record survives forever."""

    tick: int
    name: str
    why_node: str
    owner: str
    reason: str
    fires: int
    success_rate: float
    born: int
    parent: Optional[str]
    generation: int


def _safe_when(fn: Callable, ctx) -> bool:
    """A crashing trigger means 'not now', not 'kill the organism'."""
    try:
        return bool(fn(ctx))
    except Exception:
        return False


class ScriptEcology:
    """The population: spawn, compete, starve, die, mutate, remember."""

    def __init__(self, bus: Optional[EventBus] = None, rng: Optional[random.Random] = None,
                 starve_limit: int = 40, idle_window: int = 30) -> None:
        self._scripts: dict = {}      # id -> Script (live population only)
        self._by_name: dict = {}      # name -> Script (live)
        self._necrology: list = []    # ScriptDeath records, append-only
        self._saved: dict = {}        # name -> stats, for rehydration after load()
        self._next = 0
        self.bus = bus
        self.rng = rng or random.Random(7)
        self.starve_limit = starve_limit
        self.idle_window = idle_window

    # ------------------------------------------------------------------
    # population
    # ------------------------------------------------------------------
    def _register(self, script: Script, tick: int,
                  _restamp_born: bool = True) -> Script:
        if not script.name:
            raise ValueError("script needs a name")
        if script.name in self._by_name:
            raise ValueError(f"duplicate live script name: {script.name}")
        if not script.id:
            self._next += 1
            script.id = f"script:{self._next}"
        if _restamp_born and script.born <= 0:
            # Only for scripts with no history: an ADOPTED script keeps the
            # born its saved record carried — including born=0 (round 20a:
            # a tick-0-born script used to come back re-stamped at the load
            # tick, resetting its starvation grace window; found by the
            # game-dev persona as a save-compat bug).
            script.born = tick
        self._scripts[script.id] = script
        self._by_name[script.name] = script
        if self.bus is not None:
            self.bus.emit(
                EventKind.BIRTH,
                (script.name, script.why_node, f"owner={script.owner} gen={script.generation}"),
                src="ecology", ts=tick,
            )
        return script

    def spawn(self, script: Script, tick: int = 0) -> Script:
        """A new script enters the population. BIRTH is announced."""
        return self._register(script, tick)

    def adopt(self, script: Script, tick: int = 0) -> Script:
        """Rehydrate a code-defined script with its saved track record.

        Code defines behavior (closures cannot be serialized); state files
        define history. After Runtime.load(), rebuild your scripts in code
        and adopt() them to get their stats back.
        """
        saved = self._saved.pop(script.name, None)
        if saved:
            for key in ("success_rate", "fires", "born", "last_fire",
                        "parent", "generation", "starve"):
                if key in saved:
                    setattr(script, key, saved[key])
            # a rehydrated script keeps its saved biography — do not
            # restamp born at the load tick (see _register)
            return self._register(script, tick, _restamp_born=False)
        return self._register(script, tick)

    def get(self, name: str) -> Optional[Script]:
        return self._by_name.get(name)

    def alive(self, owner: Optional[str] = None) -> list:
        out = [s for s in self._scripts.values()
               if owner is None or s.owner == owner]
        return sorted(out, key=lambda s: s.name)

    def population(self) -> int:
        return len(self._scripts)

    # ------------------------------------------------------------------
    # the market interface
    # ------------------------------------------------------------------
    def bids(self, ctx, owner: Optional[str] = None) -> list:
        """Build one AttentionBid per eligible script.

        The WHY law gates entry: a script whose WHY chain is broken
        (justification 0) never even enters the market. Dead purpose
        means dead behavior — no matter how urgent it claims to be.
        """
        out = []
        for s in self._scripts.values():
            if owner is not None and s.owner != owner:
                continue
            justification = ctx.why.justification(s.why_node)
            if justification <= 0.0:
                continue
            opportunity = 1.0 if (s.when is None or _safe_when(s.when, ctx)) else 0.0
            if opportunity <= 0.0:
                continue
            urgency = max([ctx.tensions.level(r) for r in s.relieves] or [0.0])
            novelty = ctx.novelty(s.focus)
            out.append(AttentionBid(
                src=s.owner, label=s.name,
                urgency=urgency, justification=justification,
                opportunity=opportunity, novelty=novelty,
                expected_value=s.success_rate, resource=s.resource,
            ))
        return out

    def fire(self, name: str, ctx) -> Outcome:
        """Fire a script by name (used by owner components in act())."""
        s = self._by_name.get(name)
        if s is None:
            return Outcome(False, f"no live script named {name!r}")
        return s.fire(ctx)

    def bookkeeping(self, tick: int, fired_labels, starved_labels) -> list:
        """Update starvation after a market clearing. Returns new deaths."""
        fired = set(fired_labels)
        starved = set(starved_labels)
        for s in self._scripts.values():
            if s.name in fired:
                s.starve = 0
            elif s.name in starved:
                s.starve += 1
        deaths = []
        for s in list(self._scripts.values()):
            if (s.starve > self.starve_limit and s.fires == 0
                    and (tick - s.born) >= self.idle_window):
                deaths.append(self._die(s, tick, "starved: never won attention"))
        return deaths

    def prune_starved(self, tick: int, min_age: int = 30) -> list:
        """Sleep pruning is harsher: long-starving scripts die regardless
        of whether they ever fired. Death is still just a record."""
        deaths = []
        for s in list(self._scripts.values()):
            if s.starve >= self.starve_limit and (tick - s.born) >= min_age:
                deaths.append(self._die(s, tick, "pruned during sleep: starving"))
        return deaths

    def _die(self, script: Script, tick: int, reason: str) -> ScriptDeath:
        self._scripts.pop(script.id, None)
        self._by_name.pop(script.name, None)
        death = ScriptDeath(
            tick=tick, name=script.name, why_node=script.why_node,
            owner=script.owner, reason=reason, fires=script.fires,
            success_rate=round(script.success_rate, 4), born=script.born,
            parent=script.parent, generation=script.generation,
        )
        self._necrology.append(death)
        if self.bus is not None:
            self.bus.emit(
                EventKind.DEATH,
                (script.name, script.why_node, reason),
                src="ecology", ts=tick,
            )
        return death

    def mutate(self, script: Script, tick: int) -> Script:
        """Dream a variant: same behavior, jittered numeric parameters.

        Mutation explores the parameter space; LLM-proposed scripts explore
        the behavior space. Both pass through the same market afterwards.
        """
        child_params = {}
        for k, v in script.params.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                child_params[k] = v
            else:
                jitter = 1.0 + self.rng.uniform(-0.2, 0.2)
                if isinstance(v, int):
                    child_params[k] = max(1, int(round(v * jitter)))
                else:
                    child_params[k] = round(v * jitter, 4)
        gen = script.generation + 1
        base = script.name.split("~")[0]
        candidate = f"{base}~{gen}"
        while candidate in self._by_name:  # dream twice, name once
            gen += 1
            candidate = f"{base}~{gen}"
        child = Script(
            name=candidate,
            why_node=script.why_node,
            owner=script.owner,
            relieves=script.relieves,
            focus=script.focus,
            when=script.when,
            act=script.act,
            resource=script.resource,
            params=child_params,
            success_rate=0.5,          # newborns get the benefit of the doubt
            born=tick,
            parent=script.id,
            generation=gen,
        )
        return self.spawn(child, tick=tick)

    # ------------------------------------------------------------------
    # memory of the dead
    # ------------------------------------------------------------------
    def necrology(self) -> tuple:
        return tuple(self._necrology)

    def stats(self) -> list:
        return [
            {"name": s.name, "owner": s.owner, "fires": s.fires,
             "success_rate": round(s.success_rate, 4), "starve": s.starve,
             "generation": s.generation, "params": s.params}
            for s in self.alive()
        ]

    # ------------------------------------------------------------------
    # persistence (stats only — behavior lives in code)
    # ------------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "saved": {
                s.name: {
                    "id": s.id, "success_rate": s.success_rate, "fires": s.fires,
                    "born": s.born, "last_fire": s.last_fire, "parent": s.parent,
                    "generation": s.generation, "starve": s.starve,
                    "why_node": s.why_node, "owner": s.owner,
                    "relieves": list(s.relieves), "focus": list(s.focus),
                    "resource": s.resource, "params": s.params,
                }
                for s in self._scripts.values()
            },
            "necrology": [
                {"tick": d.tick, "name": d.name, "why_node": d.why_node,
                 "owner": d.owner, "reason": d.reason, "fires": d.fires,
                 "success_rate": d.success_rate, "born": d.born,
                 "parent": d.parent, "generation": d.generation}
                for d in self._necrology
            ],
            "next": self._next,
        }

    @classmethod
    def from_json(cls, data: dict, bus: Optional[EventBus] = None,
                  rng: Optional[random.Random] = None) -> "ScriptEcology":
        eco = cls(bus=bus, rng=rng)
        eco._saved = dict(data.get("saved", {}))
        eco._necrology = [
            ScriptDeath(
                tick=d["tick"], name=d["name"], why_node=d["why_node"],
                owner=d.get("owner", "?"), reason=d["reason"], fires=d["fires"],
                success_rate=d["success_rate"], born=d["born"],
                parent=d.get("parent"), generation=d.get("generation", 0),
            )
            for d in data.get("necrology", [])
        ]
        eco._next = data.get("next", 0)
        return eco
