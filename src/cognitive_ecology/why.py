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
component whose WHY chain is broken (no fully-living path to a root)
does not run — but it is not deleted either. It waits, questionable,
revivable.

Contradictions are allowed (and detectable): a node can be ALIVE while
parts of its lineage are DEAD. The organism holds beliefs it cannot
fully justify — ``contradictions()`` finds them. This is a feature:
cognitive dissonance is information.

Multi-parent purposes — the WHY DAG (v0.4, ADR-0012)
-----------------------------------------------------
A purpose may be justified by SEVERAL parents: ``declare(...,
parents=("why:1", "why:2"))``. Verdict and justification use **best
path** semantics: a node runs while AT LEAST ONE path to a root is
fully ALIVE, and its justification is the strongest living path's —
killing one parent of a jointly-justified purpose does not question
it while the other parent's lineage still warrants it. A kill
cascades only descendants with NO surviving path (no over-cascade);
a cascade fixpoint handles cross-linked topologies where a deeper
parent's cascade strands a later node (no under-cascade). Parents are
fixed at declaration, so the DAG is acyclic by construction. Single
parent declare(parent=...) keeps the exact v0.2/v0.3 tree semantics;
``parent`` remains the primary (first) parent for compatibility.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional, Sequence


class WhyState(enum.Enum):
    ALIVE = "alive"        # asserting life; heartbeats accepted
    DEAD = "dead"          # explicitly killed; terminal without resurrection
    UNKNOWN = "unknown"    # questionable — an ancestor died; revivable
    ABSENT = "absent"      # declared but parked/draft; not asserting anything


@dataclass
class WhyNode:
    id: str
    parents: tuple = ()                 # DAG parents, primary first
    statement: str = ""
    state: WhyState = WhyState.ABSENT
    born: int = 0
    last_beat: int = -1
    last_attested_by: str = ""       # component whose winning act last stamped it
    probation: bool = False           # revived but not yet re-served ( parole )

    @property
    def parent(self) -> Optional[str]:
        """The primary parent (first declared), or None for roots.
        Kept for tree-shaped code; DAG-aware code uses ``parents``."""
        return self.parents[0] if self.parents else None


