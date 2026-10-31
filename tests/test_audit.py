"""The conservation auditor: necrology replay equivalence (ADR-0008).

The claim under test: GENESIS + NECROLOGY + JOURNAL replay to exactly the
living tree. Every tamper vector — flipped state, edited statement,
removed/reordered/forged record, forged stamp — must be caught with the
specific check named. (Proposal adopted from live ideation round 004b.)
"""
import tempfile

from cognitive_ecology import Runtime, WhyState, WhyTree
from cognitive_ecology.audit import ConservationAuditor
from cognitive_ecology.why import NecroRecord


def _rich_tree() -> WhyTree:
    """A tree that has been through everything: birth, service, kill,
    cascade, lapse, revival, parole, and a save/load cycle."""
    t = WhyTree(attestation_horizon=90)
    t.declare("stay alive", node_id="why:root", tick=0)
    t.declare("forage", parent="why:root", node_id="why:forage", tick=0)
    t.declare("map", parent="why:forage", node_id="why:map", tick=0)
    t.declare("draft", node_id="why:draft", state=WhyState.ABSENT, tick=0)
    t.stamp_chain("why:map", tick=5, by="forager")
    t.stamp_chain("why:map", tick=10, by="forager")
    t.kill("why:forage", reason="superseded", tick=12)      # map -> UNKNOWN
    t.resurrect("why:forage", "new evidence", tick=14)      # cascade, parole
    t.stamp_chain("why:map", tick=20, by="forager")         # service: parole ends
    t.park("why:root", tick=25)                             # -> ABSENT
    t.activate("why:root", tick=30)                         # -> ALIVE, fresh beat
    t.reap(tick=200)                                        # nothing served since 30
    return t


def test_replay_equivalence_on_a_rich_tree():
    t = _rich_tree()
    r = ConservationAuditor().verify(t)
    assert r.ok, r.summary()
    assert r.live_digest == r.replay_digest
    assert r.genesis_records == 4 and r.transition_records == len(t.necrology())
    assert r.journal_records == len(t.journal())


def test_replay_equivalence_through_save_load():
    rt = Runtime(seed=3, attestation_horizon=40)
    rt.tensions.add("energy", growth=0.03)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage", parent="why:root", node_id="why:forage")
    rt.declare_why("legacy", parent="why:root", node_id="why:legacy")

    class _Worker:
        id = "worker"
        why_node = "why:forage"

        def bid(self, ctx):
            from cognitive_ecology import AttentionBid
            yield AttentionBid(
                src=self.id, label="worker:work", urgency=0.8,
                justification=ctx.why.justification(self.why_node),
                opportunity=1.0, novelty=1.0, expected_value=1.0)

        def act(self, ctx, label):
            from cognitive_ecology import Outcome
            return Outcome(True, "worked")

    rt.register(_Worker())
    rt.run(120)  # legacy lapses somewhere in here; worker keeps foraging
    with tempfile.TemporaryDirectory() as d:
        rt.save(d)
        rt2 = Runtime.load(d, attach=lambda r: r.register(_Worker()))
    r = ConservationAuditor().verify(rt2.why)
    assert r.ok, r.summary()
    assert r.journal_records > 100  # a real service history replayed


# ---------------------------------------------------------------------------
# tamper vectors — each must be caught, with the check named
# ---------------------------------------------------------------------------

def _tamper(tree, mutate):
    mutate(tree)  # off-the-books mutation
    r = ConservationAuditor().verify(tree)
    return r


def test_tamper_flipped_state_is_caught():
    t = _rich_tree()
    t.node("why:draft").state = WhyState.ALIVE  # never went through the log
    r = ConservationAuditor().verify(t)
    assert not r.ok
    assert r.checks["state_equivalence"] is False


def test_tamper_edited_statement_is_caught():
    t = _rich_tree()
    t.node("why:map").statement = "do something else entirely"
    r = ConservationAuditor().verify(t)
    assert not r.ok and r.checks["state_equivalence"] is False


