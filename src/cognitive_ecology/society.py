"""L9 — Society: WHY federation across organisms (ADR-0011).

One organism's purpose basis is local — until it isn't. The moment two
organisms exist, a new kind of purpose appears: **delegated purpose**,
A's purpose whose service happens inside B. A research assistant that
leans on an external archive; an agent whose "keep the shared index
fresh" is only ever served by a teammate.

The society must inherit the kernel's first law — purpose is never
deleted, *across* organisms, not just within one. So a society here is
not a message bus and not a shared memory. It is three things:

* **TREATIES** — the foreign purpose reference. A recorded, append-only
  relationship: beneficiary A's node ``a`` is served by provider B's
  node ``b``. The ledger is the registry of foreign references; the
  WhyNode rows stay untouched (a basis field would churn every existing
  conservation receipt for no semantic gain).

* **THE EXCHANGE** — treaties route attestation, nothing else. When B's
  runtime stamps B's provider chain (a component under ``b`` won), the
  society re-stamps A's beneficiary chain *on A's own books*, with
  provenance ``treaty:<id>``. That single rule composes with everything
  v0.3 already enforces:

    - freshness: A's chain stays fresh exactly as long as B serves —
      sparse service decays A's bids before anything formally breaks;
    - lapse: with an attestation horizon, a neglected delegation
      strangulates to UNKNOWN on A's own books (the SOFT path);
    - provenance: every routed stamp is journaled on A with the treaty
      id. Nothing flows silently.

  Chain-stamping composes with treaties for free: any descendant of
  ``b`` that wins stamps ``b`` itself, so "a stamp landed on ``b``" is
  exactly "the provider purpose was served," no matter which child did.

* **THE FEDERATION AUDITOR** — do these books AGREE? Every
  treaty-provenance stamp on A must be derivable from B's journal
  (forged service is detectable); no treaty may still be active with a
  dead endpoint; every provider-side break must have its question()
  receipt on A's necrology. Plus a hash chain over the ledger: pin the
  head, detect any edit of society history offline.

Death vs neglect
----------------
Two failure modes, two propagations:

* **HARD (event-driven):** B's provider node transitions to DEAD or
  UNKNOWN. The delegation is *known broken*: the treaty breaks and —
  if it was the node's sole basis — A's node is QUESTIONED
  (ALIVE -> UNKNOWN, recorded, revivable). Immediate, explicit.
* **SOFT (economic):** B's node stays ALIVE but stops serving. No
  event fires; A's stamps stop, and A's own reaper does the rest at
  A's own pace. *Doubtful* is not *broken* — the distinction mirrors
  the UNKNOWN/ALIVE epistemology one level up.

A treaty is active only while BOTH endpoints are ALIVE: B's provider
death breaks it, and so does A's beneficiary death (killed, lapsed, or
archived to cold storage). Broken treaties stay in the ledger forever.
A may revive its node and establish a NEW treaty — or start serving the
purpose locally; the node was always A's.

Clocks
------
``Society.step()`` ticks members in lockstep (join order — that order
is part of the society's determinism) and then runs one exchange.
Delegation latency is therefore one step per hop: treaty-routed stamps
become visible to downstream treaties on the NEXT exchange, which is
what makes delegation chains (A -> B -> C) cycle-safe. ``exchange()``
is public for manual drivers at your own risk: cursors make it
idempotent, but freshness semantics assume lockstep ticks.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from .events import EventKind
from .why import WhyState


ACTIVE, BROKEN, REVOKED = "active", "broken", "revoked"


@dataclass
class Treaty:
    """One foreign purpose reference: A's node is served by B's node.

    ``sole_basis`` (default) declares A's node is served ONLY by this
    treaty — at most one active sole treaty may name a beneficiary
    node. A non-sole treaty stacks: the node can also be served
    locally (or by other treaties), and the treaty's death leaves the
    node standing on whatever remains.

    The lifecycle is append-only like everything else in the kernel:
    active -> broken | revoked, never back, never removed.
    """

    id: str
    provider: str                # member name of the serving organism (B)
    provider_node: str           # B's WHY node that does the serving
    beneficiary: str             # member name of the owning organism (A)
    beneficiary_node: str        # A's WHY node whose basis is foreign
    statement: str               # what the delegation is FOR
    tick: int                    # established at
    sole_basis: bool = True
    status: str = ACTIVE
    broken_at: Optional[int] = None
    broken_reason: str = ""

    def row(self) -> tuple:
        """Stable tuple for hashing/serialization."""
        return (
            self.id, self.provider, self.provider_node,
            self.beneficiary, self.beneficiary_node, self.statement,
            self.tick, self.sole_basis, self.status,
            self.broken_at if self.broken_at is not None else -1,
            self.broken_reason,
        )


@dataclass
class ExchangeRecord:
    """Telemetry for one thing the exchange did."""

    treaty_id: str
    what: str          # "service" | "broken" | "established" | "revoked"
    provider: str
    beneficiary: str
    detail: str
    tick: int


def _chain_ids(tree, nid: str) -> set:
    """Ids from ``nid`` up through ALL its ancestors (the DAG union),
    tolerating cold-storage exits.

    Uses only public surfaces (hot nodes, archived rows) so a broken
    treaty's historical stamps stay verifiable after the beneficiary
    subtree has been swept to cold storage. In a DAG a stamp routed
    onto a multi-parent node maintains every parent's line, so the
    service check walks every parent edge.
    """
    out: set = set()
    frontier = [nid]
    seen: set = set()
    while frontier:
        cur = frontier.pop()
        if cur in seen:
            continue
        seen.add(cur)
        out.add(cur)
        if tree.has(cur):
            frontier.extend(tree.node(cur).parents)
        elif cur in tree.archived_ids():
            parents = tuple(tree.archived_row(cur).get("parents") or ()) or (
                (tree.archived_row(cur)["parent"],)
                if tree.archived_row(cur).get("parent") else ()
            )
            frontier.extend(parents)
        # else: neither hot nor archived — the walk cannot continue
    return out


@dataclass
class FederationReceipt:
    """The proof object for the society. ``ok`` means: the books agree."""

    ok: bool
    checks: dict = field(default_factory=dict)
    chain_head: str = ""
    treaty_records: int = 0
    members: int = 0
    note: str = ""

    def summary(self) -> str:
        if self.ok:
            return (f"federation receipt OK: {self.members} members, "
                    f"{self.treaty_records} treaties, chain "
                    f"{self.chain_head[:16]}…")
        failed = [k for k, v in self.checks.items() if not v]
        return f"FEDERATION RECEIPT FAILED: {', '.join(failed)} ({self.note})"


class Society:
    """A set of organisms plus the treaty exchange between them.

    The society never reaches inside a member: it consumes public
    append-only logs (journals, necrologies) and calls public
    transitions (``stamp_chain``, ``question``). Members save
    themselves; the society serializes its own ledger and cursors.
    """

    def __init__(self, name: str = "society") -> None:
        self.name = name
        self._members: dict = {}          # name -> Runtime (join order kept)
        self._treaties: list[Treaty] = []  # append-only ledger
        self._next = 0
        # how far into each member's logs the last exchange read:
        # name -> {"journal": pos, "necrology": pos,
        #          "epoch": compactions_seen, "last": last consumed triple}.
        # Idempotent re-runs. Positions are invalid across journal
        # compactions (ADR-0014), so the epoch is tracked and the
        # cursor resyncs when a member's journal shrinks.
        self._cursors: dict = {}

    # ------------------------------------------------------------------
    # membership
    # ------------------------------------------------------------------
    def join(self, runtime, name: Optional[str] = None) -> str:
        """A runtime becomes a member. Join order is the tick order."""
        if name is None:
            name = runtime.identity.name if runtime.identity else f"org:{len(self._members) + 1}"
        if name in self._members:
            raise ValueError(f"duplicate member name: {name}")
        self._members[name] = runtime
        # start watching from NOW: only post-join activity exchanges
        self._cursors[name] = {
            "journal": len(runtime.why.journal()),
            "necrology": len(runtime.why.necrology()),
            "epoch": len(runtime.why.compactions())
            if hasattr(runtime.why, "compactions") else 0,
            "last": None,
        }
        return name

    def member(self, name: str):
        return self._members[name]

    def members(self) -> dict:
        return dict(self._members)

    # ------------------------------------------------------------------
    # the treaty ledger
    # ------------------------------------------------------------------
    def establish_treaty(
        self,
        provider: str,
        provider_node: str,
        beneficiary: str,
        beneficiary_node: str,
        statement: str,
        tick: Optional[int] = None,
        sole_basis: bool = True,
    ) -> Treaty:
        """Record a foreign purpose reference: A's node is served by B's.

        Both endpoints must be ALIVE (and hot) in their own trees at
        establishment — a treaty onto a dead purpose is dead on arrival
        and is refused. At most one ACTIVE sole treaty may name a
        beneficiary node: 'served only by this' cannot be said twice.
        """
        for m in (provider, beneficiary):
            if m not in self._members:
                raise KeyError(f"unknown member: {m!r} (join first)")
        p, b = self._members[provider], self._members[beneficiary]
        if not p.why.has(provider_node):
            raise KeyError(f"provider node {provider_node!r} not in {provider}'s hot tree")
        if not b.why.has(beneficiary_node):
            raise KeyError(f"beneficiary node {beneficiary_node!r} not in {beneficiary}'s hot tree")
        if p.why.node(provider_node).state is not WhyState.ALIVE:
            raise ValueError(
                f"provider node {provider_node} is {p.why.node(provider_node).state.value}: "
                "treaties require a living provider purpose")
        if b.why.node(beneficiary_node).state is not WhyState.ALIVE:
            raise ValueError(
                f"beneficiary node {beneficiary_node} is "
                f"{b.why.node(beneficiary_node).state.value}: "
                "treaties require a living beneficiary purpose")
        for t in self._treaties:
            if t.status == ACTIVE:
                if (
                    t.beneficiary == beneficiary
                    and t.beneficiary_node == beneficiary_node
                    and t.sole_basis and sole_basis
                ):
                    raise ValueError(
                        f"{beneficiary_node} already has an active sole treaty "
                        f"({t.id}): 'served only by' cannot be said twice")
                if (
                    t.provider == provider and t.provider_node == provider_node
                    and t.beneficiary == beneficiary
                    and t.beneficiary_node == beneficiary_node
                ):
                    raise ValueError(f"treaty {t.id} is already active for this pair")

        self._next += 1
        t = Treaty(
            id=f"treaty:{self._next}", provider=provider,
            provider_node=provider_node, beneficiary=beneficiary,
            beneficiary_node=beneficiary_node, statement=statement,
            tick=tick if tick is not None else self._society_tick(),
            sole_basis=sole_basis,
        )
        self._treaties.append(t)
        self._emit_both(t, "established", t.tick, statement)
        return t

    def revoke_treaty(self, treaty_id: str, reason: str, tick: Optional[int] = None) -> Treaty:
        """The beneficiary withdraws (voluntary). The purpose is NOT
        questioned — revocation only stops the foreign service; the
        node stands on whatever serves it locally, or strangulates by
        A's own economics if nothing does."""
        t = self._by_id(treaty_id)
        if t.status != ACTIVE:
            raise ValueError(f"treaty {treaty_id} is {t.status}: only active treaties revoke")
        t.status = REVOKED
        t.broken_at = tick if tick is not None else self._society_tick()
        t.broken_reason = f"revoked: {reason}"
        self._emit_both(t, "revoked", t.broken_at, reason)
        return t

    def treaties(self) -> tuple:
        return tuple(self._treaties)

    def active_treaties(self) -> tuple:
        return tuple(t for t in self._treaties if t.status == ACTIVE)

    def _by_id(self, treaty_id: str) -> Treaty:
        for t in self._treaties:
            if t.id == treaty_id:
                return t
        raise KeyError(f"unknown treaty: {treaty_id}")

    def _society_tick(self) -> int:
        return max((rt.tick_no for rt in self._members.values()), default=0)

    def _has_other_servant(self, t: Treaty, b_rt) -> bool:
        """Was the beneficiary node EVER served by anything other than
        this treaty? (round 011: sole-ness as fact, not declaration)

        A "servant" is a stamp ON THE NODE ITSELF with a different
        provenance: a local component (its own win, or a descendant's —
        chain-stamping makes both land here) or another ACTIVE treaty
        that has actually routed service. Stamps on mere ANCESTORS do
        not count: A's local work under a sibling purpose stamps the
        shared root without ever serving this node. A dead-weight
        treaty that never served does not count either — declaring
        non-sole is free, but only real service backs the declaration.
        """
        for (_ts, nid, by) in b_rt.why.journal():
            if nid != t.beneficiary_node or by == t.id:
                continue
            if by.startswith("treaty:"):
                other = next(
                    (o for o in self._treaties if o.id == by), None)
                if other is None or other.status != ACTIVE:
                    continue  # broken/revoked/unknown: not a servant
            return True  # a local stamp, or a living second treaty
        return False

    def _emit_both(self, t: Treaty, what: str, ts: int, detail: str) -> None:
        """A treaty lifecycle change is noticed by BOTH parties."""
        for name in (t.provider, t.beneficiary):
            rt = self._members[name]
            rt.bus.emit(
                EventKind.EXCHANGE,
                (t.id, what, t.provider, t.beneficiary, detail),
                src="society", ts=ts,
            )

    # ------------------------------------------------------------------
    # the exchange
    # ------------------------------------------------------------------
    def exchange(self, tick: Optional[int] = None) -> list:
        """One round of the protocol: route service, propagate breaks.

        Deterministic order: breaks first (a death at tick t beats a
        stamp at tick t), then service routing for surviving treaties,
        then cursors advance. Treaty-routed stamps land in a member's
        journal AFTER its slice was read here, so they flow to any
        downstream treaty on the NEXT exchange — one hop of delegation
        per society step, cycle-safe by construction.
        """
        if not self._members:
            return []
        t_now = tick if tick is not None else self._society_tick()

        # snapshot the new log slices once; everything below reads
        # these frozen lists, never the live logs (a question() we
        # write mid-exchange must not be re-processed this round).
        # Journal compaction (ADR-0014) shrinks a member's journal and
        # invalidates positional cursors — resync by locating the last
        # consumed entry in the compacted journal (order is preserved,
        # only entries drop). If it was itself dropped, re-consume the
        # small compacted journal from the start: safe because stamps
        # are monotonic (a re-routed old stamp is a no-op).
        stamps: dict = {}      # name -> [(tick, node_id, by)]
        transitions: dict = {}  # name -> [NecroRecord]
        for name, rt in self._members.items():
            cur = self._cursors[name]
            journal = list(rt.why.journal())
            epoch = (len(rt.why.compactions())
                     if hasattr(rt.why, "compactions") else 0)
            if epoch != cur["epoch"] or cur["journal"] > len(journal):
                pos = 0
                last = cur.get("last")
                if last is not None:
                    for i, entry in enumerate(journal):
                        if entry == last:
                            pos = i + 1  # exact: resume after it
                            break
                cur["journal"] = pos
                cur["epoch"] = epoch
            stamps[name] = journal[cur["journal"]:]
            transitions[name] = list(rt.why.necrology())[cur["necrology"]:
                                      ] if cur["necrology"] <= len(
                rt.why.necrology()) else []

        records: list = []
        died = WhyState.DEAD, WhyState.UNKNOWN

        # -- 1. breaks: a treaty is active only while both ends live --
        for t in self._treaties:
            if t.status != ACTIVE:
                continue
            p_rt = self._members[t.provider]
            b_rt = self._members[t.beneficiary]

            # provider side: B's purpose died or was questioned in B
            for rec in transitions.get(t.provider, ()):  # frozen slice
                if rec.node_id == t.provider_node and rec.to_state in died:
                    reason = (f"{t.id} broken: provider purpose "
                              f"{t.provider}/{t.provider_node} is "
                              f"{rec.to_state.value} ({rec.reason})")
                    t.status = BROKEN
                    t.broken_at = rec.tick
                    t.broken_reason = reason
                    # the hard path: a delegation taking its beneficiary's
                    # purpose with it — questioned, never deleted, exchange
                    # receipt on A's books. Round 011's fix: sole-ness is a
                    # FACT, not a declaration — a non-sole treaty whose
                    # provider was the ONLY servant that ever stamped this
                    # chain is effectively sole, and a declared non-sole
                    # basis with a real second servant stays standing
                    if b_rt.why.has(t.beneficiary_node) and (
                            t.sole_basis
                            or not self._has_other_servant(t, b_rt)
                    ):
                        b_rt.why.question(
                            t.beneficiary_node, reason, tick=rec.tick,
                            by="society")
                    self._emit_both(t, "broken", rec.tick,
                                    f"{t.provider_node} {rec.to_state.value}")
                    records.append(ExchangeRecord(
                        t.id, "broken", t.provider, t.beneficiary,
                        f"{t.provider_node} {rec.to_state.value}", rec.tick))
                    break

            # beneficiary side: A's own purpose died (or was questioned
            # by another treaty's break — either way the basis is gone)
            if t.status == ACTIVE:
                for rec in transitions.get(t.beneficiary, ()):
                    if rec.node_id == t.beneficiary_node and rec.to_state in died:
                        reason = (f"{t.id} broken: beneficiary purpose "
                                  f"{t.beneficiary}/{t.beneficiary_node} is "
                                  f"{rec.to_state.value} ({rec.reason})")
                        t.status = BROKEN
                        t.broken_at = rec.tick
                        t.broken_reason = reason
                        self._emit_both(t, "broken", rec.tick,
                                        f"{t.beneficiary_node} {rec.to_state.value}")
                        records.append(ExchangeRecord(
                            t.id, "broken", t.provider, t.beneficiary,
                            f"{t.beneficiary_node} {rec.to_state.value}", rec.tick))
                        break

            # archival is not a necrology transition — check directly
            if t.status == ACTIVE:
                if t.provider_node in p_rt.why.archived_ids():
                    reason = (f"{t.id} broken: provider purpose "
                              f"{t.provider_node} archived to cold storage")
                    t.status, t.broken_at, t.broken_reason = BROKEN, t_now, reason
                    if b_rt.why.has(t.beneficiary_node) and (
                            t.sole_basis
                            or not self._has_other_servant(t, b_rt)
                    ):
                        b_rt.why.question(t.beneficiary_node, reason,
                                          tick=t_now, by="society")
                    self._emit_both(t, "broken", t_now, "provider archived")
                    records.append(ExchangeRecord(
                        t.id, "broken", t.provider, t.beneficiary,
                        "provider archived", t_now))
                elif t.beneficiary_node in b_rt.why.archived_ids():
                    reason = (f"{t.id} broken: beneficiary purpose "
                              f"{t.beneficiary_node} archived to cold storage")
                    t.status, t.broken_at, t.broken_reason = BROKEN, t_now, reason
                    self._emit_both(t, "broken", t_now, "beneficiary archived")
                    records.append(ExchangeRecord(
                        t.id, "broken", t.provider, t.beneficiary,
                        "beneficiary archived", t_now))

            # live endpoint sweep: state changes that happened DURING
            # this exchange (a question() another treaty's break just
            # wrote) or between exchanges (a manual driver that never
            # called us). The frozen slices above carry the receipts;
            # this sweep guarantees the invariant — no treaty walks
            # out of an exchange active with a dead endpoint.
            if t.status == ACTIVE:
                for side, rt, node_id in (
                    ("provider", p_rt, t.provider_node),
                    ("beneficiary", b_rt, t.beneficiary_node),
                ):
                    if not rt.why.has(node_id):
                        continue  # archived handled above
                    state = rt.why.node(node_id).state
                    if state not in died:
                        continue
                    last = next((r for r in reversed(rt.why.necrology())
                                 if r.node_id == node_id), None)
                    detail = (last.reason if last else "no record")
                    reason = (f"{t.id} broken: {side} purpose "
                              f"{node_id} is {state.value} ({detail})")
                    t.status, t.broken_at, t.broken_reason = (
                        BROKEN, last.tick if last else t_now, reason)
                    if side == "provider" and b_rt.why.has(t.beneficiary_node) and (
                            t.sole_basis
                            or not self._has_other_servant(t, b_rt)
                    ):
                        b_rt.why.question(
                            t.beneficiary_node, reason,
                            tick=last.tick if last else t_now, by="society")
                    self._emit_both(t, "broken", t.broken_at,
                                    f"{node_id} {state.value}")
                    records.append(ExchangeRecord(
                        t.id, "broken", t.provider, t.beneficiary,
                        f"{node_id} {state.value}", t.broken_at))
                    break

        # -- 2. route service for surviving treaties --
        for t in self._treaties:
            if t.status != ACTIVE:
                continue
            b_rt = self._members[t.beneficiary]
            for (ts, nid, _by) in stamps.get(t.provider, ()):  # frozen slice
                # a stamp on the provider node IS service of the
                # provider purpose — descendants' wins stamp it too
                if nid != t.provider_node:
                    continue
                # stamp the beneficiary's whole chain on A's books,
                # provenance = the treaty (A does not know B's parts)
                b_rt.why.stamp_chain(t.beneficiary_node, ts, by=t.id)
                b_rt.bus.emit(
                    EventKind.EXCHANGE,
                    (t.id, "service", t.provider, t.beneficiary,
                     f"{t.provider_node} @ {ts}"),
                    src="society", ts=ts,
                )
                records.append(ExchangeRecord(
                    t.id, "service", t.provider, t.beneficiary,
                    f"{t.provider_node} @ {ts}", ts))

        # -- 3. advance cursors: consume exactly what was READ, never
        #        what this exchange itself wrote. Treaty-routed stamps
        #        land past the snapshot length, so the next exchange
        #        picks them up and delegation flows one hop per call —
        #        cycle-safe (A->B->A cannot loop within a fixpoint).
        for name in self._members:
            cur = self._cursors[name]
            cur["journal"] += len(stamps[name])
            cur["necrology"] += len(transitions[name])
            if stamps[name]:
                cur["last"] = stamps[name][-1]  # resync anchor
        return records

    # ------------------------------------------------------------------
    # the clock
    # ------------------------------------------------------------------
    def step(self) -> list:
        """One lockstep heartbeat: every member ticks once (join
        order), then one exchange routes what happened. Returns the
        members' TickReports."""
        reports = []
        for rt in self._members.values():
            reports.append(rt.tick())
        self.exchange(tick=self._society_tick())
        return reports

    def run(self, n: int) -> list:
        return [self.step() for _ in range(n)]

    # ------------------------------------------------------------------
    # the federation audit
    # ------------------------------------------------------------------
    def audit(self) -> FederationReceipt:
        """Do these books agree? See FederationAuditor."""
        return FederationAuditor().audit(self)

    # ------------------------------------------------------------------
    # persistence: members save themselves; the society saves its ledger
    # ------------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "name": self.name,
            "next": self._next,
            "treaties": [
                {
                    "id": t.id, "provider": t.provider,
                    "provider_node": t.provider_node,
                    "beneficiary": t.beneficiary,
                    "beneficiary_node": t.beneficiary_node,
                    "statement": t.statement, "tick": t.tick,
                    "sole_basis": t.sole_basis, "status": t.status,
                    "broken_at": t.broken_at, "broken_reason": t.broken_reason,
                }
                for t in self._treaties
            ],
            "cursors": {k: dict(v) for k, v in self._cursors.items()},
        }

    @classmethod
    def from_json(cls, data: dict, members: dict) -> "Society":
        """Rebuild the society. ``members`` maps name -> already-loaded
        Runtime; join them in the SAME order as before saving (join
        order is the lockstep tick order, part of the society's
        determinism)."""
        soc = cls(name=data.get("name", "society"))
        for name, rt in members.items():
            soc.join(rt, name=name)
        soc._next = data.get("next", 0)
        for row in data.get("treaties", []):
            soc._treaties.append(Treaty(
                id=row["id"], provider=row["provider"],
                provider_node=row["provider_node"],
                beneficiary=row["beneficiary"],
                beneficiary_node=row["beneficiary_node"],
                statement=row["statement"], tick=row["tick"],
                sole_basis=row.get("sole_basis", True),
                status=row.get("status", ACTIVE),
                broken_at=row.get("broken_at"),
                broken_reason=row.get("broken_reason", ""),
            ))
        # cursors restored AFTER the ledger: replaying an old society
        # file onto members that have advanced is the user's call, not
        # ours to silently rebase
        saved = data.get("cursors", {})
        for name in soc._cursors:
            if name in saved:
                cur = saved[name]
                if isinstance(cur, dict):
                    soc._cursors[name] = {
                        "journal": cur.get("journal", 0),
                        "necrology": cur.get("necrology", 0),
                        "epoch": cur.get("epoch", 0),
                        "last": tuple(cur["last"]) if cur.get("last") else None,
                    }
                elif isinstance(cur, (list, tuple)) and len(cur) == 2:
                    # legacy v0.3 cursor shape
                    soc._cursors[name] = {
                        "journal": cur[0], "necrology": cur[1],
                        "epoch": 0, "last": None,
                    }
        return soc


