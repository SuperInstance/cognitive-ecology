"""L7 — Identity: the slowly-drifting self-model.

An organism needs a self: the thing that stays coherent while the scripts
churn. Identity here is three stable artifacts:

* ROOT PURPOSES — the statements (not the states) of the WHY roots;
* COMMITMENTS — append-only, hash-chained decisions the organism stands
  behind (``commit()``); tampering breaks ``verify()``;
* STYLE — the behaviors most reinforced by actual use.

The caching connection is the whole point (see agents/stable_prefix.md):
``introspect()`` produces the STABLE PROMPT PREFIX. It is memoized and
changes ONLY when you call ``drift()`` — deliberately, between sessions.
Within a session, new commitments and style shifts accumulate but do not
rewrite the prefix; that discipline is what keeps provider prompt caches
hitting (cached input is ~20x cheaper than fresh input on current
DeepInfra pricing for tencent/Hy4-preview).

Identity drift is slow by design. A self that rewrites itself every tick
is not a self; it is a weather system.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Commitment:
    tick: int
    text: str
    prev_hash: str
    hash: str


class Identity:
    """Who the organism takes itself to be. Stable within a session."""

    def __init__(self, name: str = "organism", why=None) -> None:
        self.name = name
        self.why = why  # optional WhyTree: used for root statements only
        self._commitments: List[Commitment] = []
        self._style: List = []  # [(script_name, success_rate)]
        self._introspect_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # commitments: append-only, hash-chained
    # ------------------------------------------------------------------
    def commit(self, text: str, tick: int = 0) -> Commitment:
        """Stand behind a decision, permanently. Never edited, never deleted."""
        prev = self._commitments[-1].hash if self._commitments else "GENESIS"
        digest = hashlib.sha256(f"{prev}|{tick}|{text}".encode("utf-8")).hexdigest()[:16]
        c = Commitment(tick=tick, text=text, prev_hash=prev, hash=digest)
        self._commitments.append(c)
        # NOTE: this does NOT bust the introspect cache. New commitments
        # surface in the self-model only at the next deliberate drift().
        return c

    def commitments(self) -> tuple:
        return tuple(self._commitments)

    def verify(self) -> bool:
        """Re-derive the hash chain. False means somebody edited history."""
        prev = "GENESIS"
        for c in self._commitments:
            if c.prev_hash != prev:
                return False
            expected = hashlib.sha256(
                f"{prev}|{c.tick}|{c.text}".encode("utf-8")
            ).hexdigest()[:16]
            if c.hash != expected:
                return False
            prev = c.hash
        return True

    # ------------------------------------------------------------------
    # style: what the organism actually does, not what it says it does
    # ------------------------------------------------------------------
    def observe_style(self, scripts) -> None:
        """Call after runs: the top-3 most-fired live scripts become 'style'."""
        top = sorted(scripts, key=lambda s: (-s.fires, s.name))[:3]
        self._style = [(s.name, round(s.success_rate, 3)) for s in top if s.fires > 0]

    # ------------------------------------------------------------------
    # the stable prefix
    # ------------------------------------------------------------------
    def introspect(self) -> str:
        """The self-model as a deterministic string. Memoized — read it freely.

        This string is safe to use as the frozen prefix of an LLM prompt:
        within a session it returns byte-identical output on every call.
        """
        if self._introspect_cache is not None:
            return self._introspect_cache
        lines = [f"# {self.name} — self-model"]
        if self.why is not None:
            lines.append("## Root purposes")
            for r in sorted(self.why.roots(), key=lambda n: n.id):
                lines.append(f"- {r.statement}  [{r.id}]")
        if self._commitments:
            lines.append("## Commitments (latest 3, newest first)")
            for c in reversed(self._commitments[-3:]):
                lines.append(f"- [tick {c.tick}] {c.text}")
        if self._style:
            lines.append("## Style (most reinforced behaviors)")
            for name, rate in self._style:
                lines.append(f"- {name} (success {rate})")
        self._introspect_cache = "\n".join(lines)
        return self._introspect_cache

    def drift(self) -> str:
        """The ONLY way the self-model rewrites itself. Deliberate, rare,
        and every call is a prompt-cache bust you chose and can count."""
        self._introspect_cache = None
        return self.introspect()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "commitments": [
                {"tick": c.tick, "text": c.text,
                 "prev_hash": c.prev_hash, "hash": c.hash}
                for c in self._commitments
            ],
            "style": list(self._style),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Identity":
        ident = cls(name=data.get("name", "organism"))
        ident._commitments = [
            Commitment(tick=c["tick"], text=c["text"],
                       prev_hash=c["prev_hash"], hash=c["hash"])
            for c in data.get("commitments", [])
        ]
        ident._style = [tuple(x) for x in data.get("style", [])]
        return ident
