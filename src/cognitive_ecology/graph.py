"""L2 — the World Graph. Anti-RAG knowledge with a biography.

RAG treats memory as a filing cabinet: chunk, embed, retrieve the top-k
similar fragments, stuff them in a context window, forget them again. The
agent never *lives* in its knowledge — it visits, briefly, with amnesia
between visits.

The World Graph inverts this:

* Knowledge is a typed property graph the organism INHABITS. Nodes are
  entities (``berry:3``, ``tension:energy``, ``topic:cache-economics``);
  edges are relations with weights.
* Every node has a BIOGRAPHY: ``born`` (first seen), ``last_seen``,
  ``weight`` (importance, reinforced by use). Knowledge is not a document;
  it is a history.
* Recall is TRAVERSAL, not similarity search. ``walk()`` expands from cue
  nodes, best-first, scored by weight x recency, under a budget. There is
  no embedding index anywhere in this kernel.
* The graph is append/decay-only. ``decay()`` weakens unseen nodes toward a
  floor but NEVER deletes them — the graph has the same conservation
  property as the WHY tree. Forgetting is fading, not erasure.

Anti-RAG, precisely: relevance comes from co-occurrence, repetition,
recency, and the current attentional context — not from vector similarity.
"""
from __future__ import annotations

import heapq
import json
from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass
class GNode:
    id: str
    kind: str
    props: dict
    born: int
    last_seen: int
    weight: float = 1.0


@dataclass
class GEdge:
    src: str
    dst: str
    rel: str
    props: dict
    born: int
    weight: float = 0.4


@dataclass
class WalkResult:
    """What a walk brought back: node ids in visit order + the edges used."""

    ids: list = field(default_factory=list)
    edges: list = field(default_factory=list)


