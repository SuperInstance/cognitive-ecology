"""The WHY DAG: purposes justified by several parents (ADR-0012).

Pins the semantics the live ideation round 009 ranked #2 of the v0.4
frontier, verbatim from the adoption note:

    purpose C with parents A and B; kill A only; C must survive if B
    remains served, and die only when all parents lapse.

Plus everything that makes best-path honest: no over-cascade (a
surviving parent's lineage shields the child), no under-cascade
(cross-linked topologies reach the fixpoint), justification as the
strongest living path, stamping the whole DAG lineage, contradictions
that require destroyed warrant (not merely doubt), the conservation
auditor replaying a DAG basis, cold storage of DAG subtrees, and
treaties onto multi-parent beneficiaries.
"""
import pytest

from cognitive_ecology import (
    ColdStorage, ConservationAuditor, Runtime, Society, WhyState, WhyTree,
)


def _dag():
    """Two roots, one shared child, one grandchild under the child."""
    t = WhyTree()
    t.declare("root A", node_id="A", tick=0)
    t.declare("root B", node_id="B", tick=0)
    t.declare("the shared purpose", parents=("A", "B"), node_id="C", tick=0)
    t.declare("serves the shared purpose", parent="C", node_id="D", tick=0)
    return t


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def test_parents_fixed_at_declaration_and_acyclic():
    t = _dag()
    assert t.node("C").parents == ("A", "B")
    assert t.node("C").parent == "A"       # primary parent compatibility
    assert t.node("D").parents == ("C",)
    assert {n.id for n in t.roots()} == {"A", "B"}
    with pytest.raises(ValueError, match="not both"):
        t.declare("bad", parent="A", parents=("A", "B"))
    with pytest.raises(KeyError, match="unknown parent"):
        t.declare("bad", parents=("A", "nope"))
    # duplicate parents collapse (dedupe keeps order)
    n = t.declare("dupe", parents=("A", "B", "A"), node_id="E")
    assert n.parents == ("A", "B")


def test_paths_enumerate_all_routes_deterministically():
    t = _dag()
    paths = t.paths("C")
    assert [[n.id for n in p] for p in paths] == [["C", "A"], ["C", "B"]]
    # the tree node inherits BOTH routes through its DAG parent
    assert [[n.id for n in p] for p in t.paths("D")] == [
        ["D", "C", "A"], ["D", "C", "B"]]


# ---------------------------------------------------------------------------
# THE PINNING TEST (round 009, verbatim)
# ---------------------------------------------------------------------------

def test_kill_one_parent_the_shared_purpose_survives():
    t = _dag()
    t.kill("A", "A is done", tick=5)
    # C survives: B's lineage still warrants it — NO over-cascade
    assert t.node("C").state is WhyState.ALIVE
    assert t.node("D").state is WhyState.ALIVE
    assert t.why_should_this_run("C")
    assert t.justification("C") == 1.0        # B's path is fully alive
    # C is not a contradiction: it holds living warrant through B
    assert t.node("C") not in t.contradictions()
    # the dead path is dead: A is DEAD, recorded
    assert t.node("A").state is WhyState.DEAD


def test_kill_the_last_parent_and_it_dies():
    t = _dag()
    t.kill("A", "A is done", tick=5)
    t.kill("B", "B is done too", tick=6)
    # every path is destroyed: C and D are questionable, never deleted
    assert t.node("C").state is WhyState.UNKNOWN
    assert t.node("D").state is WhyState.UNKNOWN
    assert not t.why_should_this_run("C")
    assert t.justification("C") == 0.0
    assert t.conservation()["invariant_ok"]


def test_revive_re_resolves_only_its_own_questions():
    t = _dag()
    t.kill("A", "A is done", tick=5)
    t.kill("B", "B is done too", tick=6)
    t.resurrect("A", "A returns with new evidence", tick=7)
    # A's resurrection restores a living path: C and D return (on parole)
    assert t.node("C").state is WhyState.ALIVE
    assert t.node("D").state is WhyState.ALIVE
    # A dies again: B's death still stands, so every path is broken
    t.kill("A", "A is done again", tick=8)
    assert t.node("C").state is WhyState.UNKNOWN
    assert t.node("D").state is WhyState.UNKNOWN
    # and B's resurrection re-resolves the doubt the same way
    t.resurrect("B", "B returns with new evidence", tick=10)
    assert t.node("C").state is WhyState.ALIVE
    assert t.node("D").state is WhyState.ALIVE


# ---------------------------------------------------------------------------
# no under-cascade: the cross-linked topology
# ---------------------------------------------------------------------------

