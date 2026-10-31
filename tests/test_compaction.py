"""Journal compaction: the replay basis without the ballast (ADR-0014).

The soak measured the price of "never deleted": 60k journal entries at
10k ticks, verify O(journal), throughput 6.4k -> 2.3k ticks/s. These
tests pin the compaction that pays that price back honestly:

- replay equivalence is EXACT (the compacted basis replays to the same
  tree, bit for bit — live digest == replay digest);
- what is kept is the last stamp per (node, ALIVE window, PROVENANCE):
  enough for the replay AND for the society's effective-sole check
  (each servant's evidence survives inside the window);
- every compaction is receipted (counts balance, dropped digest, chain
  before/after) and the receipts are covered by the auditor's chain;
- service derivability survives compaction (the check spans only the
  still-uncompacted span, bounded by BOTH books' cutoffs);
- nothing else changes: determinism, persistence, tamper detection.
"""
import pytest

from cognitive_ecology import (
    AttentionBid, ColdStorage, ConservationAuditor, Outcome, Runtime,
    Society, WhyState, WhyTree,
)
from cognitive_ecology.compaction import JournalCompactor


class _Worker:
    def __init__(self, cid, why_node, tension):
        self.id, self.why_node = cid, why_node
        self._t = tension

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label=f"{self.id}:work",
            urgency=max(0.3, ctx.tensions.level(self._t)),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0)

    def act(self, ctx, label):
        return Outcome(True, "ok")


def _rt(horizon=None, ticks=300):
    rt = Runtime(seed=5, top_k=2, idle_window=999,
                 attestation_horizon=horizon)
    rt.tensions.add("energy", growth=0.05)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage", parent="why:root", node_id="why:a")
    rt.declare_why("map", parent="why:root", node_id="why:b")
    rt.register(_Worker("w1", "why:a", "energy"))
    rt.register(_Worker("w2", "why:b", "energy"))
    rt.run(ticks)
    return rt


# ---------------------------------------------------------------------------
# replay equivalence — the core guarantee
# ---------------------------------------------------------------------------

def test_compacted_basis_replays_bit_for_bit():
    rt = _rt(ticks=300)
    before = ConservationAuditor().verify(rt.why)
    assert before.ok
    n_before = len(rt.why.journal())
    receipt = JournalCompactor(rt.why).compact()
    assert receipt is not None and receipt.entries_dropped > 0
    assert receipt.entries_before == n_before
    after = ConservationAuditor().verify(rt.why)
    assert after.ok
    # EXACT equivalence: same live tree, from a much smaller basis
    assert after.live_digest == before.live_digest
    assert len(rt.why.journal()) < n_before // 10  # an order smaller
    print(f"journal: {n_before} -> {len(rt.why.journal())}")


def test_repeated_compaction_is_stable():
    rt = _rt(ticks=200)
    JournalCompactor(rt.why).compact()
    d1 = ConservationAuditor().verify(rt.why).live_digest
    r2 = JournalCompactor(rt.why).compact()  # nothing new to drop
    assert r2 is None
    assert ConservationAuditor().verify(rt.why).live_digest == d1
    rt.run(50)  # new stamps accumulate on the compacted journal
    receipt = JournalCompactor(rt.why).compact()
    assert receipt is not None
    assert ConservationAuditor().verify(rt.why).ok


def test_windows_preserve_last_stamp_per_provenance():
    """Two servants stamp the same node; compaction keeps BOTH of their
    last stamps (the society's effective-sole check depends on it)."""
    t = WhyTree(attestation_horizon=None)
    t.declare("root", node_id="R", tick=0)
    t.declare("shared", parent="R", node_id="S", tick=0)
    for tick in range(1, 50):
        t.stamp_chain("S", tick, by="servant-1")
        t.stamp_chain("S", tick, by="servant-2")
    JournalCompactor(t).compact()
    provs = {by for (_ts, nid, by) in t.journal() if nid == "S"}
    assert provs == {"servant-1", "servant-2"}  # both servants' evidence
    assert ConservationAuditor().verify(t).ok