class WorldGraph:
    """A typed graph the organism lives in. Append/decay-only, never delete."""

    def __init__(self) -> None:
        self._nodes: dict = {}
        self._edges: dict = {}
        self._index: dict = {}
        self._now = 0

    # ------------------------------------------------------------------
    # mutation (append / reinforce only)
    # ------------------------------------------------------------------
    def upsert(self, node_id: str, kind: str, props: Optional[dict] = None, tick: int = 0) -> GNode:
        """Create a node, or refresh + merge props if it exists."""
        self._now = max(self._now, tick)
        existing = self._nodes.get(node_id)
        if existing is not None:
            if props:
                existing.props.update(props)
            existing.last_seen = tick
            existing.weight = min(2.0, existing.weight + 0.05)
            return existing
        node = GNode(id=node_id, kind=kind, props=dict(props or {}), born=tick, last_seen=tick)
        self._nodes[node_id] = node
        return node

    def link(
        self, src: str, dst: str, rel: str,
        props: Optional[dict] = None, tick: int = 0, strengthen: float = 0.1,
    ) -> GEdge:
        """Create or reinforce a directed edge. Hebbian by default."""
        self._now = max(self._now, tick)
        key = (src, dst, rel)
        existing = self._edges.get(key)
        if existing is not None:
            existing.weight = min(2.0, existing.weight + strengthen)
            return existing
        edge = GEdge(src=src, dst=dst, rel=rel, props=dict(props or {}), born=tick)
        self._edges[key] = edge
        self._index.setdefault(src, []).append(key)
        self._index.setdefault(dst, []).append(key)
        return edge

    def seen(self, node_ids: Iterable[str], tick: int = 0) -> int:
        """Mark nodes as seen this tick (bumps recency + weight)."""
        n = 0
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node is not None:
                node.last_seen = tick
                node.weight = min(2.0, node.weight + 0.05)
                n += 1
        self._now = max(self._now, tick)
        return n

    def forget(self, node_id: str) -> None:
        """Deliberate erasure DOES NOT EXIST. This method is a tombstone.

        Calling it raises. Keeping the raiser makes the design decision
        executable documentation: forgetting here means decay-to-floor,
        never deletion.
        """
        raise NotImplementedError(
            "The World Graph is append/decay-only: nodes are never deleted. "
            "Use decay() — forgetting is fading, not erasure."
        )

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def get(self, node_id: str) -> Optional[GNode]:
        return self._nodes.get(node_id)

    def has(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def edges_of(self, node_id: str) -> list:
        return [self._edges[k] for k in self._index.get(node_id, []) if k in self._edges]

    def neighbors(self, node_id: str) -> list:
        out = []
        for e in self.edges_of(node_id):
            other = e.dst if e.src == node_id else e.src
            n = self._nodes.get(other)
            if n is not None:
                out.append((e, n))
        return out

    def _score(self, node: GNode) -> float:
        """Attention-shaped relevance: importance x recency."""
        age = max(0, self._now - node.last_seen)
        return node.weight * (1.0 / (1.0 + age))

    def walk(self, starts: Iterable[str], budget: int = 16) -> WalkResult:
        """ANTI-RAG RECALL: best-first traversal from cue nodes, under budget.

        This replaces `vector_search(query, k)`. You give it where you are
        (cue nodes); it gives you the neighborhood worth attending to.
        """
        heap: list = []
        visited: set = set()
        order: list = []
        edges_used: list = []
        for s in starts:
            node = self._nodes.get(s)
            if node is not None and s not in visited:
                heapq.heappush(heap, (-self._score(node), s))
        while heap and len(visited) < max(1, budget):
            _, nid = heapq.heappop(heap)
            if nid in visited:
                continue
            visited.add(nid)
            order.append(nid)
            for edge in self.edges_of(nid):
                other = edge.dst if edge.src == nid else edge.src
                if other not in visited:
                    onode = self._nodes.get(other)
                    if onode is not None:
                        heapq.heappush(heap, (-self._score(onode), other))
                if edge not in edges_used:
                    edges_used.append(edge)
        return WalkResult(ids=order, edges=edges_used)

    def decay(self, tick: int, horizon: int = 200, rate: float = 0.98, floor: float = 0.05) -> int:
        """Weaken nodes unseen for `horizon` ticks. Never delete. Returns count decayed."""
        self._now = max(self._now, tick)
        n = 0
        for node in self._nodes.values():
            if node.last_seen < tick - horizon and node.weight > floor:
                node.weight = max(floor, node.weight * rate)
                n += 1
        return n

    def churn_since(self, tick: int) -> float:
        """Fraction of nodes seen since `tick` — the novelty signal."""
        if not self._nodes:
            return 0.0
        fresh = sum(1 for n in self._nodes.values() if n.last_seen >= tick)
        return fresh / len(self._nodes)

    def digest(self, max_nodes: int = 32) -> str:
        """Deterministic, prompt-friendly summary of the salient world.

        Sorted by (-weight, id): same world -> same string, ALWAYS. This
        stability is what makes the world digest safely cacheable when it
        appears in prompts (see agents/stable_prefix.md).
        """
        ranked = sorted(self._nodes.values(), key=lambda n: (-n.weight, n.id))[:max_nodes]
        lines = [f"world-graph: {self.node_count()} nodes, {self.edge_count()} edges"]
        for n in ranked:
            props = json.dumps(n.props, sort_keys=True, separators=(",", ":"))
            line = f"{n.id} ({n.kind}) w={n.weight:.2f} last_seen={n.last_seen}"
            if n.props:
                line += f" {props}"
            lines.append(line)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "now": self._now,
            "nodes": [
                {"id": n.id, "kind": n.kind, "props": n.props, "born": n.born,
                 "last_seen": n.last_seen, "weight": round(n.weight, 6)}
                for n in self._nodes.values()
            ],
            "edges": [
                {"src": e.src, "dst": e.dst, "rel": e.rel, "props": e.props,
                 "born": e.born, "weight": round(e.weight, 6)}
                for e in self._edges.values()
            ],
        }

    @classmethod
    def from_json(cls, data: dict) -> "WorldGraph":
        g = cls()
        g._now = data.get("now", 0)
        for nd in data["nodes"]:
            g._nodes[nd["id"]] = GNode(
                id=nd["id"], kind=nd["kind"], props=nd["props"],
                born=nd["born"], last_seen=nd["last_seen"], weight=nd["weight"],
            )
        for ed in data["edges"]:
            key = (ed["src"], ed["dst"], ed["rel"])
            g._edges[key] = GEdge(
                src=ed["src"], dst=ed["dst"], rel=ed["rel"], props=ed["props"],
                born=ed["born"], weight=ed["weight"],
            )
            g._index.setdefault(ed["src"], []).append(key)
            g._index.setdefault(ed["dst"], []).append(key)
        return g
