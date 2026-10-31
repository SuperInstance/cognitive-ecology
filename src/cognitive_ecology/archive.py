"""Honest archival — cold storage that is not deletion (ADR-0010).

A ten-year organism accumulates DEAD purposes. "Never deleted" must not
mean "never tidy": a hot tree with ten thousand dead nodes is slow to
walk, noisy to prompt, and dishonest about what the organism still
considers live.

What makes archival HONEST (OPEN_QUESTIONS #6, answered):

1. **Eligibility is conservative.** Only a DEAD node, dead longer than
   ``min_age`` ticks, with NO ALIVE descendant anywhere in its subtree
   (nothing living depends on this lineage), may be archived — and only
   together with its whole eligible subtree (parent references stay
   intact; no dangling chains).
2. **The books stay balanced.** Archived nodes are counted by
   ``conservation()`` — hot + archived == ever_declared, always.
3. **The biography travels.** The archive manifest carries each node's
   full row: statement, lineage, states, last heartbeat, provenance.
   The conservation auditor replays the genesis+necrology+journal basis
   and checks the manifest against the reconstruction — cold nodes are
   as verifiable as hot ones.
4. **Restoration is a ceremony, not a toggle.** ``restore()`` returns a
   node to the hot tree still DEAD, with a necrology record naming the
   reason; from there the normal ``resurrect(reason)`` (with parole)
   applies. Coming back from cold storage is two conscious acts, both
   recorded.

Archival is a STORAGE transition, never a STATE transition: the
necrology does not record archival itself (nothing about the node's
purpose changed), only the restore.
"""
from __future__ import annotations

from typing import Optional

from .why import WhyState, WhyTree


class ColdStorage:
    """Archives ancient DEAD subtrees out of the hot WHY tree."""

    def __init__(self, tree: WhyTree, min_age: int = 1000) -> None:
        if min_age < 1:
            raise ValueError("min_age must be >= 1")
        self.tree = tree
        self.min_age = min_age

    # -- eligibility --------------------------------------------------------------

    def _death_tick(self, nid: str) -> Optional[int]:
        """The tick of the most recent DEAD transition for this node."""
        last = None
        for r in self.tree.necrology():
            if r.node_id == nid and r.to_state is WhyState.DEAD:
                last = r.tick
        return last

    def eligible(self, nid: str, now: Optional[int] = None) -> bool:
        """DEAD, ancient, and nothing ALIVE in the subtree depends on it."""
        if not self.tree.has(nid):
            return False
        node = self.tree.node(nid)
        if node.state is not WhyState.DEAD:
            return False
        t = self.tree.now if now is None else now
        died = self._death_tick(nid)
        if died is None or (t - died) < self.min_age:
            return False
        # no living descendant may depend on this lineage
        for did in self.tree.descendants(nid):
            if self.tree.node(did).state is WhyState.ALIVE:
                return False
        return True

    # -- the sweep -----------------------------------------------------------------

    def sweep(self, now: Optional[int] = None) -> list:
        """Archive every eligible top-most DEAD subtree. Returns archived ids."""
        t = self.tree.now if now is None else now
        # a node whose PARENT is also eligible is archived with the parent
        roots = [
            n.id for n in self.tree.nodes()
            if self.eligible(n.id, t)
            and not (n.parent is not None and self.eligible(n.parent, t))
        ]
        archived = []
        for nid in sorted(roots):  # deterministic
            for row in self.tree._detach_subtree(nid):
                row["archived_at"] = t
                self.tree._archived[row["id"]] = row
                archived.append(row["id"])
        return archived

    # -- the ceremony ----------------------------------------------------------------

    def restore(self, nid: str, reason: str, tick: Optional[int] = None) -> None:
        """Return an archived subtree root to the hot tree (still DEAD).

        The reason is recorded in the necrology (DEAD -> DEAD: a storage
        transition made visible); from here, ``resurrect(reason)`` with
        parole applies as usual. Two conscious acts, both on the books.
        """
        if nid not in self.tree._archived:
            raise KeyError(f"{nid!r} is not in cold storage")
        if not reason or not reason.strip():
            raise ValueError("restoration requires a reason (the ceremony)")
        t = self.tree.now if tick is None else tick
        # restore the whole cold subtree: nid plus every archived node
        # whose parent chain leads back to it (or it would orphan the cold)
        restored = {nid}
        row = self.tree._archived.pop(nid)
        row.pop("archived_at", None)
        self.tree._attach_row(row)
        grew = True
        while grew:
            grew = False
            for did in list(self.tree._archived):
                if self.tree._archived[did].get("parent") in restored:
                    drow = self.tree._archived.pop(did)
                    drow.pop("archived_at", None)
                    self.tree._attach_row(drow)
                    restored.add(did)
                    grew = True
        node = self.tree.node(nid)
        self.tree._necrology.append(_restore_record(node, t, reason))

    def manifest(self) -> list:
        """The archive manifest, id-sorted — the biography of the cold."""
        return [
            dict(self.tree._archived[nid]) for nid in sorted(self.tree._archived)
        ]

    def summary(self) -> str:
        m = self.manifest()
        if not m:
            return "cold storage: empty"
        return (f"cold storage: {len(m)} nodes "
                f"(oldest archived at tick "
                f"{min(r['archived_at'] for r in m)})")


def _restore_record(node, tick: int, reason: str):
    from .why import NecroRecord
    return NecroRecord(
        tick=tick, node_id=node.id, statement=node.statement,
        from_state=WhyState.DEAD, to_state=WhyState.DEAD,
        reason=f"restored from cold storage: {reason}",
    )
