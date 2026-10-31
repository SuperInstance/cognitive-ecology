"""L6 — WHY: the conserved purpose layer. The crown of the stack.

Most agents die because their purpose is deletable — it lives in a prompt
someone edits, a backlog ticket someone closes, a context window that
evaporates. cognitive-ecology makes purpose a **conserved quantity**:

    THE WHY CONSERVATION LAW
    1. A WHY node is never deleted. Not ever. No API exists for it.
    2. Purpose has four states: ALIVE, DEAD, UNKNOWN, ABSENT.
    3. Killing a node cascades its living descendants to UNKNOWN —
       *questionable*, not gone. They can be revived.
    4. Every transition is recorded in an append-only necrology.

The result: an organism can lose its purpose, doubt its purpose, even
contradict its purpose — but it can never *erase* its purpose. History
stays auditable, revival stays possible, and "why did you do that?" always
has an answer.

The heartbeat question
----------------------
Every tick, every component must answer ``why_should_this_run()``. A
component whose WHY chain is broken (any ancestor DEAD or UNKNOWN) does not
run — but it is not deleted either. It waits, questionable, revivable.

Contradictions are allowed (and detectable): a node can be ALIVE while an
ancestor is DEAD. The organism holds beliefs it cannot fully justify —
``contradictions()`` finds them. This is a feature: cognitive dissonance is
information.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class WhyState(enum.Enum):
    ALIVE = "alive"        # asserting life; heartbeats accepted
    DEAD = "dead"          # explicitly killed; terminal without resurrection
    UNKNOWN = "unknown"    # questionable — an ancestor died; revivable
    ABSENT = "absent"      # declared but parked/draft; not asserting anything


@dataclass
class WhyNode:
    id: str
    parent: Optional[str]
    statement: str
    state: WhyState = WhyState.ABSENT
    born: int = 0
    last_beat: int = -1


@dataclass
class NecroRecord:
    """One line in the necrology: purpose changed hands, but never vanished."""

    tick: int
    node_id: str
    statement: str
    from_state: WhyState
    to_state: WhyState
    reason: str


@dataclass
class WhyVerdict:
    ok: bool
    reason: str
    path: list = field(default_factory=list)      # node ids, leaf -> root
    blocked_at: Optional[str] = None
    blocked_state: Optional[WhyState] = None


class WhyTree:
    """The conserved purpose graph. Append-only by construction."""

    def __init__(self) -> None:
        self._nodes: dict = {}
        self._children: dict = {}
        self._necrology: list = []
        self._ever_declared = 0
        self._next = 0

    # ------------------------------------------------------------------
    # structure
    # ------------------------------------------------------------------
    def declare(
        self,
        statement: str,
        parent: Optional[str] = None,
        state: WhyState = WhyState.ALIVE,
        tick: int = 0,
        node_id: Optional[str] = None,
    ) -> WhyNode:
        """Add a WHY node. Ids are auto-assigned (`why:1`, `why:2`, ...) unless given."""
        nid = node_id or f"why:{self._next + 1}"
        self._next += 1
        if nid in self._nodes:
            raise ValueError(f"duplicate WHY node id: {nid}")
        if parent is not None and parent not in self._nodes:
            raise KeyError(f"unknown parent WHY node: {parent}")
        node = WhyNode(
            id=nid, parent=parent, statement=statement, state=state,
            born=tick, last_beat=(tick if state is WhyState.ALIVE else -1),
        )
        self._nodes[nid] = node
        if parent is not None:
            self._children.setdefault(parent, []).append(nid)
        self._ever_declared += 1
        return node

    def node(self, nid: str) -> WhyNode:
        return self._nodes[nid]

    def has(self, nid: str) -> bool:
        return nid in self._nodes

    def nodes(self) -> list:
        return list(self._nodes.values())

    def children(self, nid: str) -> list:
        return [self._nodes[c] for c in self._children.get(nid, []) if c in self._nodes]

    def roots(self) -> list:
        return [n for n in self._nodes.values() if n.parent is None]

    def descendants(self, nid: str) -> list:
        """All node ids below `nid` (BFS)."""
        out: list = []
        queue = list(self._children.get(nid, []))
        seen = {nid}
        while queue:
            cur = queue.pop(0)
            if cur in seen:
                continue
            seen.add(cur)
            out.append(cur)
            queue.extend(self._children.get(cur, []))
        return out

    # ------------------------------------------------------------------
    # state transitions — every one recorded, nothing deleted
    # ------------------------------------------------------------------
    def _record(self, node: WhyNode, to_state: WhyState, reason: str, tick: int) -> None:
        self._necrology.append(
            NecroRecord(
                tick=tick, node_id=node.id, statement=node.statement,
                from_state=node.state, to_state=to_state, reason=reason,
            )
        )
        node.state = to_state

    def kill(self, nid: str, reason: str = "killed", tick: int = 0) -> WhyNode:
        """Mark DEAD. Living descendants cascade to UNKNOWN (questionable)."""
        node = self._nodes[nid]
        if node.state is WhyState.DEAD:
            return node
        self._record(node, WhyState.DEAD, reason, tick)
        for did in self.descendants(nid):
            dn = self._nodes[did]
            if dn.state is WhyState.ALIVE:
                self._record(
                    dn, WhyState.UNKNOWN, f"cascade: ancestor {nid} died ({reason})", tick
                )
        return node

    def revive(self, nid: str, reason: str = "rejustified", tick: int = 0) -> WhyNode:
        """UNKNOWN -> ALIVE. Questionable purposes may be re-justified."""
        node = self._nodes[nid]
        if node.state is not WhyState.UNKNOWN:
            raise ValueError(
                f"revive() only applies to UNKNOWN nodes (this one is {node.state.value})"
            )
        self._record(node, WhyState.ALIVE, reason, tick)
        node.last_beat = tick
        self._cascade_revive(nid, tick)
        return node

    def resurrect(self, nid: str, reason: str, tick: int = 0) -> WhyNode:
        """DEAD -> ALIVE. Requires substantive new evidence (a real reason)."""
        node = self._nodes[nid]
        if node.state is not WhyState.DEAD:
            raise ValueError("resurrect() only applies to DEAD nodes")
        if not reason or not reason.strip():
            raise ValueError(
                "resurrection requires a substantive reason (the new evidence)"
            )
        self._record(node, WhyState.ALIVE, f"resurrected: {reason}", tick)
        node.last_beat = tick
        self._cascade_revive(nid, tick)
        return node

    def _cascade_revive(self, nid: str, tick: int) -> None:
        """A revived ancestor re-resolves the questions it raised."""
        for did in self.descendants(nid):
            dn = self._nodes[did]
            if dn.state is WhyState.UNKNOWN:
                self._record(
                    dn, WhyState.ALIVE, f"cascade: ancestor {nid} revived", tick
                )
                dn.last_beat = tick

    def activate(self, nid: str, tick: int = 0) -> WhyNode:
        """ABSENT -> ALIVE: a draft/parked purpose starts asserting itself."""
        node = self._nodes[nid]
        if node.state is not WhyState.ABSENT:
            raise ValueError(
                f"activate() only applies to ABSENT nodes (this one is {node.state.value})"
            )
        self._record(node, WhyState.ALIVE, "activated", tick)
        node.last_beat = tick
        return node

    def park(self, nid: str, tick: int = 0) -> WhyNode:
        """-> ABSENT: park a purpose without killing it (recorded, reversible)."""
        node = self._nodes[nid]
        if node.state is WhyState.DEAD:
            raise ValueError("DEAD nodes cannot be parked; they stay DEAD (use resurrect)")
        self._record(node, WhyState.ABSENT, "parked", tick)
        return node

    def heartbeat(self, nid: str, tick: int = 0) -> bool:
        """Stamp liveness. Returns False if the node is not ALIVE."""
        node = self._nodes[nid]
        if node.state is WhyState.ALIVE:
            node.last_beat = tick
            return True
        return False

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def chain(self, nid: str) -> list:
        """The ancestry, leaf -> root."""
        out: list = []
        seen: set = set()
        cur: Optional[WhyNode] = self._nodes[nid]
        while cur is not None and cur.id not in seen:
            out.append(cur)
            seen.add(cur.id)
            cur = self._nodes[cur.parent] if cur.parent else None
        return out

    def justification(self, nid: str) -> float:
        """How justifiable is this node's chain, 0..1.

        A DEAD ancestor anywhere is a hard veto (0.0) — the purpose lineage
        is broken. Otherwise the score is the fraction of the chain that is
        ALIVE; UNKNOWN ancestors discount proportionally.
        """
        chain = self.chain(nid)
        if not chain:
            return 0.0
        if any(n.state is WhyState.DEAD for n in chain):
            return 0.0
        alive = sum(1 for n in chain if n.state is WhyState.ALIVE)
        return alive / len(chain)

    def verdict(self, nid: str) -> WhyVerdict:
        """Full answer to 'should this run?', with the blocking node named."""
        chain = self.chain(nid)
        path = [n.id for n in chain]
        for n in chain:  # leaf -> root: the most proximate blocker is reported
            if n.state is not WhyState.ALIVE:
                return WhyVerdict(
                    ok=False, reason=f"{n.state.value}:{n.id}",
                    path=path, blocked_at=n.id, blocked_state=n.state,
                )
        return WhyVerdict(ok=True, reason="ok", path=path)

    def why_should_this_run(self, nid: str) -> bool:
        """The heartbeat question. Asked of every component, every tick."""
        return self.verdict(nid).ok

    def contradictions(self) -> list:
        """ALIVE nodes with a DEAD ancestor — beliefs held without warrant."""
        out = []
        for n in self._nodes.values():
            if n.state is WhyState.ALIVE and any(
                a.state is WhyState.DEAD for a in self.chain(n.id)[1:]
            ):
                out.append(n)
        return out

    def necrology(self) -> tuple:
        """Every purpose transition, ever. Append-only."""
        return tuple(self._necrology)

    def conservation(self) -> dict:
        """The audit: states must always account for every node ever declared."""
        counts = {s: 0 for s in WhyState}
        for n in self._nodes.values():
            counts[n.state] += 1
        total = sum(counts.values())
        return {
            "ever_declared": self._ever_declared,
            "alive": counts[WhyState.ALIVE],
            "dead": counts[WhyState.DEAD],
            "unknown": counts[WhyState.UNKNOWN],
            "absent": counts[WhyState.ABSENT],
            "invariant_ok": total == self._ever_declared,
        }

    def digest(self) -> str:
        """Stable, prompt-friendly rendering.

        Shows STATEMENTS (the stable part) rather than states (which churn):
        a digest that flips between prompts would bust every provider's
        prefix cache. State churn belongs in the volatile suffix.
        """
        lines = ["why-tree:"]
        for n in sorted(self._nodes.values(), key=lambda x: x.id):
            depth = len(self.chain(n.id)) - 1
            lines.append(f"{'  ' * depth}- {n.statement}  [{n.id}]")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "nodes": [
                {
                    "id": n.id, "parent": n.parent, "statement": n.statement,
                    "state": n.state.value, "born": n.born, "last_beat": n.last_beat,
                }
                for n in self._nodes.values()
            ],
            "necrology": [
                {
                    "tick": r.tick, "node_id": r.node_id, "statement": r.statement,
                    "from": r.from_state.value, "to": r.to_state.value, "reason": r.reason,
                }
                for r in self._necrology
            ],
            "ever_declared": self._ever_declared,
            "next": self._next,
        }

    @classmethod
    def from_json(cls, data: dict) -> "WhyTree":
        tree = cls()
        for nd in data["nodes"]:
            node = WhyNode(
                id=nd["id"], parent=nd["parent"], statement=nd["statement"],
                state=WhyState(nd["state"]), born=nd["born"], last_beat=nd["last_beat"],
            )
            tree._nodes[node.id] = node
            if node.parent is not None:
                tree._children.setdefault(node.parent, []).append(node.id)
        for r in data["necrology"]:
            tree._necrology.append(
                NecroRecord(
                    tick=r["tick"], node_id=r["node_id"], statement=r["statement"],
                    from_state=WhyState(r["from"]), to_state=WhyState(r["to"]),
                    reason=r["reason"],
                )
            )
        tree._ever_declared = data["ever_declared"]
        tree._next = data["next"]
        return tree
