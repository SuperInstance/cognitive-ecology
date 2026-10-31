"""Homeostatic drives — where urgency comes from.

An organism without drives has no economy: nothing is ever urgent, so
attention defaults to whatever shouts loudest. Tensions are the slow
accumulation of unmet needs. They rise every tick by their growth rate and
discharge when a script relieves them.

    energy    grows 0.03/tick   -> forage relieves 0.6
    curiosity grows 0.02/tick   -> explore relieves 0.5

Because tension levels feed the ``urgency`` factor of every attention bid,
the whole market's temperature is set here. Design note: a tension with a
huge growth rate will dominate the organism — that is not a bug, it is
hunger. If your organism is obsessed, check its diet (growth rates) before
blaming the market.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tension:
    name: str
    level: float = 0.0
    growth: float = 0.02
    description: str = ""


class TensionField:
    """The organism's drives: grow every tick, discharge on satisfaction."""

    def __init__(self) -> None:
        self._t: dict = {}

    def add(self, name: str, growth: float = 0.02, level: float = 0.0,
            description: str = "") -> Tension:
        if name in self._t:
            raise ValueError(f"duplicate tension: {name}")
        t = Tension(name=name, level=level, growth=growth, description=description)
        self._t[name] = t
        return t

    def has(self, name: str) -> bool:
        return name in self._t

    def names(self) -> list:
        return sorted(self._t)

    def get(self, name: str) -> Optional[Tension]:
        return self._t.get(name)

    # -- dynamics ---------------------------------------------------------
    def tick(self) -> list:
        """Grow every tension. Returns [(name, old, new)] for meaningful changes."""
        changes = []
        for t in self._t.values():
            old = t.level
            t.level = min(1.0, t.level + t.growth)
            if t.level - old > 0.005:
                changes.append((t.name, old, t.level))
        return changes

    def relieve(self, name: str, amount: float = 0.5) -> float:
        """Satisfaction discharges the drive. Returns the new level."""
        t = self._t.get(name)
        if t is None:
            return 0.0
        t.level = max(0.0, t.level - amount)
        return t.level

    def burden(self, name: str, amount: float = 0.1) -> float:
        """Acting has costs: increase a drive (e.g. exploring costs energy)."""
        t = self._t.get(name)
        if t is None:
            return 0.0
        t.level = min(1.0, t.level + amount)
        return t.level

    # -- readings -----------------------------------------------------------
    def level(self, name: str) -> float:
        t = self._t.get(name)
        return t.level if t else 0.0

    def urgency(self, name: str) -> float:
        """The attention-market name for a tension level."""
        return self.level(name)

    def snapshot(self) -> dict:
        return {name: round(t.level, 4) for name, t in sorted(self._t.items())}

    # -- persistence ----------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "tensions": [
                {"name": t.name, "level": t.level, "growth": t.growth,
                 "description": t.description}
                for t in self._t.values()
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TensionField":
        f = cls()
        for td in data.get("tensions", []):
            f._t[td["name"]] = Tension(
                name=td["name"], level=td["level"], growth=td["growth"],
                description=td.get("description", ""),
            )
        return f
