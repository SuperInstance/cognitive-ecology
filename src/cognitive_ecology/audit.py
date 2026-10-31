"""The conservation auditor — necrology replay equivalence.

The WHY conservation law says purpose is never deleted. Until v0.3 that
was a property we *tested* (random storms, invariant counts) but could not
*prove* about a specific organism. This module makes it proof-carrying:

    GENESIS  +  NECROLOGY  +  ATTESTATION JOURNAL  =  REPLAY BASIS

* **genesis** — every declaration as born: identity, parent, statement,
  birth tick, birth state, birth heartbeat.
* **necrology** — every state transition, append-only, with from/to.
* **journal** — every attestation stamp: (tick, node, by).

``ConservationAuditor.verify(tree)`` replays that basis from nothing and
requires the reconstruction to equal the live tree — states, heartbeats,
provenance, parole — bit for bit. Any mutation that happened off the books
(a state flipped directly, a record removed, a log reordered, a stamp
forged) makes the receipt fail with the specific check named.

The receipt also carries a **hash chain** over the necrology (each record
chained to the digest of all before it): pin the chain head and any later
edit of history breaks it — the append-only property, checkable offline.

Replay semantics (from-state, to-state) -> effect, matching why.py:

    UNKNOWN -> ALIVE   revive          last_beat=tick, parole
    DEAD    -> ALIVE   resurrect       last_beat=tick, parole
    ABSENT  -> ALIVE   activate        last_beat=tick, no parole
    ALIVE   -> DEAD    kill            state only
    ALIVE   -> UNKNOWN lapse/cascade   state only
    ALIVE   -> ABSENT  park            state only

(ADR-0008; proposal adopted from live ideation round 004b.)
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from .why import WhyState, WhyTree


def _digest(rows) -> str:
    """Stable digest over a list of tuples of scalars."""
    h = hashlib.sha256()
    for row in rows:
        h.update(repr(row).encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


@dataclass
class ConservationReceipt:
    """The proof object. ``ok`` means: replay == live, bit for bit."""

    ok: bool
    checks: dict = field(default_factory=dict)
    live_digest: str = ""
    replay_digest: str = ""
    chain_head: str = ""          # hash chain over the necrology
    genesis_records: int = 0
    transition_records: int = 0
    journal_records: int = 0
    note: str = ""

    def summary(self) -> str:
        if self.ok:
            return (f"conservation receipt OK: {self.genesis_records} declared, "
                    f"{self.transition_records} transitions, "
                    f"{self.journal_records} stamps replayed; "
                    f"digest {self.live_digest[:16]}… chain {self.chain_head[:16]}…")
        failed = [k for k, v in self.checks.items() if not v]
        return f"CONSERVATION RECEIPT FAILED: {', '.join(failed)} ({self.note})"


class ConservationAuditor:
    """Replays the basis and compares against the living tree."""

    # -- the replay ------------------------------------------------------------

    def replay(self, genesis, necrology, journal):
        """Reconstruct (nodes, problems) from the basis alone.

        The basis is replayed CHRONOLOGICALLY on a single timeline with
        three phases at equal ticks (the example-08 play-test fix):
        to-ALIVE transitions first (a same-tick revive precedes the
        treaty-routed stamp that lands on the revived node), then
        stamps, then all other transitions (the runtime's per-tick
        order: act -> stamp -> reap; a questioned node refuses its
        stamp, so a stamp never follows its own question). Transitions
        apply in their LISTED order — an append-only log is
        chronological by construction, so a reordered history fails the
        log_order or transition_validity check.

        problems is a list of (check_name, detail) — empty means the log
        itself is internally consistent.
        """
        problems: list = []
        nodes: dict = {}
        for (nid, parent, statement, born, state, last_beat) in genesis:
            if nid in nodes:
                problems.append(("genesis_unique", f"duplicate genesis id {nid}"))
                continue
            nodes[nid] = {
                "id": nid, "parent": parent, "statement": statement,
                "born": born, "state": WhyState(state),
                "last_beat": last_beat, "last_attested_by": "", "probation": False,
            }

        # append-only logs are chronological; listed order is the truth order
        last_tick = -1
        for rec in necrology:
            if rec.tick < last_tick:
                problems.append((
                    "log_order",
                    f"transition at tick {rec.tick} follows one at {last_tick}: "
                    "history was reordered"))
            last_tick = rec.tick

        # three-phase equal-tick ordering (found by the example-08
        # play-test): a to-ALIVE transition at tick t applies BEFORE
        # stamps at t — a same-tick revive() must be on the books
        # before a treaty-routed stamp lands on the revived node
        # (society.py revives, then the exchange routes service).
        # All OTHER transitions apply AFTER stamps at the same tick —
        # the runtime's per-tick order is act -> stamp -> reap, and the
        # exchange's order is break-then-route, where a questioned node
        # REFUSES its stamp (heartbeat on non-ALIVE writes no journal
        # entry), so a stamp never follows its own question.
        def _phase(rec) -> int:
            return 0 if rec.to_state is WhyState.ALIVE else 2

        timeline = sorted(
            [(r.tick, _phase(r), i, ("t", r)) for i, r in enumerate(necrology)]
            + [(j[0], 1, i, ("j", j)) for i, j in enumerate(journal)],
            key=lambda x: (x[0], x[1], x[2]),
        )
        for _tick, _kind, _i, (what, item) in timeline:
            if what == "j":
                tick, nid, by = item
                if nid not in nodes:
                    problems.append(("stamp_known_node", f"stamp for unknown node {nid}"))
                    continue
                n = nodes[nid]
                if n["state"] is not WhyState.ALIVE:
                    problems.append((
                        "stamp_validity",
                        f"stamp on {nid} at tick {tick} but node is {n['state'].value}"))
                    continue
                n["last_beat"] = tick
                if by:
                    n["last_attested_by"] = by
                n["probation"] = False
            else:
                rec = item
                if rec.node_id not in nodes:
                    problems.append((
                        "transition_known_node", f"record for unknown node {rec.node_id}"))
                    continue
                n = nodes[rec.node_id]
                if n["state"] is not rec.from_state:
                    problems.append((
                        "transition_validity",
                        f"{rec.node_id} at tick {rec.tick}: log says "
                        f"{rec.from_state.value}->{rec.to_state.value} but node is "
                        f"{n['state'].value}",
                    ))
                    continue
                if n["statement"] != rec.statement:
                    problems.append((
                        "statement_consistency",
                        f"{rec.node_id}: record statement differs from genesis"))
                n["state"] = rec.to_state
                if rec.to_state is WhyState.ALIVE and rec.from_state in (
                    WhyState.UNKNOWN, WhyState.DEAD,
                ):
                    n["last_beat"] = rec.tick
                    n["probation"] = True
                elif rec.to_state is WhyState.ALIVE and rec.from_state is WhyState.ABSENT:
                    n["last_beat"] = rec.tick
        return nodes, problems

    # -- the comparison ----------------------------------------------------------

    @staticmethod
    def _live_rows(tree: WhyTree, ids: set | None = None) -> list:
        rows = []
        for n in sorted(tree.nodes(), key=lambda x: x.id):
            if ids is not None and n.id not in ids:
                continue
            rows.append((
                n.id, n.parent, n.statement, n.born, n.state.value,
                n.last_beat, n.last_attested_by, n.probation))
        return rows

    @staticmethod
    def _replayed_rows(nodes: dict) -> list:
        return [
            (n["id"], n["parent"], n["statement"], n["born"], n["state"].value,
             n["last_beat"], n["last_attested_by"], n["probation"])
            for _, n in sorted(nodes.items())
        ]

    def chain(self, necrology, journal=()) -> str:
        """Hash chain over necrology + attestation journal: pin the head,
        detect ANY edit of history — including a superseded stamp."""
        h = hashlib.sha256(b"genesis")
        for r in necrology:
            h.update(
                f"{r.tick}|{r.node_id}|{r.statement}|"
                f"{r.from_state.value}|{r.to_state.value}|{r.reason}".encode("utf-8")
            )
            h.update(b"\x1e")
        for (tick, nid, by) in journal:
            h.update(f"{tick}|{nid}|{by}".encode("utf-8"))
            h.update(b"\x1e")
        return h.hexdigest()

    def verify(self, tree: WhyTree) -> ConservationReceipt:
        genesis = tree.genesis()
        necrology = tree.necrology()
        journal = tree.journal()
        archived = set(tree.archived_ids())

        checks: dict = {}
        if not genesis:
            return ConservationReceipt(
                ok=False, checks={"genesis_present": False},
                note="no genesis block (pre-v0.3 tree or deserialized legacy "
                     "state): the replay basis is incomplete, so no receipt "
                     "can be issued",
            )
        checks["genesis_present"] = True
        checks["accounts_for_every_declaration"] = (
            len(genesis) == len(tree.nodes()) + len(archived))

        nodes, problems = self.replay(genesis, necrology, journal)
        for name, _detail in problems:
            checks[name] = False
        if not problems:
            checks["log_internally_consistent"] = True

        live_rows = self._live_rows(tree)  # hot nodes only
        replay_rows = self._replayed_rows(nodes)
        # state equivalence is over the HOT set; archived nodes must match
        # their manifest rows exactly (cold storage is verifiable too)
        hot_replay = [r for r in replay_rows if r[0] not in archived]
        checks["state_equivalence"] = live_rows == hot_replay
        manifest_ok = True
        if archived:
            manifest = {nid: tree.archived_row(nid) for nid in archived}
            for r in replay_rows:
                if r[0] not in archived:
                    continue
                m = manifest.get(r[0])
                if m is None:
                    manifest_ok = False
                    continue
                if (m["id"], m["parent"], m["statement"], m["born"], m["state"],
                        m["last_beat"], m.get("last_attested_by", ""),
                        m.get("probation", False)) != r:
                    manifest_ok = False
            checks["archive_manifest_equivalence"] = manifest_ok

        # conservation accounting, the cheap invariant, for the receipt
        counts = {s: 0 for s in WhyState}
        for n in tree.nodes():
            counts[n.state] += 1
        checks["conservation_accounting"] = (
            sum(counts.values()) + len(archived)
            == len(tree.nodes()) + len(archived) == len(genesis))

        ok = all(checks.values())
        return ConservationReceipt(
            ok=ok,
            checks=checks,
            live_digest=_digest(live_rows),
            replay_digest=_digest(hot_replay),  # hot-to-hot; cold is covered
            chain_head=self.chain(necrology, journal),
            genesis_records=len(genesis),
            transition_records=len(necrology),
            journal_records=len(journal),
            note="" if ok else "; ".join(f"{n}: {d}" for n, d in problems),
        )