def test_tamper_removed_record_is_caught():
    t = _rich_tree()
    t._necrology.pop(2)  # a cascade record vanishes from history
    r = ConservationAuditor().verify(t)
    assert not r.ok
    assert not r.checks.get("log_internally_consistent", True) or \
        not r.checks["state_equivalence"]


def test_tamper_reordered_records_are_caught():
    t = _rich_tree()
    recs = list(t._necrology)
    # cross-tick reorder: a tick-200 lapse now precedes the tick-12 kill.
    # (same-tick reorders of independent records are outcome-equivalent
    # and correctly absorbed by the chronological replay)
    recs[0], recs[-1] = recs[-1], recs[0]
    t._necrology[:] = recs
    r = ConservationAuditor().verify(t)
    assert not r.ok
    assert r.checks.get("log_order") is False or \
        r.checks.get("transition_validity") is False


def test_tamper_forged_record_is_caught():
    t = _rich_tree()
    t._necrology.append(
        NecroRecord(tick=999, node_id="why:map", statement="map",
                    from_state=WhyState.UNKNOWN, to_state=WhyState.ALIVE,
                    reason="forged revival"))
    r = ConservationAuditor().verify(t)
    assert not r.ok
    # the forged revive applies cleanly in replay (its from_state matches
    # the lapsed node) -- what catches it is that live != replayed
    assert r.checks["state_equivalence"] is False


def test_tamper_forged_stamp_is_caught():
    t = _rich_tree()
    # a stamp for a node whose replayed state is not ALIVE at that point
    t._journal.append((200, "why:draft", "liar"))
    r = ConservationAuditor().verify(t)
    assert not r.ok
    assert r.checks.get("stamp_validity") is False


def test_tamper_dropped_stamp_is_caught():
    t = _rich_tree()
    # drop the LAST stamp for why:map (tick 20): parole stays set and
    # last_beat/provenance diverge in replay
    t._journal[:] = [j for j in t._journal if j != (20, "why:map", "forager")]
    r = ConservationAuditor().verify(t)
    assert not r.ok and r.checks["state_equivalence"] is False


def test_chain_head_pins_history():
    t = _rich_tree()
    a = ConservationAuditor()
    head1 = a.chain(t.necrology())
    # any edit of history — even a byte of a reason — breaks the chain
    recs = list(t.necrology())
    recs[0] = NecroRecord(recs[0].tick, recs[0].node_id, recs[0].statement,
                          recs[0].from_state, recs[0].to_state,
                          recs[0].reason + " ")
    t._necrology[:] = recs
    head2 = a.chain(t.necrology())
    assert head1 != head2


def test_legacy_tree_without_genesis_gets_an_honest_no():
    t = WhyTree()
    t.declare("only node", node_id="why:1", tick=0)
    t._genesis.clear()  # simulate a pre-v0.3 tree
    r = ConservationAuditor().verify(t)
    assert not r.ok
    assert r.checks["genesis_present"] is False
    assert "no genesis block" in r.note


def test_replay_survives_a_random_storm():
    """The same storm as the re-attestation suite, verified at the end."""
    import random
    rng = random.Random(11)
    t = WhyTree(attestation_horizon=30)
    t.declare("root", node_id="why:root", tick=0)
    extra = ["why:root"]
    for i in range(40):
        nid = f"why:x{i}"
        t.declare(f"purpose {i}", parent=rng.choice(extra), node_id=nid, tick=0)
        extra.append(nid)
    for tick in range(1, 300):
        t.now = tick
        for v in rng.sample(list(t.nodes()), k=min(3, len(t.nodes()))):
            r = rng.random()
            if r < 0.25 and v.state is WhyState.ALIVE:
                t.stamp_chain(v.id, tick, by="storm")
            elif r < 0.4 and v.state is WhyState.ALIVE:
                t.kill(v.id, reason="storm", tick=tick)
            elif r < 0.5 and v.state is WhyState.UNKNOWN:
                t.revive(v.id, reason="storm re-justify", tick=tick)
        t.reap(tick)
    r = ConservationAuditor().verify(t)
    assert r.ok, r.summary()
    assert r.transition_records > 100 and r.journal_records > 100
