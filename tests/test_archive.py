"""Honest archival: cold storage that is not deletion (ADR-0010).

OPEN_QUESTIONS #6 asked what would make archival honest. The answer under
test: conservative eligibility, balanced books, biographies that travel,
and restoration as a recorded two-act ceremony.
"""
import tempfile

from cognitive_ecology import ColdStorage, Runtime, WhyState, WhyTree
from cognitive_ecology.audit import ConservationAuditor


def _aged_tree() -> WhyTree:
    """A lineage: root -> old (killed long ago, dead child) -> and a live
    sibling branch that must never be touched."""
    t = WhyTree()
    t.declare("stay alive", node_id="why:root", tick=0)
    t.declare("live work", parent="why:root", node_id="why:live", tick=0)
    t.declare("old mission", parent="why:root", node_id="why:old", tick=0)
    t.declare("old subtask", parent="why:old", node_id="why:oldsub", tick=0)
    t.declare("dead leaf", parent="why:oldsub", node_id="why:oldleaf", tick=0)
    t.stamp_chain("why:oldleaf", tick=10, by="worker")
    t.kill("why:old", reason="mission closed", tick=20)  # cascade below
    t.stamp_chain("why:live", tick=30, by="worker")
    t.now = 2000
    return t


def test_eligibility_is_conservative():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    assert cs.eligible("why:old")           # dead 1980 ticks, no live below
    assert not cs.eligible("why:root")      # ALIVE
    assert not cs.eligible("why:live")      # ALIVE
    # young dead is not eligible
    t2 = WhyTree()
    t2.declare("a", node_id="why:a", tick=0)
    t2.declare("b", parent="why:a", node_id="why:b", tick=0)
    t2.kill("why:b", reason="x", tick=5)
    t2.now = 50
    assert not ColdStorage(t2, min_age=1000).eligible("why:b")


def test_dead_with_live_descendant_is_not_eligible():
    # a contradiction: ALIVE descendant under a DEAD ancestor
    t = _aged_tree()
    t.node("why:oldleaf").state = WhyState.ALIVE  # force the contradiction
    cs = ColdStorage(t, min_age=1000)
    assert not cs.eligible("why:old")  # something living depends on the lineage


def test_sweep_archives_whole_dead_subtree_and_books_balance():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    archived = cs.sweep()
    assert sorted(archived) == ["why:old", "why:oldleaf", "why:oldsub"]
    # hot tree keeps only the living branch
    assert [n.id for n in t.nodes()] == ["why:root", "why:live"]
    # the books balance: hot + archived == ever declared
    c = t.conservation()
    assert c["archived"] == 3 and c["ever_declared"] == 5
    assert c["invariant_ok"]
    # the live branch still works untouched
    assert t.why_should_this_run("why:live")


def test_nothing_is_lost_the_manifest_carries_biographies():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    cs.sweep()
    m = {row["id"]: row for row in cs.manifest()}
    assert m["why:old"]["statement"] == "old mission"
    assert m["why:old"]["parent"] == "why:root"
    assert m["why:oldleaf"]["last_attested_by"] == "worker"
    assert all(r["archived_at"] == 2000 for r in m.values())


def test_auditor_verifies_cold_storage_against_the_replay():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    cs.sweep()
    r = ConservationAuditor().verify(t)
    assert r.ok, r.summary()
    assert r.checks.get("archive_manifest_equivalence") is True


def test_tampered_manifest_is_caught():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    cs.sweep()
    t._archived["why:old"]["statement"] = "rewritten history"
    r = ConservationAuditor().verify(t)
    assert not r.ok
    assert r.checks.get("archive_manifest_equivalence") is False


def test_restoration_is_a_recorded_two_act_ceremony():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    cs.sweep()
    # act one: restore (still DEAD, reason recorded in the necrology)
    cs.restore("why:old", reason="the mission became relevant again", tick=2001)
    assert t.has("why:old")
    assert t.node("why:old").state is WhyState.DEAD
    restores = [r for r in t.necrology() if "restored from cold storage" in r.reason]
    assert len(restores) == 1 and "relevant again" in restores[0].reason
    # the restored subtree hangs together
    assert t.node("why:old").parent == "why:root"
    # act two: resurrection with parole
    t.resurrect("why:old", "new evidence for the old mission", tick=2002)
    assert t.node("why:old").state is WhyState.ALIVE
    assert t.node("why:old").probation is True
    # act one restored the WHOLE cold subtree (transitive)
    assert t.has("why:oldsub") and t.has("why:oldleaf")
    # and the whole ceremony is verifiable
    r = ConservationAuditor().verify(t)
    assert r.ok, r.summary()
    c = t.conservation()
    assert c["archived"] == 0 and c["invariant_ok"]  # the cold came back whole


def test_restore_requires_a_reason():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    cs.sweep()
    try:
        cs.restore("why:old", reason="   ")
        raise AssertionError("empty reason must be rejected")
    except ValueError:
        pass


def test_archival_survives_save_load_and_still_verifies():
    from tests.test_calibration import _bid  # noqa: F401  (import check)
    rt = Runtime(seed=5)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("old", parent="why:root", node_id="why:old")
    rt.why.kill("why:old", reason="closed", tick=1)
    rt.why.now = 5000
    ColdStorage(rt.why, min_age=100).sweep()
    with tempfile.TemporaryDirectory() as d:
        rt.save(d)

        def attach(r):
            pass

        rt2 = Runtime.load(d, attach=attach)
    assert rt2.why.archived_ids() == ("why:old",)
    r = ConservationAuditor().verify(rt2.why)
    assert r.ok, r.summary()


def test_sweep_is_deterministic_and_idempotent():
    t = _aged_tree()
    cs = ColdStorage(t, min_age=1000)
    a = cs.sweep()
    b = cs.sweep()  # nothing left to archive
    assert sorted(a) == ["why:old", "why:oldleaf", "why:oldsub"] and b == []