class FederationAuditor:
    """Lifts ADR-0008 one level: from 'do these books replay' to
    'do these books AGREE'.

    Checks (all must hold for ``ok``):

    * ``ledger_append_only``   — ids contiguous in order; a record that
      vanished leaves a hole the hash chain cannot hide.
    * ``endpoints_alive_while_active`` — no ACTIVE treaty whose provider
      or beneficiary node is dead/unknown/absent/archived. A missed or
      late propagation is a society bug, not a state.
    * ``service_derivable`` — every treaty-provenance stamp on a
      beneficiary's journal (the node or its chain) matches a real
      stamp on the provider's provider node at the same tick.
      **Forged service is detectable.**
    * ``break_receipts_present`` — every sole-basis treaty broken by
      its provider has the question() record on the beneficiary's
      necrology (the exchange receipt the pinning test demands).
    * ``member_conservation`` — every member's own books still balance
      (the cheap local invariant, re-asserted at the federation level).
    """

    def audit(self, society: Society) -> FederationReceipt:
        members = society.members()
        ledger = society.treaties()
        checks: dict = {}

        # 1. the ledger is append-only and contiguous
        expected_ids = [f"treaty:{i}" for i in range(1, len(ledger) + 1)]
        checks["ledger_append_only"] = (
            [t.id for t in ledger] == expected_ids
            and all(t.status in (ACTIVE, BROKEN, REVOKED) for t in ledger)
        )

        # 2. active treaties have living endpoints on both sides
        endpoints_ok = True
        for t in ledger:
            if t.status != ACTIVE:
                continue
            if t.provider not in members or t.beneficiary not in members:
                endpoints_ok = False
                continue
            p, b = members[t.provider].why, members[t.beneficiary].why
            for tree, nid in ((p, t.provider_node), (b, t.beneficiary_node)):
                if (not tree.has(nid)
                        or tree.node(nid).state is not WhyState.ALIVE
                        or nid in tree.archived_ids()):
                    endpoints_ok = False
        checks["endpoints_alive_while_active"] = endpoints_ok

        # 3. every treaty-provenance stamp is derivable from the
        #    provider's journal: no member may claim unfrozen service
        provider_stamps: dict = {}  # member -> {(tick, node_id)}
        for name, rt in members.items():
            provider_stamps[name] = {
                (ts, nid) for (ts, nid, _by) in rt.why.journal()
            }
        by_treaty = {t.id: t for t in ledger}
        # ADR-0014: stamps older than the relevant compaction are attested
        # by that compaction's pinnable chain_before — check only the
        # still-uncompacted span for cross-organism derivability. The
        # span is bounded by BOTH books' last compactions: a beneficiary
        # stamp at tick T can only be derived if the provider's journal
        # still holds tick T.
        cutoffs = {}
        for name, rt in members.items():
            comps = rt.why.compactions() if hasattr(rt.why, "compactions") else ()
            cutoffs[name] = comps[-1].tick if comps else -1
        service_ok = True
        for name, rt in members.items():
            chains: dict = {}  # treaty id -> set of node ids in its beneficiary chain
            for (ts, nid, by) in rt.why.journal():
                if not by.startswith("treaty:"):
                    continue
                t = by_treaty.get(by)
                if t is not None and ts <= max(
                        cutoffs.get(name, -1), cutoffs.get(t.provider, -1)):
                    continue  # inside a compacted span: rides on the pinned head
                # the stamp must belong to a real treaty naming THIS
                # member as beneficiary — provenance is not free text
                if t is None or t.beneficiary != name:
                    service_ok = False
                    continue
                if t.id not in chains:
                    # walk up from the stamped node, tolerating nodes
                    # that have since gone to cold storage (a broken
                    # treaty's history is still real history)
                    chains[t.id] = _chain_ids(rt.why, t.beneficiary_node)
                if nid not in chains[t.id]:
                    service_ok = False
                    continue
                # the provider must actually have stamped its node at
                # that tick — service cannot be invented on A's books
                if (ts, t.provider_node) not in provider_stamps.get(t.provider, set()):
                    service_ok = False
        checks["service_derivable"] = service_ok

        # 4. provider-side breaks of sole treaties carry their receipt
        receipts_ok = True
        for t in ledger:
            if not (t.status == BROKEN and t.sole_basis
                    and "provider purpose" in t.broken_reason):
                continue
            if t.beneficiary not in members:
                receipts_ok = False
                continue
            necro = members[t.beneficiary].why.necrology()
            if not any(
                r.node_id == t.beneficiary_node
                and r.to_state is WhyState.UNKNOWN
                and t.id in r.reason
                for r in necro
            ):
                receipts_ok = False
        checks["break_receipts_present"] = receipts_ok

        # 5. every member's own conservation still holds
        checks["member_conservation"] = all(
            rt.why.conservation()["invariant_ok"] for rt in members.values()
        )

        ok = all(checks.values())
        return FederationReceipt(
            ok=ok,
            checks=checks,
            chain_head=self.chain(ledger),
            treaty_records=len(ledger),
            members=len(members),
            note="" if ok else "the society's books disagree; "
                 "see the failed checks for the direction",
        )

    def chain(self, ledger) -> str:
        """Hash chain over the treaty ledger: pin the head, detect any
        edit of society history offline — a removed or rewritten treaty
        breaks it."""
        h = hashlib.sha256(b"society-genesis")
        for t in ledger:
            h.update(repr(t.row()).encode("utf-8"))
            h.update(b"\x1f")
        return h.hexdigest()
