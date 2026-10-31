"""Small shared helpers. No dependencies, no magic."""
from __future__ import annotations

import hashlib
import itertools
import json
from typing import Any

_counter = itertools.count(1)


def clamp01(x: Any) -> float:
    """Clamp anything number-like into [0, 1]. NaN and garbage become 0.0."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(0.0, min(1.0, v))


def ema(prev: float, x: float, alpha: float = 0.3) -> float:
    """Exponential moving average — how success rates learn, gently."""
    return (1.0 - alpha) * float(prev) + alpha * float(x)


def stable_hash(obj: Any) -> str:
    """Deterministic 12-hex hash of any JSON-able object.

    Used for: prompt-prefix cache-bust detection, commitment hash chains,
    reproducible node ids. Sorting keys means equal structures hash equally —
    the property the whole stable-prefix caching strategy depends on.
    """
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def short_id(prefix: str) -> str:
    """Short deterministic ids like 'why:7' or 'script:12'."""
    return f"{prefix}:{next(_counter)}"


def slug(text: str) -> str:
    """'Berry Bush #3!' -> 'berry-bush-3' — for graph-safe node ids."""
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "x"
