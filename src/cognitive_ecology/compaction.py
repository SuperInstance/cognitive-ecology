"""Journal compaction — the replay basis without the ballast (ADR-0014).

The attestation journal grows one entry per stamped node per winning
act: 60,000 entries at the 10,000-tick soak, and verify is O(journal)
— throughput fell from 6.4k to 2.3k ticks/s across the run. "Never
deleted" must not mean "never tidy" (the same argument that built
honest archival, ADR-0010).

What makes compaction HONEST:

1. **It preserves replay equivalence exactly.** The replay's final
   state per node needs only the LAST stamp per (node, ALIVE window):
   last_beat, provenance, and probation-clearing are all decided by
   the last stamp in a window. We keep the last stamp per
   (node, window, PROVENANCE) — a superset that additionally preserves
   each servant's evidence (the society's effective-sole check asks
   "did anything else ever stamp this node"; per-provenance lasts
   keep that answer inside the current window).
2. **It is receipted, never silent.** Compaction is a storage
   transition, not a history edit: every compaction appends a
   CompactionReceipt (counts, digest of the dropped entries, the chain
   head before and after) to an append-only list on the tree, and the
   auditor's hash chain covers the receipts — you cannot drop stamps
   and pretend nothing happened.
3. **The pre-compaction chain head is pinnable.** History before the
   last compaction is attested by the receipt's chain_before: pin it
   (or any earlier head) offline and any edit of the surviving basis
   still breaks against it. The federation auditor checks
   service-derivability for stamps AFTER the last compaction; older
   claims ride on the pinned head.

The necrology is NEVER compacted — it is the transition record, one
line per event, already minimal.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from .audit import ConservationAuditor
from .why import WhyState, WhyTree


@dataclass
class CompactionReceipt:
    """One deliberate, receipted exception to journal append-only."""

    tick: int               # the tree's now at compaction time
    entries_before: int     # journal length before
    entries_kept: int       # journal length after
    entries_dropped: int    # before - kept (redundant stamps)
    dropped_digest: str     # digest over the dropped entries, in order
    chain_before: str       # audit chain head before compaction
    chain_after: str        # audit chain head after (receipts included)

    def row(self) -> tuple:
        return (
            self.tick, self.entries_before, self.entries_kept,
            self.entries_dropped, self.dropped_digest,
            self.chain_before, self.chain_after,
        )

    def summary(self) -> str:
        return (f"compacted at tick {self.tick}: {self.entries_before} -> "
                f"{self.entries_kept} entries "
                f"({self.entries_dropped} redundant stamps dropped, digest "
                f"{self.dropped_digest[:12]}…)")


def _digest_entries(entries) -> str:
    h = hashlib.sha256()
    for e in entries:
        h.update(repr(tuple(e)).encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


class JournalCompactor:
    """Compacts a WhyTree's attestation journal, preserving replay."""

    def __init__(self, tree: WhyTree) -> None:
        self.tree = tree

    # -- the ALIVE windows -------------------------------------------------

    def _windows(self) -> dict:
        """node id -> list of (open_tick, close_tick|None) ALIVE windows,
        derived from the necrology (the transition record)."""
        windows: dict = {}
        # birth states come from genesis
        for (nid, _parents, _stmt, born, state, last_beat) in self.tree.genesis():
            if state == WhyState.ALIVE.value:
                windows[nid] = [(born, None)]
            else:
                windows[nid] = []
        for rec in self.tree.necrology():
            wins = windows.setdefault(rec.node_id, [])
            if rec.to_state is WhyState.ALIVE:
                wins.append((rec.tick, None))            # window opens
            elif wins and wins[-1][1] is None:
                wins[-1] = (wins[-1][0], rec.tick)       # window closes
        return windows

    def _window_of(self, windows: dict, nid: str, tick: int) -> int:
        """Which ALIVE window index does tick fall into (-1 none)."""
        for i, (lo, hi) in enumerate(windows.get(nid, [])):
            if tick >= lo and (hi is None or tick <= hi):
                return i
        return -1

    # -- the compaction ------------------------------------------------------

    def compact(self, tick: Optional[int] = None) -> Optional[CompactionReceipt]:
        """Keep the last stamp per (node, ALIVE window, provenance);
        drop the rest under a receipt. Idempotent: nothing to drop ->
        no receipt. Returns the receipt, or None."""
        tree = self.tree
        t = tree.now if tick is None else tick
        journal = list(tree.journal())
        if not journal:
            return None

        windows = self._windows()
        keep: dict = {}  # (nid, window_idx, by) -> entry (last wins)
        for entry in journal:
            ts, nid, by = entry
            w = self._window_of(windows, nid, ts)
            if w < 0:
                # a stamp outside any ALIVE window cannot replay anyway;
                # keep it so the auditor's validity check still sees it
                # (this is a corrupted-journal case, not ours to hide)
                keep[("!", ts, nid, by)] = entry
                continue
            keep[(nid, w, by)] = entry

        # preserve original relative order among the kept entries
        kept = [e for e in journal
                if self._is_kept(e, windows, keep)]
        if len(kept) == len(journal):
            return None  # nothing redundant; no receipt, no mutation

        dropped = [e for e in journal if e not in kept]
        chain_before = ConservationAuditor().chain(
            tree.necrology(), tree.journal(),
            tree.compactions() if hasattr(tree, "compactions") else ())
        receipt = CompactionReceipt(
            tick=t,
            entries_before=len(journal),
            entries_kept=len(kept),
            entries_dropped=len(dropped),
            dropped_digest=_digest_entries(dropped),
            chain_before=chain_before,
            chain_after="",  # filled after the journal is replaced
        )
        tree._replace_journal(kept, receipt)
        receipt.chain_after = ConservationAuditor().chain(
            tree.necrology(), tree.journal(), tree.compactions())
        return receipt

    def _is_kept(self, entry, windows: dict, keep: dict) -> bool:
        ts, nid, by = entry
        w = self._window_of(windows, nid, ts)
        if w < 0:
            return ("!", ts, nid, by) in keep
        return keep.get((nid, w, by)) is entry
