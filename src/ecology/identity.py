"""Identity — a stable attractor, not a profile.

Identity is not memory and not a chat history. It is *persistent
preference*: what repeatedly wins. Values get reinforced when acting on them
pays off and decay when they do not; the distribution stays normalized, so
identity is the shape of the distribution, and its stability is measurable
(concentration). Rewriting a routine does not touch identity; identity is
what decides which rewrites survive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Identity:
    values: dict[str, float] = field(
        default_factory=lambda: {"truth": 1 / 3, "usefulness": 1 / 3, "exploration": 1 / 3}
    )
    goals: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)

    # ---- learning: what repeatedly wins ----

    def reinforce(self, value: str, amount: float = 1.0, rate: float = 0.2) -> None:
        """Reward a value; renormalize so identity stays a distribution.

        The EMA pull keeps identity an attractor: single events barely move
        it, but consistent outcomes settle it.
        """
        if value not in self.values or rate <= 0:
            return
        self.values[value] *= 1.0 + rate * amount
        total = sum(self.values.values())
        if total > 0:
            for key in self.values:
                self.values[key] /= total

    # ---- queries ----

    def top_values(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self.values.items(), key=lambda kv: -kv[1])[:n]

    def stability(self) -> float:
        """Concentration of the value distribution in [0, 1].

        0 = perfectly undecided (uniform), 1 = fully decided (one value
        takes everything). A healthy identity is a *stable* attractor: it
        should move slowly and only under sustained pressure.
        """
        total = sum(self.values.values())
        if total <= 0 or not self.values:
            return 0.0
        entropy = -sum((p / total) * math.log(p / total) for p in self.values.values() if p > 0)
        uniform = math.log(len(self.values))
        if uniform <= 0:
            return 1.0
        return 1.0 - entropy / uniform

    def snapshot(self) -> dict:
        return {
            "values": dict(self.values),
            "top": self.top_values(3),
            "stability": round(self.stability(), 4),
            "goals": list(self.goals),
            "themes": list(self.themes),
        }