def test_stamps_across_kill_and_revive_windows():
    """A node killed and revived has two ALIVE windows; the last stamp
    of EACH window is kept (the replay needs both)."""
    t = WhyTree(attestation_horizon=None)
    t.declare("root", node_id="R", tick=0)
    t.declare("purpose", parent="R", node_id="P", tick=0)
    for tick in range(1, 20):
        t.stamp_chain("P", tick, by="w")
    t.kill("P", "done", tick=20)
    t.resurrect("P", "back with evidence", tick=25)
    for tick in range(26, 40):
        t.stamp_chain("P", tick, by="w")
    receipt = JournalCompactor(t).compact()
    assert receipt is not None
    stamps_on_p = [ts for (ts, nid, _by) in t.journal() if nid == "P"]
    assert 19 in stamps_on_p and 39 in stamps_on_p  # each window's last
    assert ConservationAuditor().verify(t).ok


# ---------------------------------------------------------------------------
# receipts and tamper detection
# ---------------------------------------------------------------------------

def test_compaction_receipts_balance_and_chain():
    rt = _rt(ticks=150)
    receipt = JournalCompactor(rt.why).compact()
    assert receipt.entries_before == receipt.entries_kept + receipt.entries_dropped
    assert receipt.chain_before != receipt.chain_after
    # the receipts are covered by the auditor's chain: editing one breaks it
    head = ConservationAuditor().chain(
        rt.why.necrology(), rt.why.journal(), rt.why.compactions())
    rt.why._compactions[0].entries_dropped += 1  # lie about what was dropped
    head2 = ConservationAuditor().chain(
        rt.why.necrology(), rt.why.journal(), rt.why.compactions())
    assert head != head2
    # and the accounting check catches the unbalanced receipt
    assert not ConservationAuditor().verify(rt.why).checks.get(
        "compaction_accounting", True)


def test_tamper_after_compaction_is_caught():
    rt = _rt(ticks=200)
    JournalCompactor(rt.why).compact()
    receipt = ConservationAuditor().verify(rt.why)
    assert receipt.ok
    # edit a surviving stamp off the books' expectations
    rt.why.node("why:a").last_beat = 999
    assert not ConservationAuditor().verify(rt.why).ok


def test_compaction_persistence_roundtrip():
    rt = _rt(ticks=200)
    JournalCompactor(rt.why).compact()
    loaded = WhyTree.from_json(rt.why.to_json())
    assert len(loaded.compactions()) == 1
    assert loaded.compactions()[0].row() == rt.why.compactions()[0].row()
    assert ConservationAuditor().verify(loaded).ok


# ---------------------------------------------------------------------------
# the society composes: effective-sole + service derivability survive
# ---------------------------------------------------------------------------

def test_effective_sole_check_survives_compaction():
    """Round 011's shield-treaty defense reads the journal for 'did
    anything else ever stamp this node'. Compaction keeps each
    servant's last stamp in the window, so the check still fires —
    and still does NOT fire when a real second servant existed."""
    from tests.test_society import _beneficiary, _provider

    a, b = _beneficiary(), _provider()
    soc = Society(name="compacted")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty("B", "why:serve", "A", "why:index",
                         "delegation", tick=0)
    soc.run(30)
    JournalCompactor(a.why).compact()  # drop the redundant routed stamps
    b.why.kill("why:serve", "closed", tick=31)
    soc.step()
    # A's node is questioned: no other servant's stamp survived in-window
    assert a.why.node("why:index").state is WhyState.UNKNOWN
    assert soc.audit().ok


def test_service_derivable_spans_only_uncompacted_history():
    """After BOTH books compact, the federation auditor checks service
    derivability only for stamps after the latest relevant compaction —
    older claims ride on the pinnable chain_before receipts."""
    from tests.test_society import _beneficiary, _provider

    a, b = _beneficiary(), _provider()
    soc = Society(name="compacted-society")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty("B", "why:serve", "A", "why:index",
                         "delegation", tick=0)
    soc.run(40)
    JournalCompactor(a.why).compact()
    JournalCompactor(b.why).compact()
    soc.run(10)  # fresh, still-uncompacted service flows
    receipt = soc.audit()
    assert receipt.ok, receipt.summary()
    # both organisms' own receipts hold on the compacted bases
    assert ConservationAuditor().verify(a.why).ok
    assert ConservationAuditor().verify(b.why).ok