def test_cross_linked_topology_reaches_the_fixpoint():
    """The case a single BFS pass gets wrong: X is checked BEFORE its
    deeper parent P2 cascades, so X's last living path (through P2)
    looks alive at check time. The fixpoint re-checks survivors."""
    t = WhyTree()
    t.declare("root", node_id="R", tick=0)
    t.declare("left", parent="R", node_id="L", tick=0)
    t.declare("deep left", parent="L", node_id="P2", tick=0)
    t.declare("shallow right", parent="R", node_id="P1", tick=0)
    # X hangs off BOTH: a short path (through P1) and a deep one (P2)
    t.declare("cross-linked", parents=("P1", "P2"), node_id="X", tick=0)
    # and a child of X that only lives through X
    t.declare("under X", parent="X", node_id="Y", tick=0)
    # killing R strands everything — but the interesting kill is P1+P2:
    t.kill("P1", "shallow parent dies", tick=3)
    assert t.node("X").state is WhyState.ALIVE  # deep path through P2 holds
    t.kill("P2", "deep parent dies", tick=4)
    # X: no living path (P1 dead, P2 dead) -> UNKNOWN; Y follows
    assert t.node("X").state is WhyState.UNKNOWN
    assert t.node("Y").state is WhyState.UNKNOWN
    assert t.conservation()["invariant_ok"]


def test_tree_cascade_order_is_bit_for_bit_v02():
    """A tree kill cascades every living descendant in BFS order — the
    exact v0.2 behavior, order included (the necrology is the receipt)."""
    t = WhyTree()
    t.declare("root", node_id="R", tick=0)
    t.declare("a", parent="R", node_id="a", tick=0)
    t.declare("b", parent="R", node_id="b", tick=0)
    t.declare("a1", parent="a", node_id="a1", tick=0)
    t.declare("a2", parent="a", node_id="a2", tick=0)
    t.kill("R", "done", tick=1)
    order = [r.node_id for r in t.necrology()][1:]  # after R itself
    assert order == ["a", "b", "a1", "a2"]  # BFS, not alphabetical luck


# ---------------------------------------------------------------------------
# justification: the strongest living path
# ---------------------------------------------------------------------------

def test_justification_takes_the_strongest_path():
    t = WhyTree(attestation_horizon=90)
    t.declare("root A", node_id="A", tick=0)
    t.declare("root B", node_id="B", tick=0)
    t.declare("shared", parents=("A", "B"), node_id="C", tick=0)
    # only the B-path nodes keep being served
    t.heartbeat("C", 50)
    t.heartbeat("B", 50)
    t.now = 60
    # A's path: [C, A] — A stale (age 60, past grace 30) -> freshness 0.5
    # B's path: [C, B] — both stamped at 50 -> freshness 1.0
    # best path wins: the shared purpose is as fresh as its best basis
    assert t.freshness("C") == 1.0
    assert t.justification("C") == 1.0


def test_probation_on_one_path_only_caps_that_path():
    t = _dag()
    t.kill("A", "done", tick=1)
    t.resurrect("A", "new evidence", tick=2)   # A on parole
    # C's path through A: [C, A(alive, parole)] -> capped 0.5
    # C's path through B: [C, B(alive)] -> 1.0; best path wins
    assert t.justification("C") == 1.0
    t.kill("B", "done too", tick=3)    # only the paroled path remains
    assert t.justification("C") == pytest.approx(0.5)


def test_dead_path_scores_zero_living_path_scores():
    t = _dag()
    t.kill("A", "done", tick=1)
    # path [C, A(dead)] -> 0; path [C, B(alive)] -> 1.0
    assert t.justification("C") == 1.0
    # D's primary path [D, C, A] contains dead A; but paths() sees
    # [D, C, B] too — D survives through C's living basis
    assert t.justification("D") == 1.0


# ---------------------------------------------------------------------------
# stamping and the auditor
# ---------------------------------------------------------------------------

def test_stamping_serves_the_whole_dag_lineage():
    t = WhyTree()
    t.declare("root A", node_id="A", tick=0)
    t.declare("root B", node_id="B", tick=0)
    t.declare("shared", parents=("A", "B"), node_id="C", tick=0)
    took = t.stamp_chain("C", 10, by="worker")
    assert took == 3  # C + both parents
    assert t.node("A").last_beat == 10
    assert t.node("B").last_beat == 10
    assert t.node("C").last_attested_by == "worker"


def test_conservation_auditor_replays_the_dag():
    t = WhyTree(attestation_horizon=90)
    t.declare("root A", node_id="A", tick=0)
    t.declare("root B", node_id="B", tick=0)
    t.declare("shared", parents=("A", "B"), node_id="C", tick=0)
    t.declare("under", parent="C", node_id="D", tick=0)
    t.stamp_chain("D", 5, by="w")
    t.kill("A", "A done", tick=6)
    t.stamp_chain("D", 7, by="w")       # still served through B's path
    t.kill("B", "B done", tick=8)
    t.resurrect("B", "B back with evidence", tick=9)  # parole
    t.stamp_chain("D", 10, by="w")
    receipt = ConservationAuditor().verify(t)
    assert receipt.ok, receipt.summary()
    assert receipt.genesis_records == 4
    # tamper: forge an extra parent off the books
    t2 = WhyTree.from_json(t.to_json())
    t2.node("C").parents = ("A", "B", "D")  # off-books reparent
    assert not ConservationAuditor().verify(t2).ok


