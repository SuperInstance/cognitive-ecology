"""L8 — Sleep: what the organism does when nothing is worth doing.

An organism that only reacts never consolidates. When the attention market
clears nothing for several consecutive ticks — no urgency, no opportunity,
nothing novel — the runtime hands the body to the sleep cycle:

* REPLAY: recent events re-consolidate into the world graph with a boost
  (episodes become structure — the hippocampal move);
* PRUNE: scripts that have been starving for a long time die, with their
  records preserved in the necrology (sleep pruning is harsher than the
  waking rule: it does not require "never fired");
* DREAM: the ecology mutates a couple of live scripts — jittered parameter
  variants that will compete in tomorrow's market. Dreams are cheap
  experiments with no side effects on the world.

Sleep is entered from idleness, not from a clock. An organism mid-crisis
does not sleep; an organism with nothing to say does.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .events import EventBus, EventKind


@dataclass
class SleepStats:
    """Cumulative sleep accounting."""

    cycles: int = 0
    replayed: int = 0    # graph mutations from replay
    pruned: int = 0      # scripts that died in sleep
    dreams: int = 0      # mutant scripts spawned


class SleepCycle:
    """Replay, prune, dream — in that order, on idle."""

    def __init__(self, ecology, memory, bus: Optional[EventBus] = None,
                 rng: Optional[random.Random] = None, idle_window: int = 5) -> None:
        self.ecology = ecology
        self.memory = memory
        self.bus = bus
        self.rng = rng or random.Random(11)
        self.idle_window = idle_window
        self.stats = SleepStats()

    def should_sleep(self, idle_streak: int) -> bool:
        """Sleep when the market has cleared nothing for `idle_window` ticks."""
        return idle_streak >= self.idle_window

    def cycle(self, tick: int, events=None) -> SleepStats:
        """One sleep cycle: replay -> prune -> dream. Returns cumulative stats."""
        replayed = self.memory.replay(events or [], tick) if events else 0
        pruned = len(self.ecology.prune_starved(tick))
        dreams: list = []
        alive = self.ecology.alive()
        if alive:
            for s in self.rng.sample(alive, min(2, len(alive))):
                dreams.append(self.ecology.mutate(s, tick).name)

        self.stats.cycles += 1
        self.stats.replayed += replayed
        self.stats.pruned += pruned
        self.stats.dreams += len(dreams)

        if self.bus is not None:
            self.bus.emit(
                EventKind.NOTE_OFF,
                ("sleep", f"replayed={replayed} pruned={pruned} dreams={dreams}"),
                src="sleep", ts=tick,
            )
        return self.stats