# ---------------------------------------------------------------------------
# the performance receipt
# ---------------------------------------------------------------------------

def test_verify_cost_stays_bounded_under_periodic_compaction():
    """10k ticks with compaction every 1k: the journal stays small and
    verification stays fast — the O(journal) price stops growing."""
    import time
    rt = _rt(horizon=200, ticks=0)
    times, sizes = [], []
    for epoch in range(10):
        rt.run(1000)
        r = JournalCompactor(rt.why).compact()
        sizes.append(len(rt.why.journal()))
        t0 = time.monotonic()
        ok = ConservationAuditor().verify(rt.why).ok
        times.append(time.monotonic() - t0)
        assert ok
    # the journal is BOUNDED (not 10k-entries-growing) and verify stays
    # in the same order of magnitude across epochs
    assert max(sizes) < 500, sizes
    assert max(times) < 0.5, times
    print(f"journal sizes across 10 epochs: {sizes}")
    print(f"verify times (s): {[round(t, 3) for t in times]}")


# ---------------------------------------------------------------------------
# round 016: the society-soak bug — compaction vs exchange cursors
# ---------------------------------------------------------------------------

def test_exchange_survives_journal_compaction_without_a_gap():
    """Found by the society soak: compacting a provider's journal left
    the exchange's positional cursor pointing past the end — every
    slice came back empty until the journal REGREW past the cursor (a
    ~500-tick silent service gap in the soak; the beneficiary starved
    and lapsed). The fix: epoch-aware resync (locate the last consumed
    entry in the compacted journal) + monotonic heartbeats (a re-routed
    old stamp is a no-op, so the resync cannot rewind freshness)."""
    from cognitive_ecology import Society

    class S:
        def __init__(s, cid, wn):
            s.id, s.why_node = cid, wn

        def bid(s, ctx):
            yield AttentionBid(
                src=s.id, label=f"{s.id}:serve", urgency=0.8,
                justification=ctx.why.justification(s.why_node),
                opportunity=1.0, novelty=1.0, expected_value=1.0)

        def act(s, ctx, label):
            return Outcome(True, "ok")

    a = Runtime(seed=1, idle_window=999, attestation_horizon=100)
    a.declare_why("root", node_id="why:root")
    a.declare_why("index", parent="why:root", node_id="why:index")
    b = Runtime(seed=2, idle_window=999)
    b.declare_why("root", node_id="why:root")
    b.declare_why("serve", parent="why:root", node_id="why:serve")
    b.register(S("B.s", "why:serve"))
    soc = Society()
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty("B", "why:serve", "A", "why:index", "d", tick=0)
    soc.run(20)
    assert a.why.node("why:index").last_beat == 20

    JournalCompactor(b.why).compact()  # journal shrinks under the cursor
    assert len(b.why.journal()) < 20

    soc.run(20)  # routing must continue WITHOUT a gap
    assert a.why.node("why:index").last_beat == 40
    assert a.why.justification("why:index") == 1.0
    assert soc.audit().ok
    assert ConservationAuditor().verify(a.why).ok


def test_stale_stamps_never_rewind_freshness():
    t = WhyTree(attestation_horizon=100)
    t.declare("root", node_id="R", tick=0)
    t.declare("kid", parent="R", node_id="K", tick=0)
    t.stamp_chain("K", 50, by="now")
    assert t.node("K").last_beat == 50
    took = t.stamp_chain("K", 20, by="late-routed-old-stamp")
    assert took == 2  # accepted...
    assert t.node("K").last_beat == 50  # ...but freshness never rewound
    assert t.node("K").last_attested_by == "now"  # nor did provenance
    # and the stale stamp did not pollute the journal
    assert all(ts >= 50 for (ts, _nid, _by) in t.journal())
    assert ConservationAuditor().verify(t).ok