def test_dag_persistence_roundtrip():
    t = _dag()
    t.stamp_chain("D", 4, by="w")
    t.kill("A", "done", tick=5)
    loaded = WhyTree.from_json(t.to_json())
    assert loaded.node("C").parents == ("A", "B")
    assert loaded.node("C").parent == "A"
    assert loaded.node("A").state is WhyState.DEAD
    assert ConservationAuditor().verify(loaded).ok
    # legacy v0.3 state (parent strings, no parents field) still loads
    legacy = WhyTree()
    legacy.declare("root", node_id="R", tick=0)
    legacy.declare("kid", parent="R", node_id="K", tick=0)
    data = legacy.to_json()
    for nd in data["nodes"]:
        nd.pop("parents")  # simulate a v0.3 save
    data["genesis"] = [["R", None, "root", 0, "alive", 0],
                       ["K", "R", "kid", 0, "alive", 0]]  # v0.3 rows
    restored = WhyTree.from_json(data)
    assert restored.node("K").parents == ("R",)
    assert ConservationAuditor().verify(restored).ok


# ---------------------------------------------------------------------------
# contradictions: destroyed warrant, not mere doubt
# ---------------------------------------------------------------------------

def test_contradictions_require_destroyed_warrant():
    t = _dag()
    t.kill("A", "done", tick=1)
    assert t.contradictions() == []          # living path through B
    t.kill("B", "done too", tick=2)
    # C and D were cascaded to UNKNOWN — not contradictions, questioned
    assert t.contradictions() == []
    # force an ALIVE-with-no-warrant node (the honest dissonance case)
    t.declare("stray", parents=("A", "B"), node_id="S", tick=3,
              state=WhyState.ALIVE)
    assert [n.id for n in t.contradictions()] == ["S"]
    # UNKNOWN ancestors alone (doubt, not destruction) do not count
    t2 = _dag()
    t2.question("A", "doubt", tick=1)        # UNKNOWN, not DEAD
    assert t2.contradictions() == []


# ---------------------------------------------------------------------------
# runtime + cold storage + treaties over the DAG
# ---------------------------------------------------------------------------

def test_runtime_components_under_a_dag_node_run():
    from cognitive_ecology import AttentionBid, Outcome

    class Worker:
        id, why_node = "w", "C"

        def bid(self, ctx):
            yield AttentionBid(
                src=self.id, label="w:work", urgency=0.8,
                justification=ctx.why.justification(self.why_node),
                opportunity=1.0, novelty=1.0, expected_value=1.0)

        def act(self, ctx, label):
            return Outcome(True, "did it")

    rt = Runtime(seed=3, idle_window=999)
    rt.declare_why("root A", node_id="A")
    rt.declare_why("root B", node_id="B")
    rt.declare_why("shared", parents=["A", "B"], node_id="C")
    rt.register(Worker())
    rt.run(10)
    # running under C served BOTH lineages
    assert rt.why.node("A").last_beat == 10
    assert rt.why.node("B").last_beat == 10
    rt.why.kill("A", "done", tick=11)
    rt.run(5)  # the worker still runs through B's path
    assert any("w:work" in r.ran for r in rt.run(1))


def test_cold_storage_sweeps_and_restores_dag_subtrees():
    t = WhyTree()
    t.declare("root", node_id="R", tick=0)
    t.declare("dead branch", parent="R", node_id="X", tick=0)
    t.declare("dead leaf", parents=("X",), node_id="X1", tick=0)
    t.declare("alive elsewhere", parent="R", node_id="Y", tick=0)
    t.kill("X", "done", tick=1)
    t.now = 2000
    cold = ColdStorage(t, min_age=100)
    archived = cold.sweep()
    assert set(archived) == {"X", "X1"}
    assert t.conservation()["invariant_ok"]
    assert ConservationAuditor().verify(t).ok
    cold.restore("X", "we want it back", tick=2001)
    assert t.has("X") and t.has("X1")
    assert ConservationAuditor().verify(t).ok


def test_treaty_onto_a_dag_beneficiary():
    """A treaty may delegate a multi-parent purpose; the service check
    walks every parent edge (a routed stamp maintains the whole DAG
    lineage, so the whole lineage is service-derivable ground)."""
    from tests.test_society import _beneficiary, _provider  # reuse rigs

    a = _beneficiary()
    a.declare_why("second root", node_id="why:root2")
    # re-parent the index purpose onto BOTH roots (off the hot books is
    # impossible — declare a fresh DAG node instead)
    a.declare_why("keep the shared index fresh (joint)",
                  parents=["why:root", "why:root2"], node_id="why:jindex")
    b = _provider()
    soc = Society(name="dag-society")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.establish_treaty("B", "why:serve", "A", "why:jindex",
                         "A's joint purpose is served by B", tick=0)
    soc.run(10)
    node = a.why.node("why:jindex")
    assert node.last_attested_by == "treaty:1"
    assert node.last_beat == 10
    # BOTH roots' lines stayed fresh through the treaty's stamps
    assert a.why.node("why:root").last_beat == 10
    assert a.why.node("why:root2").last_beat == 10
    assert a.why.justification("why:jindex") == 1.0
    assert soc.audit().ok
    b.why.kill("why:serve", "closed", tick=11)
    soc.step()
    assert a.why.node("why:jindex").state is WhyState.UNKNOWN
    assert soc.audit().ok
