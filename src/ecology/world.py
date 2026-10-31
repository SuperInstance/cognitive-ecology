"""L2 — the World State Graph.

Not RAG. Not documents. Typed, addressable objects — think MUD objects:
Project, Goal, Routine, Agent, Observation, Belief, Memory… The graph is the
world; everything else (including the WHY layer) interprets it.

Persistence is SQLite (stdlib): boring, everywhere, transactional, and it
keeps the world a file you can back up. In-memory mirrors make ticks cheap;
writes flush on ``persist()``. The WHY kernel is deliberately *not* stored
here — justification lives in its own two-file format so the Rust CLI and
this runtime read the same truth.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    attrs_json TEXT NOT NULL DEFAULT '{}',
    created_tick INTEGER NOT NULL DEFAULT 0,
    updated_tick INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,
    attrs_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (src, dst, rel)
);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
"""


@dataclass
class WorldNode:
    id: str
    type: str
    attrs: dict[str, Any] = field(default_factory=dict)
    created_tick: int = 0
    updated_tick: int = 0


class WorldGraph:
    """Typed object store with edges — the world's state."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else None
        self._conn: sqlite3.Connection | None = None
        self.nodes: dict[str, WorldNode] = {}
        self.edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._path)
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
            self._load()

    # ---- nodes ----

    def add_node(
        self,
        node_id: str,
        node_type: str,
        attrs: dict | None = None,
        tick: int = 0,
    ) -> WorldNode:
        node = WorldNode(node_id, node_type, dict(attrs or {}), tick, tick)
        self.nodes[node_id] = node
        return node

    def node(self, node_id: str) -> WorldNode | None:
        return self.nodes.get(node_id)

    def nodes_of_type(self, node_type: str) -> list[WorldNode]:
        return [n for n in self.nodes.values() if n.type == node_type]

    def touch(self, node_id: str, tick: int, **attr_updates: Any) -> None:
        node = self.nodes.get(node_id)
        if node is None:
            return
        node.attrs.update(attr_updates)
        node.updated_tick = tick

    # ---- edges ----

    def add_edge(self, src: str, dst: str, rel: str, attrs: dict | None = None) -> None:
        self.edges[(src, dst, rel)] = dict(attrs or {})

    def neighbors(self, node_id: str, rel: str | None = None) -> list[str]:
        return [
            dst for (s, dst, r) in self.edges if s == node_id and (rel is None or r == rel)
        ]

    def predecessors(self, node_id: str, rel: str | None = None) -> list[str]:
        return [
            src for (src, d, r) in self.edges if d == node_id and (rel is None or r == rel)
        ]

    # ---- memory graduation (L6' — a memory is not stored, it graduates) ----

    MATURITY_LEVELS = ("observation", "episode", "pattern", "routine", "policy")

    def graduate(self, node_id: str, target: str) -> bool:
        """Promote a memory node along the maturity ladder; never backward."""
        node = self.nodes.get(node_id)
        if node is None or target not in self.MATURITY_LEVELS:
            return False
        current = node.attrs.get("maturity", "observation")
        if self.MATURITY_LEVELS.index(target) > self.MATURITY_LEVELS.index(current):
            node.attrs["maturity"] = target
            return True
        return False

    # ---- persistence ----

    def persist(self) -> None:
        if self._conn is None:
            return
        cur = self._conn.cursor()
        for node in self.nodes.values():
            cur.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?)",
                (
                    node.id,
                    node.type,
                    json.dumps(node.attrs, default=str),
                    node.created_tick,
                    node.updated_tick,
                ),
            )
        for (src, dst, rel), attrs in self.edges.items():
            cur.execute(
                "INSERT OR REPLACE INTO edges VALUES (?, ?, ?, ?)",
                (src, dst, rel, json.dumps(attrs, default=str)),
            )
        self._conn.commit()

    def _load(self) -> None:
        assert self._conn is not None
        for node_id, node_type, attrs_json, created, updated in self._conn.execute(
            "SELECT id, type, attrs_json, created_tick, updated_tick FROM nodes"
        ):
            self.nodes[node_id] = WorldNode(
                node_id, node_type, json.loads(attrs_json), created, updated
            )
        for src, dst, rel, attrs_json in self._conn.execute(
            "SELECT src, dst, rel, attrs_json FROM edges"
        ):
            self.edges[(src, dst, rel)] = json.loads(attrs_json)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()

    # ---- views ----

    def census(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes.values():
            counts[node.type] = counts.get(node.type, 0) + 1
        return counts
