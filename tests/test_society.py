"""Society-basis: WHY federation across organisms (ADR-0011).

Pins the semantics the live ideation round 009 ranked #1 of the v0.4
frontier. The sharp one, verbatim from the adoption note:

    A's purpose served only by B lapses when B dies, with an exchange
    receipt on A's books.

Plus everything that makes that honest: service routed through
treaties keeps freshness on the beneficiary's own books; neglect
strangulates through the SOFT path (A's own reaper, no event from B);
forged service is detectable; missed propagations are detectable; the
treaty ledger is append-only; and one-hop delegation chains work.
"""
import pytest

from cognitive_ecology import (
    ACTIVE, BROKEN, REVOKED, AttentionBid, ConservationAuditor, EventKind,
    Outcome, Runtime, Society, WhyState,
)


# ---------------------------------------------------------------------------
# fixtures: two organisms, one society
# ---------------------------------------------------------------------------

class _Greedy:
    """A component that always bids and always acts."""

    def __init__(self, cid, why_node, tension, switchable=False):
        self.id = cid
        self.why_node = why_node
        self._tension = tension
        self._switchable = switchable
        self.on = True

    def bid(self, ctx):
        if self._switchable and not self.on:
            return
        yield AttentionBid(
            src=self.id, label=f"{self.id}:work",
            urgency=max(ctx.tensions.level(self._tension), 0.5),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        ctx.tensions.relieve(self._tension, 0.2)
        return Outcome(True, "did the thing")


def _provider(name="B", seed=11):
    """B: an archive that exists to be leaned on. Serves why:serve every
    tick — until the test switches the server off (soft-path tests)."""
    rt = Runtime(seed=seed, idle_window=999)
    rt.tensions.add("energy", growth=0.03)
    rt.declare_why("the archive exists", node_id="why:root")
    rt.declare_why("serve the archive", parent="why:root", node_id="why:serve")
    rt.register(_Greedy(f"{name}.server", "why:serve", "energy", switchable=True))
    return rt


def _beneficiary(name="A", seed=5, horizon=40):
    """A: leans on B for its shared-index purpose (no local component
    under why:index — the treaty is the sole basis by construction)."""
    rt = Runtime(seed=seed, idle_window=999, attestation_horizon=horizon)
    rt.tensions.add("focus", growth=0.03)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("keep the shared index fresh", parent="why:root",
                   node_id="why:index")
    rt.declare_why("mind my own work", parent="why:root", node_id="why:local")
    rt.register(_Greedy(f"{name}.worker", "why:local", "focus"))
    return rt


def _society(a, b, tick=0, sole_basis=True):
    soc = Society(name="test-society")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty(
        provider="B", provider_node="why:serve",
        beneficiary="A", beneficiary_node="why:index",
        statement="A's index freshness is served by B's archive",
        tick=tick, sole_basis=sole_basis,
    )
    return soc


def _exchange_events(rt, what=None):
    return [
        e for e in rt.bus.log()
        if e.kind is EventKind.EXCHANGE and (what is None or e.payload[1] == what)
    ]


# ---------------------------------------------------------------------------
# the question() transition (external doubt)
# ---------------------------------------------------------------------------

def test_question_records_and_replays():
    rt = _beneficiary()
    rt.why.question("why:index", "treaty:1 broken: partner died", tick=7)
    node = rt.why.node("why:index")
    assert node.state is WhyState.UNKNOWN
    rec = rt.why.necrology()[-1]
    assert (rec.from_state, rec.to_state) == (WhyState.ALIVE, WhyState.UNKNOWN)
    assert "treaty:1" in rec.reason
    # no cascade: descendants stay formally alive, verdict-blocked
    rt.declare_why("index page 3", parent="why:index", node_id="why:page3")
    rt.why.question("why:index", "again", tick=8)  # no-op on UNKNOWN
    assert len(rt.why.necrology()) == 1
    # the conservation auditor replays the question like any transition
    assert ConservationAuditor().verify(rt.why).ok


def test_question_requires_living_node():
    rt = _beneficiary()
    rt.why.kill("why:index", "done", tick=3)
    rt.why.question("why:index", "late doubt", tick=4)  # DEAD: silent no-op
    assert rt.why.node("why:index").state is WhyState.DEAD
    assert len(rt.why.necrology()) == 1


# ---------------------------------------------------------------------------
# service routing: the treaty keeps A's books fresh
# ---------------------------------------------------------------------------

def test_service_flows_to_beneficiary_books():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(30)
    node = a.why.node("why:index")
    # A never ran anything under why:index — the treaty served it
    assert node.last_attested_by == "treaty:1"
    assert node.last_beat == 30  # routed every tick
    assert a.why.justification("why:index") == 1.0  # fresh under a horizon
    # the receipt: EXCHANGE events on A's books
    services = _exchange_events(a, what="service")
    assert len(services) == 30
    assert services[0].payload[:2] == ("treaty:1", "service")
    # establishment was noticed by BOTH parties
    assert len(_exchange_events(a, what="established")) == 1
    assert len(_exchange_events(b, what="established")) == 1
    assert soc.audit().ok


def test_exchange_is_idempotent_cursors_consume_once():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(5)
    stamps_before = len(a.why.journal())
    soc.exchange()  # nothing new happened: routes nothing
    assert len(a.why.journal()) == stamps_before
    assert soc.exchange() == []


# ---------------------------------------------------------------------------
# THE PINNING TEST: hard propagation when the provider dies
# ---------------------------------------------------------------------------

def test_sole_basis_lapses_when_provider_dies():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(25)
    assert a.why.node("why:index").state is WhyState.ALIVE

    b.why.kill("why:serve", reason="archive closed", tick=26)
    soc.step()  # the exchange notices and propagates

    node = a.why.node("why:index")
    assert node.state is WhyState.UNKNOWN  # questioned, NEVER deleted
    # the exchange receipt on A's books: the question record names the treaty
    recs = [r for r in a.why.necrology() if r.node_id == "why:index"]
    assert any("treaty:1" in r.reason and "archive closed" in r.reason
               for r in recs)
    # ...and the EXCHANGE event
    assert len(_exchange_events(a, what="broken")) == 1
    # the treaty is broken, and broken treaties are never deleted
    t = soc.treaties()[0]
    assert t.status == BROKEN and "archive closed" in t.broken_reason
    # A's own books still balance, and the question replays
    assert a.why.conservation()["invariant_ok"]
    assert ConservationAuditor().verify(a.why).ok
    # the society's books agree
    assert soc.audit().ok


def test_provider_lapse_also_propagates_hard():
    """B's own economics strangle the provider purpose -> same hard break."""
    b = _provider()
    b.why.attestation_horizon = 10  # B is stingy with itself
    a = _beneficiary()
    soc = _society(a, b)
    b.component("B.server").on = False  # B stops serving (stays ALIVE in B)
    # B's reaper (t%25) lapses why:serve once it exceeds B's horizon
    soc.run(30)
    assert b.why.node("why:serve").state is WhyState.UNKNOWN
    assert a.why.node("why:index").state is WhyState.UNKNOWN
    # the receipt names the treaty — doubt came from outside A
    assert any("treaty:1" in r.reason for r in a.why.necrology()
               if r.node_id == "why:index")
    assert soc.treaties()[0].status == BROKEN
    assert soc.audit().ok


# ---------------------------------------------------------------------------
# the soft path: neglect strangulates on A's own books
# ---------------------------------------------------------------------------

def test_neglect_strangulates_via_own_reaper():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(10)
    b.component("B.server").on = False  # B goes quiet; why:serve stays ALIVE
    # A's horizon is 40, last routed stamp at tick 10; A's reaper runs on
    # multiples of 25: at t=50 age is exactly 40 (not >), so the lapse
    # lands at the t=75 sweep
    soc.run(70)
    node = a.why.node("why:index")
    assert node.state is WhyState.UNKNOWN
    # the receipt is A's OWN lapse record — no treaty event claimed a death
    rec = [r for r in a.why.necrology() if r.node_id == "why:index"][-1]
    assert rec.reason.startswith("lapsed: unattested")
    assert rec.from_state is WhyState.ALIVE
    # the lapse itself breaks the treaty (beneficiary side)
    assert soc.treaties()[0].status == BROKEN
    assert "beneficiary purpose" in soc.treaties()[0].broken_reason
    assert soc.audit().ok


def test_dual_basis_survives_provider_death():
    """Non-sole treaty: B's death breaks the treaty, not A's purpose."""
    a, b = _beneficiary(), _provider()
    # A also serves the index locally — the treaty is a redundancy, not a sole basis
    a.register(_Greedy("A.indexer", "why:index", "focus"))
    soc = _society(a, b, sole_basis=False)
    soc.run(10)
    b.why.kill("why:serve", reason="archive closed", tick=11)
    soc.run(5)
    assert soc.treaties()[0].status == BROKEN
    assert a.why.node("why:index").state is WhyState.ALIVE  # stood on local service
    assert a.why.justification("why:index") > 0.5
    assert soc.audit().ok


# ---------------------------------------------------------------------------
# establishment honesty
# ---------------------------------------------------------------------------

def test_establish_requires_living_endpoints():
    a, b = _beneficiary(), _provider()
    soc = Society()
    soc.join(a, name="A")
    soc.join(b, name="B")
    b.why.kill("why:serve", "closed", tick=1)
    with pytest.raises(ValueError, match="living provider"):
        soc.establish_treaty("B", "why:serve", "A", "why:index", "x", tick=1)
    a.why.kill("why:index", "dropped", tick=1)
    a.why.question("why:local", "doubt", tick=1)
    with pytest.raises(ValueError):
        soc.establish_treaty("B", "why:root", "A", "why:index", "x", tick=1)
    with pytest.raises(KeyError):
        soc.establish_treaty("C", "why:serve", "A", "why:local", "x", tick=1)


def test_sole_exclusivity_cannot_be_said_twice():
    a, b = _beneficiary(), _provider()
    soc = Society()
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty("B", "why:serve", "A", "why:index", "first", tick=0)
    with pytest.raises(ValueError, match="cannot be said twice"):
        soc.establish_treaty("B", "why:root", "A", "why:index", "second", tick=0)
    # the sole basis breaks -> A's node is questioned -> a NEW sole treaty
    # requires A's revival ceremony first (no UNKNOWN-washing treaties)
    b.why.kill("why:serve", "closed", tick=1)
    soc.exchange()
    assert a.why.node("why:index").state is WhyState.UNKNOWN
    with pytest.raises(ValueError, match="living beneficiary"):
        soc.establish_treaty("B", "why:root", "A", "why:index", "again", tick=2)
    a.why.revive("why:index", "A re-justifies on a new basis", tick=2)
    soc.establish_treaty("B", "why:root", "A", "why:index", "again", tick=2)
    assert soc.treaties()[1].status == ACTIVE


def test_beneficiary_death_breaks_treaty():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(5)
    a.why.kill("why:index", "we stopped caring", tick=6)
    soc.step()
    assert soc.treaties()[0].status == BROKEN
    assert "beneficiary purpose" in soc.treaties()[0].broken_reason
    assert soc.audit().ok


def test_revocation_leaves_purpose_standing():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(5)
    soc.revoke_treaty("treaty:1", "A stands on its own now", tick=6)
    assert soc.treaties()[0].status == REVOKED
    assert a.why.node("why:index").state is WhyState.ALIVE  # not questioned
    # ...but with no service and a horizon, A's own economics decide
    soc.run(60)
    assert a.why.node("why:index").state is WhyState.UNKNOWN
    assert soc.audit().ok


# ---------------------------------------------------------------------------
# the federation auditor catches lies
# ---------------------------------------------------------------------------

def test_forged_service_is_caught():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(5)
    # A claims service B never gave: a treaty-provenance stamp at a tick
    # where B's provider node was never stamped
    a.why.stamp_chain("why:index", 999, by="treaty:1")
    receipt = soc.audit()
    assert not receipt.ok
    assert receipt.checks["service_derivable"] is False
    assert "service_derivable" in receipt.summary()


def test_missed_propagation_is_caught():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(5)
    b.why.kill("why:serve", "closed", tick=6)
    # NO exchange runs — the propagation was missed
    receipt = soc.audit()
    assert not receipt.ok
    assert receipt.checks["endpoints_alive_while_active"] is False


def test_ledger_tamper_breaks_the_chain():
    a, b = _beneficiary(), _provider()
    soc = Society()
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty("B", "why:serve", "A", "why:index", "first", tick=0)
    soc.establish_treaty("B", "why:root", "A", "why:local", "second",
                         tick=0, sole_basis=False)
    soc.run(3)
    head = soc.audit().chain_head
    # rewrite one word of society history
    soc.treaties()[0].statement = "A's index freshness is served by NOBODY"
    assert soc.audit().chain_head != head
    # ledger integrity is its own check: a removed treaty leaves a hole
    # in the contiguous id sequence the append-only check demands
    soc._treaties.pop(0)  # remove the FIRST: treaty:2 remains, ids not contiguous
    assert not soc.audit().checks["ledger_append_only"]


def test_member_books_must_balance():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(3)
    a.why._nodes.pop("why:index")  # off the books deletion
    receipt = soc.audit()
    assert not receipt.ok


# ---------------------------------------------------------------------------
# delegation chains: one hop per exchange, cycle-safe
# ---------------------------------------------------------------------------

def test_delegation_chain_one_hop_per_exchange():
    """C serves B, B's served purpose serves A: influence propagates
    transitively, one exchange per hop, and every stamp stays derivable."""
    c = _provider(name="C", seed=21)
    b = _beneficiary(name="B", seed=11, horizon=None)
    a = _beneficiary(name="A", seed=5)
    soc = Society(name="chain")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.join(c, name="C")
    soc.establish_treaty("C", "why:serve", "B", "why:index",
                         "B leans on C", tick=0)           # treaty:1
    soc.establish_treaty("B", "why:index", "A", "why:index",
                         "A leans on B's delegated basis", tick=0)  # treaty:2
    soc.run(4)
    # B was served by C...
    assert b.why.node("why:index").last_attested_by == "treaty:1"
    # ...and A received B's treaty-served stamps one hop later
    node = a.why.node("why:index")
    assert node.last_attested_by == "treaty:2"
    assert node.last_beat >= 3  # service from tick 3 arrived by step 4
    # the whole chain is mutually derivable — no member invented service
    assert soc.audit().ok


# ---------------------------------------------------------------------------
# persistence and lockstep determinism
# ---------------------------------------------------------------------------

def test_society_persistence_roundtrip():
    a, b = _beneficiary(), _provider()
    soc = _society(a, b)
    soc.run(7)
    data = soc.to_json()
    soc2 = Society.from_json(data, members={"A": a, "B": b})
    assert [t.id for t in soc2.treaties()] == ["treaty:1"]
    assert soc2.treaties()[0].status == ACTIVE
    # cursors survived: an immediate exchange routes nothing new
    stamps_before = len(a.why.journal())
    soc2.exchange()
    assert len(a.why.journal()) == stamps_before
    assert soc2.audit().ok


def test_lockstep_determinism_bit_for_bit():
    def build():
        a, b = _beneficiary(), _provider()
        soc = _society(a, b)
        soc.run(50)
        return soc

    s1, s2 = build(), build()
    assert s1.audit().chain_head == s2.audit().chain_head
    r1, r2 = s1.audit(), s2.audit()
    assert r1.checks == r2.checks
    assert r1.chain_head == r2.chain_head


# ---------------------------------------------------------------------------
# round 011 red-team fixes: sole-ness as fact, doubter provenance
# ---------------------------------------------------------------------------

def test_effective_sole_questioned_despite_non_sole_declaration():
    """Round 011, the shield-treaty hole: declaring non-sole is free,
    so a beneficiary whose ONLY servant died should not escape the hard
    path by checking a box. Sole-ness is derived from the journals."""
    a, b = _beneficiary(), _provider()
    soc = _society(a, b, sole_basis=False)  # the LIE: non-sole, no other servant
    soc.run(10)
    b.why.kill("why:serve", "archive closed", tick=11)
    soc.step()
    # no local component, no second treaty ever stamped why:index ->
    # effectively sole -> questioned anyway
    assert a.why.node("why:index").state is WhyState.UNKNOWN
    assert any("doubted by society" in r.reason for r in a.why.necrology())
    assert soc.audit().ok


def test_dead_weight_second_treaty_is_not_a_servant():
    """The non-sole declaration names a second treaty that never served:
    a dead-weight treaty backs nothing, and the books show it."""
    a, b = _beneficiary(), _provider()
    c = _provider(name="C", seed=31)
    soc = Society(name="shield-test")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.join(c, name="C")
    c.component("C.server").on = False  # C's purpose lives but never serves
    soc.establish_treaty("B", "why:serve", "A", "why:index",
                         "the real servant", tick=0, sole_basis=False)
    soc.establish_treaty("C", "why:serve", "A", "why:index",
                         "the dead-weight shield", tick=0, sole_basis=False)
    soc.run(10)
    b.why.kill("why:serve", "archive closed", tick=11)
    soc.step()
    # the shield treaty never stamped why:index, so the beneficiary was
    # effectively sole on B -> questioned; and the live endpoint sweep
    # breaks the shield in the SAME exchange (no treaty walks out of an
    # exchange active with a dead endpoint)
    assert soc.treaties()[1].status == BROKEN
    assert "beneficiary purpose" in soc.treaties()[1].broken_reason
    assert a.why.node("why:index").state is WhyState.UNKNOWN
    assert soc.audit().ok


def test_real_second_servant_backs_the_declaration():
    """Non-sole with a REAL second servant: the declaration is honest,
    the node stands on the surviving service."""
    a, b = _beneficiary(), _provider()
    c = _provider(name="C", seed=31)
    soc = Society(name="honest-dual")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.join(c, name="C")
    soc.establish_treaty("B", "why:serve", "A", "why:index",
                         "primary servant", tick=0, sole_basis=False)
    soc.establish_treaty("C", "why:serve", "A", "why:index",
                         "secondary servant", tick=0, sole_basis=False)
    soc.run(10)  # both servants actively stamping
    assert a.why.justification("why:index") == 1.0
    b.why.kill("why:serve", "primary closed", tick=11)
    soc.run(3)   # C keeps serving; treaty:1 breaks, no question
    assert soc.treaties()[0].status == BROKEN
    assert a.why.node("why:index").state is WhyState.ALIVE
    assert a.why.node("why:index").last_attested_by == "treaty:2"
    assert soc.audit().ok


def test_question_records_the_doubter():
    rt = _beneficiary()
    rt.why.question("why:index", "external challenge", tick=4, by="federation")
    rec = rt.why.necrology()[-1]
    assert rec.reason.endswith("(doubted by federation)")
    # an unnamed doubter is recorded as such — the reason stands alone
    rt2 = _beneficiary()
    rt2.why.question("why:index", "anonymous doubt", tick=1)
    assert rt2.why.necrology()[-1].reason == "anonymous doubt"
