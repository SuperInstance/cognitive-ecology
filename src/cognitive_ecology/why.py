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

The re-attestation economics (v0.3)
-----------------------------------
``never deleted'' cannot mean ``never questioned''. If liveness attested
once stays valid forever, purpose is a purchase, not a subscription — the
organism never has to *maintain* what it believes. So an optional
``attestation_horizon`` makes liveness a subscription:

* running under a purpose stamps heartbeats along its whole chain
  (*use it*), transitive to the root;
* a chain's ``justification()`` is discounted by its stalest ALIVE link
  (weakest-link freshness) — stale purposes lose attention contention
  before they are ever formally questioned;
* an ALIVE node unattested for longer than the horizon *lapses* to
  UNKNOWN (questionable — never deleted), recorded in the necrology;
* a lapsed purpose returns only by explicit ``revive(reason)`` — a
  conscious re-justification that buys a fresh horizon. The lapse itself
  stays in the necrology forever.

With ``attestation_horizon=None`` (the default) none of this activates:
the v0.2 semantics — attest once, alive until explicitly killed — hold.

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
    last_attested_by: str = ""       # component whose winning act last stamped it
    probation: bool = False           # revived but not yet re-served ( parole )


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
    """The conserved purpose graph. Append-only by construction.

    ``attestation_horizon`` (optional, >= 1) activates the re-attestation
    economics: freshness discounts, lapse-to-UNKNOWN, revive ceremony.
    ``None`` keeps the v0.2 semantics (attest once, alive until killed).
    """

    def __init__(self, attestation_horizon: Optional[int] = None) -> None:
        if attestation_horizon is not None and attestation_horizon < 1:
            raise ValueError("attestation_horizon must be >= 1 (or None to disable)")
        self.attestation_horizon = attestation_horizon
        self.now: int = 0  # the tree's notion of 'now'; the runtime advances it
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
        """UNKNOWN -> ALIVE. Questionable purposes may be re-justified.

        Revival is PAROLE, not pardon: the node lands on probation — its
        justification is capped until a genuine winning act re-attests it
        (round 004's UNKNOWN-washing fix: mass kill-and-revive must never
        be cheaper than honest service).
        """
        node = self._nodes[nid]
        if node.state is not WhyState.UNKNOWN:
            raise ValueError(
                f"revive() only applies to UNKNOWN nodes (this one is {node.state.value})"
            )
        self._record(node, WhyState.ALIVE, reason, tick)
        node.last_beat = tick
        node.probation = True
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
        node.probation = True  # evidence earns a hearing, not full strength
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
                dn.probation = True  # cascaded revivals are on parole too

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

    def heartbeat(self, nid: str, tick: int = 0, by: str = "") -> bool:
        """Stamp liveness. Returns False if the node is not ALIVE."""
        node = self._nodes[nid]
        if node.state is WhyState.ALIVE:
            node.last_beat = tick
            if by:
                node.last_attested_by = by
            node.probation = False  # genuine service ends parole
            return True
        return False

    def stamp_chain(self, nid: str, tick: int, by: str = "") -> int:
        """Re-attest a purpose by USE: stamp every ALIVE node leaf -> root.

        Serving a purpose maintains its whole lineage — a running child
        keeps its root fresh — and ends any probation along the way.
        Returns how many nodes took the stamp.
        """
        took = 0
        for n in self.chain(nid):
            if self.heartbeat(n.id, tick, by=by):
                took += 1
        return took

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

    def freshness(self, nid: str, tick: Optional[int] = None) -> float:
        """Weakest-link freshness of the chain's ALIVE nodes, 0..1.

        Full freshness through the first third of the horizon (the grace
        window — a new purpose gets time to establish), then linear decay
        to zero at the horizon. With no horizon configured, always 1.0.
        """
        if self.attestation_horizon is None:
            return 1.0
        t = self.now if tick is None else tick
        h = self.attestation_horizon
        grace = h // 3
        worst = 1.0
        for n in self.chain(nid):
            if n.state is not WhyState.ALIVE:
                continue  # non-alive links are priced by justification()
            last = n.last_beat if n.last_beat >= 0 else n.born
            age = max(0, t - last)
            if age <= grace:
                f = 1.0
            elif age >= h:
                f = 0.0
            else:
                f = 1.0 - (age - grace) / (h - grace)
            if f < worst:
                worst = f
        return worst

    PROBATION_CAP = 0.5  # a revived-but-unserved purpose bids at half strength

    def justification(self, nid: str, tick: Optional[int] = None) -> float:
        """How justifiable is this node's chain, 0..1.

        A DEAD ancestor anywhere is a hard veto (0.0) — the purpose lineage
        is broken. Otherwise the score is the fraction of the chain that is
        ALIVE (UNKNOWN ancestors discount proportionally), multiplied by
        the chain's weakest-link FRESHNESS when re-attestation economics
        are on, and capped at PROBATION_CAP while any chain node is on
        parole (revived without service since). Liveness attested long ago
        is worth less than liveness maintained; liveness *asserted* without
        service is worth half.
        """
        if tick is not None:
            self.now = tick  # explicit tick advances the tree's clock
        chain = self.chain(nid)
        if not chain:
            return 0.0
        if any(n.state is WhyState.DEAD for n in chain):
            return 0.0
        alive = sum(1 for n in chain if n.state is WhyState.ALIVE)
        base = alive / len(chain)
        if base <= 0.0:
            return 0.0
        score = base * self.freshness(nid)
        if any(n.probation for n in chain if n.state is WhyState.ALIVE):
            score = min(score, self.PROBATION_CAP)
        return score

    def reap(self, tick: Optional[int] = None) -> list:
        """Lapse long-unattested ALIVE nodes to UNKNOWN (never deletion).

        A node is lapsed when it has gone longer than the horizon without
        a heartbeat. Lapse is per-node — an unserved purpose questions
        ITSELF; it does not cascade like a kill (a kill says 'the lineage
        is wrong', a lapse says 'nobody served this'). Every lapse is
        recorded in the necrology and can only be undone by an explicit
        ``revive(reason)``. Returns the lapsed nodes, in id order.
        """
        if self.attestation_horizon is None:
            return []
        t = self.now if tick is None else tick
        h = self.attestation_horizon
        lapsed = []
        for n in sorted(self._nodes.values(), key=lambda x: x.id):
            if n.state is not WhyState.ALIVE:
                continue
            last = n.last_beat if n.last_beat >= 0 else n.born
            age = t - last
            if age > h:
                self._record(
                    n, WhyState.UNKNOWN,
                    f"lapsed: unattested for {age} ticks (horizon {h})", t,
                )
                lapsed.append(n)
        return lapsed

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
            "attestation_horizon": self.attestation_horizon,
            "now": self.now,
            "nodes": [
                {
                    "id": n.id, "parent": n.parent, "statement": n.statement,
                    "state": n.state.value, "born": n.born, "last_beat": n.last_beat,
                    "last_attested_by": n.last_attested_by, "probation": n.probation,
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
        tree = cls(attestation_horizon=data.get("attestation_horizon"))
        tree.now = data.get("now", 0)
        for nd in data["nodes"]:
            node = WhyNode(
                id=nd["id"], parent=nd["parent"], statement=nd["statement"],
                state=WhyState(nd["state"]), born=nd["born"], last_beat=nd["last_beat"],
                last_attested_by=nd.get("last_attested_by", ""),
                probation=nd.get("probation", False),
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