def _receipt_from_row(row) -> "object":
    """Rehydrate a CompactionReceipt row (late import: compaction.py
    imports why.py, so the dependency must not be at module load)."""
    from .compaction import CompactionReceipt
    return CompactionReceipt(
        tick=row[0], entries_before=row[1], entries_kept=row[2],
        entries_dropped=row[3], dropped_digest=row[4],
        chain_before=row[5], chain_after=row[6])


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
        # proof-carrying conservation (v0.3): the genesis block records every
        # declaration as born; the attestation journal records every stamp.
        # Together with the necrology they are a complete replay basis —
        # see audit.py and ADR-0008.
        self._genesis: list = []   # (id, parent, statement, born, state, last_beat)
        self._journal: list = []   # (tick, node_id, by)
        # honest archival (v0.3, ADR-0010): ancient DEAD subtrees leave the
        # hot tree for cold storage — counted, manifested, restorable.
        self._archived: dict = {}  # id -> full row dict + archived_at
        # journal compaction (v0.4, ADR-0014): deliberate, receipted
        # exceptions to journal append-only — see compaction.py
        self._compactions: list = []

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
        parents: Optional[Sequence[str]] = None,
    ) -> WhyNode:
        """Add a WHY node. Ids are auto-assigned (`why:1`, `why:2`, ...) unless given.

        ``parent=`` declares a single-parent (tree) node — the v0.2/v0.3
        shape. ``parents=(a, b, ...)`` declares a multi-parent (DAG)
        node, primary parent first; the two arguments are mutually
        exclusive. Parents are fixed at declaration, which keeps the
        purpose graph acyclic by construction.
        """
        if parents is not None and parent is not None:
            raise ValueError("pass parent= (tree) or parents= (DAG), not both")
        if parents is None:
            parents = (parent,) if parent is not None else ()
        parents = tuple(dict.fromkeys(parents))  # dedupe, keep order
        nid = node_id or f"why:{self._next + 1}"
        self._next += 1
        if nid in self._nodes:
            raise ValueError(f"duplicate WHY node id: {nid}")
        for p in parents:
            if p not in self._nodes:
                raise KeyError(f"unknown parent WHY node: {p}")
        node = WhyNode(
            id=nid, parents=parents, statement=statement, state=state,
            born=tick, last_beat=(tick if state is WhyState.ALIVE else -1),
        )
        self._nodes[nid] = node
        self._genesis.append(
            (nid, parents, statement, tick, state.value,
             tick if state is WhyState.ALIVE else -1)
        )
        for p in parents:
            self._children.setdefault(p, []).append(nid)
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
        return [n for n in self._nodes.values() if not n.parents]

    def descendants(self, nid: str) -> list:
        """All node ids below `nid` over ANY parent edge (BFS, deduped).
        In a DAG a descendant may be reachable through several paths;
        it is still one descendant."""
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
        """Mark DEAD. Living descendants with NO surviving path cascade
        to UNKNOWN (questionable). In a DAG a descendant kept alive by
        another parent's lineage does NOT cascade (no over-cascade);
        cross-linked topologies reach the answer by fixpoint (no
        under-cascade). Trees keep the exact v0.2 behavior: every
        living descendant cascades, in BFS order."""
        node = self._nodes[nid]
        if node.state is WhyState.DEAD:
            return node
        self._record(node, WhyState.DEAD, reason, tick)
        self._cascade_question(nid, tick,
                               f"cascade: ancestor {nid} died ({reason})")
        return node

    def _has_living_path(self, nid: str) -> bool:
        """Is there at least one fully-ALIVE path from nid to a root?
        (Used post-kill: DEAD/UNKNOWN links break a path; a path through
        another living parent survives.)"""
        stack, seen = [nid], set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            n = self._nodes[cur]
            if n.state is not WhyState.ALIVE and cur != nid:
                continue  # this link is broken; other parents may survive
            if not n.parents:
                return True  # reached a living root through living links
            stack.extend(n.parents)
        return False

    def _cascade_question(self, nid: str, tick: int, reason: str) -> None:
        """Question every living descendant of nid that has no surviving
        path. A single BFS pass is exact for trees (every descendant's
        only path ran through the killed node). A DAG can strand a node
        whose last living path ran through a *descendant* that cascades
        later in the same sweep — so survivors are re-checked until a
        full pass cascades nothing. Monotone (UNKNOWN only grows), so
        the fixpoint terminates in at most one round per cascade."""
        pending = self.descendants(nid)
        while pending:
            survivors = []
            cascaded = False
            for did in pending:
                dn = self._nodes[did]
                if dn.state is WhyState.ALIVE and not self._has_living_path(did):
                    self._record(dn, WhyState.UNKNOWN, reason, tick)
                    cascaded = True
                elif dn.state is WhyState.ALIVE:
                    survivors.append(did)
            if not cascaded or not survivors:
                break
            pending = survivors

    def question(self, nid: str, reason: str, tick: int = 0,
                 by: str = "") -> WhyNode:
        """ALIVE -> UNKNOWN: doubt arrived from OUTSIDE the organism.

        This is the external-doubt transition — the mirror of revive().
        The runtime itself never calls it; it exists for society-level
        organs (society.py, ADR-0011) to record that the basis of a
        purpose changed somewhere else: a treaty partner died, a
        federation auditor challenged the lineage. Like a lapse, it
        questions the node itself without cascading — descendants stay
        formally alive but verdict-blocked, and ``contradictions()``
        will find them. Like everything else: recorded, never deleted,
        revivable by an explicit ``revive(reason)``.

        ``by`` names the doubter (round 011): the books record WHO
        questioned the purpose, not merely that it was questioned —
        society questions carry ``by="society"``; an unnamed doubter
        is recorded as such.
        """
        node = self._nodes[nid]
        if node.state is not WhyState.ALIVE:
            return node  # already questioned or dead: nothing to doubt
        recorded = f"{reason} (doubted by {by})" if by else reason
        self._record(node, WhyState.UNKNOWN, recorded, tick)
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
        """A revived ancestor re-resolves the questions it raised: every
        UNKNOWN descendant that would have a fully-living path (all its
        ancestors on some path ALIVE, the node itself excluded — its own
        UNKNOWN-ness is what we are deciding) returns, on parole. A
        descendant whose every path still runs through a DEAD ancestor
        keeps its doubt (that parent's kill still stands). Trees keep
        the exact v0.2 behavior: BFS order, everything revives; DAGs
        reach cross-linked answers by fixpoint, like the cascade."""
        pending = self.descendants(nid)
        while pending:
            remaining, revived = [], False
            for did in pending:
                dn = self._nodes[did]
                if dn.state is WhyState.UNKNOWN and self._would_have_living_path(did):
                    self._record(
                        dn, WhyState.ALIVE, f"cascade: ancestor {nid} revived", tick
                    )
                    dn.last_beat = tick
                    dn.probation = True  # cascaded revivals are on parole too
                    revived = True
                elif dn.state is WhyState.UNKNOWN:
                    remaining.append(did)
            if not revived or not remaining:
                break
            pending = remaining

    def _would_have_living_path(self, nid: str) -> bool:
        """Would this node have a fully-living path if it were ALIVE?
        (Every ancestor on some path ALIVE; the node itself excluded —
        used by the revive cascade, where the node's own state is the
        question being decided.)"""
        for path in self.paths(nid):
            if all(n.state is WhyState.ALIVE for n in path[1:]):
                return True
        return False

    def _ancestors_ids(self, nid: str) -> set:
        """Every ancestor over ANY parent edge (the DAG union)."""
        out: set = set()
        stack = list(self._nodes[nid].parents)
        while stack:
            cur = stack.pop()
            if cur in out or cur not in self._nodes:
                continue
            out.add(cur)
            stack.extend(self._nodes[cur].parents)
        return out

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
        """Stamp liveness. Returns False if the node is not ALIVE.

        Stamps are MONOTONIC (the round-015 society-soak fix): a stamp
        carrying a tick older than the node's current last_beat is a
        no-op — stale information must never rewind freshness. This is
        what makes journal compaction safe for the society: after a
        compaction invalidates the exchange's positional cursors, the
        resync may re-consume already-routed stamps, and a re-routed
        old stamp changes nothing (no state, no journal entry).
        """
        node = self._nodes[nid]
        if node.state is WhyState.ALIVE:
            if tick < node.last_beat:
                return True  # stale: accepted, but nothing to learn
            node.last_beat = tick
            if by:
                node.last_attested_by = by
            node.probation = False  # genuine service ends parole
            self._journal.append((tick, nid, by))
            return True
        return False

    def stamp_chain(self, nid: str, tick: int, by: str = "") -> int:
        """Re-attest a purpose by USE: stamp every ALIVE node leaf -> root.

        Serving a purpose maintains its whole lineage — a running child
        keeps its roots fresh — and ends any probation along the way.
        In a DAG the lineage is the union of ALL paths: serving a
        jointly-justified purpose maintains both of its parents' lines.
        Stamp order is the primary path first (leaf -> root — the exact
        v0.2/v0.3 tree order), then any extra ancestors in path order,
        so journals stay byte-compatible for tree-shaped organisms.
        Returns how many nodes took the stamp.
        """
        took = 0
        order, seen = [nid], {nid}
        for path in self.paths(nid):
            for n in path[1:]:  # path[0] is nid itself
                if n.id not in seen:
                    seen.add(n.id)
                    order.append(n.id)
        for aid in order:
            if self.heartbeat(aid, tick, by=by):
                took += 1
        return took

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def chain(self, nid: str) -> list:
        """The PRIMARY ancestry, leaf -> root (first parent at each step).
        DAG-aware code wants ``paths()`` (all paths) or ``_ancestors_ids``
        (the union); this stays for tree-shaped callers and readability."""
        out: list = []
        seen: set = set()
        cur: Optional[WhyNode] = self._nodes[nid]
        while cur is not None and cur.id not in seen:
            out.append(cur)
            seen.add(cur.id)
            cur = self._nodes[cur.parent] if cur.parent else None
        return out

    def paths(self, nid: str) -> list:
        """Every path from nid to a root, each a list of WhyNodes
        (leaf -> root), in deterministic DFS order (primary parents
        first). A tree has exactly one path."""
        out: list = []

        def walk(cur: str, acc: list, seen: set) -> None:
            node = self._nodes[cur]
            if cur in seen:  # defensive: acyclic by construction
                return
            acc.append(node)
            if not node.parents:
                out.append(list(acc))
            else:
                for p in node.parents:
                    walk(p, acc, seen | {cur})
            acc.pop()

        walk(nid, [], set())
        return out

    def freshness(self, nid: str, tick: Optional[int] = None) -> float:
        """Weakest-link freshness of the BEST living path, 0..1.

        Full freshness through the first third of the horizon (the grace
        window — a new purpose gets time to establish), then linear decay
        to zero at the horizon. With no horizon configured, always 1.0.
        In a DAG each path is priced independently and the best wins —
        a purpose served through either parent is fresh through that
        parent (OR semantics, matching verdict()).
        """
        if self.attestation_horizon is None:
            return 1.0
        return max(
            (self._path_freshness(p, tick) for p in self.paths(nid)),
            default=0.0,
        )

    def _path_freshness(self, path: list, tick: Optional[int]) -> float:
        if self.attestation_horizon is None:
            return 1.0  # no economics configured: freshness is not priced
        t = self.now if tick is None else tick
        h = self.attestation_horizon
        grace = h // 3
        worst = 1.0
        for n in path:
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
        """How justifiable is this node, 0..1 — the BEST living path's score.

        A path with a DEAD ancestor anywhere scores 0 (that lineage's
        warrant is destroyed); otherwise the path scores its alive
        fraction (UNKNOWN ancestors discount proportionally) multiplied
        by its weakest-link FRESHNESS, capped at PROBATION_CAP while any
        ALIVE node on THAT path is on parole. The node's justification
        is the strongest path's score — in a DAG a jointly-justified
        purpose is as strong as its best living basis (OR semantics,
        matching verdict()); a tree has exactly one path, so this is
        the exact v0.2/v0.3 score. Liveness attested long ago is worth
        less than liveness maintained; liveness *asserted* without
        service is worth half.
        """
        if tick is not None:
            self.now = tick  # explicit tick advances the tree's clock
        best = 0.0
        for path in self.paths(nid):
            if any(n.state is WhyState.DEAD for n in path):
                continue  # this lineage's warrant is destroyed
            alive = sum(1 for n in path if n.state is WhyState.ALIVE)
            base = alive / len(path)
            if base <= 0.0:
                continue
            score = base * self._path_freshness(path, tick)
            if any(n.probation for n in path if n.state is WhyState.ALIVE):
                score = min(score, self.PROBATION_CAP)
            if score > best:
                best = score
        return best

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
        """Full answer to 'should this run?', with the blocking node named.

        OK iff at least ONE path to a root is fully ALIVE (OR
        semantics). On failure the reported path is the one that got
        furthest leaf->root (most living warrant), with its proximate
        blocker named — a tree keeps the exact v0.2 single-path answer.
        """
        best_path, best_prefix, blocker = None, -1, None
        for path in self.paths(nid):
            prefix = 0
            for n in path:  # leaf -> root: count the living warrant
                if n.state is WhyState.ALIVE:
                    prefix += 1
                else:
                    if best_prefix == -1 or prefix > best_prefix:
                        best_path, best_prefix, blocker = path, prefix, n
                    break
            else:
                return WhyVerdict(
                    ok=True, reason="ok", path=[n.id for n in path]
                )
        if best_path is None:  # no paths at all should not happen; be safe
            return WhyVerdict(ok=False, reason="unknown", path=[nid],
                              blocked_at=nid, blocked_state=self._nodes[nid].state)
        b = blocker
        return WhyVerdict(
            ok=False, reason=f"{b.state.value}:{b.id}",
            path=[n.id for n in best_path], blocked_at=b.id, blocked_state=b.state,
        )

    def why_should_this_run(self, nid: str) -> bool:
        """The heartbeat question. Asked of every component, every tick."""
        return self.verdict(nid).ok

    def contradictions(self) -> list:
        """ALIVE nodes whose warrant is destroyed but still asserted:
        no fully-living path AND at least one DEAD ancestor. A node
        kept alive by another parent's lineage is NOT a contradiction
        (it has living warrant); a node blocked only by UNKNOWN
        (doubtful) ancestors is questionable, not contradictory. A tree
        reduces to the v0.2 rule exactly: ALIVE with a DEAD ancestor."""
        out = []
        for n in self._nodes.values():
            if n.state is not WhyState.ALIVE:
                continue
            anc = self._ancestors_ids(n.id)
            if not anc:
                continue  # a living root has living warrant (itself)
            if any(self._nodes[a].state is WhyState.DEAD for a in anc) \
                    and not self._has_living_path(n.id):
                out.append(n)
        return out

    def necrology(self) -> tuple:
        """Every purpose transition, ever. Append-only."""
        return tuple(self._necrology)

    def genesis(self) -> tuple:
        """Every declaration as born: (id, parents, statement, tick,
        state, last_beat). The parents field is a tuple (primary first);
        legacy single-parent rows load as one-parent tuples.

        The first block of the replay basis (audit.py)."""
        return tuple(self._genesis)

    def journal(self) -> tuple:
        """Every attestation stamp, in order: (tick, node_id, by).

        The third block of the replay basis (audit.py)."""
        return tuple(self._journal)

    def archived_ids(self) -> tuple:
        """Ids in cold storage (ADR-0010). Counted by conservation();
        biographied by the archive manifest; restorable by ceremony."""
        return tuple(sorted(self._archived))

    def archived_row(self, nid: str) -> dict:
        return dict(self._archived[nid])

    def compactions(self) -> tuple:
        """Every journal compaction ever performed, with receipts
        (ADR-0014). Append-only like everything that touches history."""
        return tuple(self._compactions)

    def _replace_journal(self, kept: list, receipt) -> None:
        """Swap in a compacted journal under a receipt. Internal — only
        JournalCompactor (compaction.py) may call this, and only with a
        receipt naming what was dropped. There is no other API that
        removes a journal entry."""
        self._journal = list(kept)
        self._compactions.append(receipt)

    def _detach_subtree(self, nid: str) -> list:
        """Remove nid and its descendants from the hot tree. Internal —
        only ColdStorage (archive.py) may call this, and only for
        eligible DEAD subtrees. Returns the removed full rows."""
        ids = [nid] + self.descendants(nid)
        rows = []
        for i in ids:
            n = self._nodes.pop(i)
            self._children.pop(i, None)
            rows.append({
                "id": n.id, "parents": list(n.parents),
                "parent": n.parent, "statement": n.statement,
                "born": n.born, "state": n.state.value, "last_beat": n.last_beat,
                "last_attested_by": n.last_attested_by, "probation": n.probation,
            })
        # drop dangling child-map entries pointing at detached ids
        for i in ids:
            for kids in self._children.values():
                if i in kids:
                    kids.remove(i)
        return rows

    def _attach_row(self, row: dict) -> None:
        """Rehydrate one archived row into the hot tree (restore ceremony)."""
        parents = tuple(row.get("parents") or ()) or (
            (row["parent"],) if row.get("parent") else ()
        )
        node = WhyNode(
            id=row["id"], parents=parents, statement=row["statement"],
            state=WhyState(row["state"]), born=row["born"],
            last_beat=row["last_beat"],
            last_attested_by=row.get("last_attested_by", ""),
            probation=row.get("probation", False),
        )
        self._nodes[node.id] = node
        for p in node.parents:
            self._children.setdefault(p, []).append(node.id)

    def conservation(self) -> dict:
        """The audit: states must always account for every node ever declared.

        Nodes in cold storage count too — archival is a storage change,
        never a deletion (ADR-0010)."""
        counts = {s: 0 for s in WhyState}
        for n in self._nodes.values():
            counts[n.state] += 1
        hot = sum(counts.values())
        total = hot + len(self._archived)
        return {
            "ever_declared": self._ever_declared,
            "alive": counts[WhyState.ALIVE],
            "dead": counts[WhyState.DEAD],
            "unknown": counts[WhyState.UNKNOWN],
            "absent": counts[WhyState.ABSENT],
            "archived": len(self._archived),
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
            depth = max((len(p) for p in self.paths(n.id)), default=1) - 1
            lines.append(f"{'  ' * depth}- {n.statement}  [{n.id}]")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "attestation_horizon": self.attestation_horizon,
            "now": self.now,
            "genesis": [self._genesis_row(g) for g in self._genesis],
            "journal": [list(j) for j in self._journal],
            "compactions": [
                list(r.row()) for r in self._compactions
            ],
            "archived": {nid: dict(row) for nid, row in self._archived.items()},
            "nodes": [
                {
                    "id": n.id, "parents": list(n.parents), "parent": n.parent,
                    "statement": n.statement,
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

    @staticmethod
    def _genesis_row(g: tuple) -> list:
        """Serialize a genesis row, normalizing the parents field to a
        list (DAG) while emitting legacy-compatible single-parent rows
        for trees: (id, parents_list, statement, born, state, last_beat)."""
        nid, par, statement, born, state, last_beat = g
        return [nid, list(par), statement, born, state, last_beat]

    @staticmethod
    def _normalize_genesis(g) -> tuple:
        """Accept both v0.4 rows (parents at index 1) and v0.3 rows
        (a single parent string or None at index 1); always return the
        v0.4 shape with a parents tuple."""
        nid, par, statement, born, state, last_beat = g
        if isinstance(par, str):
            par = (par,)
        elif par is None:
            par = ()
        else:
            par = tuple(par)
        return (nid, par, statement, born, state, last_beat)

    @classmethod
    def from_json(cls, data: dict) -> "WhyTree":
        tree = cls(attestation_horizon=data.get("attestation_horizon"))
        tree.now = data.get("now", 0)
        tree._genesis = [cls._normalize_genesis(g) for g in data.get("genesis", [])]
        tree._journal = [tuple(j) for j in data.get("journal", [])]
        tree._compactions = [
            _receipt_from_row(r) for r in data.get("compactions", [])
        ]
        tree._archived = {nid: dict(row) for nid, row in data.get("archived", {}).items()}
        for nd in data["nodes"]:
            parents = tuple(nd.get("parents") or ()) or (
                (nd["parent"],) if nd.get("parent") else ()
            )
            node = WhyNode(
                id=nd["id"], parents=parents, statement=nd["statement"],
                state=WhyState(nd["state"]), born=nd["born"], last_beat=nd["last_beat"],
                last_attested_by=nd.get("last_attested_by", ""),
                probation=nd.get("probation", False),
            )
            tree._nodes[node.id] = node
            for p in node.parents:
                tree._children.setdefault(p, []).append(node.id)
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
