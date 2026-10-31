"""The safe seam + attach ergonomics (round 23).

Wave-1 findings 6 and 7, closed at the layer that owns them:

  attach() is a rite of passage  ->  ensure_why / ensure_tension /
                                     ensure_component / ensure_script:
                                     the rite runs twice, painlessly
  duplicate proposals count as   ->  spawn_unique: a rejected duplicate
  accepted (population bloat)        is a DEMOTION — counted, logged,
                                     visible on the bus, and paid for
                                     in the proposer's accept_rate
  rest accepts "nan"              ->  the seam rejects it; the kernel
                                     no-ops it (defense in depth)
"""
from __future__ import annotations

import math

import pytest

from cognitive_ecology import Runtime, Script, ScriptEcology
from cognitive_ecology.scripts import Outcome


# ---------------------------------------------------------------------------
# the attach rite, de-rited
# ---------------------------------------------------------------------------
class _Desk:
    """A component built the way real hosts build them: closures."""

    id = "desk"
    why_node = "why:desk"

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner="desk")

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


def _attach(rt: Runtime) -> None:
    """THE RITE — now four idempotent calls instead of guarded ones."""
    rt.ensure_why("serve the user", node_id="why:root")
    rt.ensure_why("answer questions", parent="why:root", node_id="why:desk")
    rt.ensure_tension("questions", growth=0.3, level=0.0)
    rt.ensure_component(_Desk())
    rt.ensure_script(Script(
        name="answer", why_node="why:desk", owner="desk",
        relieves=("questions",), act=lambda ctx: Outcome(True, "ok"),
    ), tick=rt.tick_no)


class TestEnsure:
    def test_the_rite_runs_twice_painlessly(self):
        rt = Runtime()
        _attach(rt)
        _attach(rt)  # <- the whole point: no guards, no raises
        assert len(rt.why.nodes()) == 2
        assert rt.tensions.names() == ["questions"]
        assert rt.component("desk") is not None
        assert rt.ecology.population() == 1

    def test_ensure_why_returns_the_same_node(self):
        rt = Runtime()
        a = rt.ensure_why("one purpose", node_id="why:p")
        b = rt.ensure_why("one purpose", node_id="why:p")
        assert a is b

    def test_ensure_why_statement_mismatch_raises(self):
        """An id means one purpose, forever — re-attaching with a
        different statement is a lie, not an idempotence."""
        rt = Runtime()
        rt.ensure_why("one purpose", node_id="why:p")
        with pytest.raises(ValueError, match="already means"):
            rt.ensure_why("a DIFFERENT purpose", node_id="why:p")

    def test_ensure_tension_never_resets_a_saved_level(self):
        rt = Runtime()
        rt.ensure_tension("energy", growth=0.1, level=0.0)
        rt.tensions.burden("energy", 0.7)
        rt.ensure_tension("energy", growth=0.1, level=0.0)  # re-attach
        assert rt.tensions.level("energy") == pytest.approx(0.7)

    def test_ensure_component_reports_registration(self):
        rt = Runtime()
        rt.ensure_why("the desk works", node_id="why:desk")
        assert rt.ensure_component(_Desk()) is True
        assert rt.ensure_component(_Desk()) is False

    def test_ensure_script_rehydrates_after_load(self, tmp_path):
        rt = Runtime()
        _attach(rt)
        rt.ecology.get("answer").fires = 42
        rt.save(str(tmp_path / "s"))

        rt2 = Runtime.load(str(tmp_path / "s"), attach=_attach)
        answer = rt2.ecology.get("answer")
        assert answer is not None and answer.fires == 42


# ---------------------------------------------------------------------------
# duplicate economics: a rejected duplicate is a demotion
# ---------------------------------------------------------------------------
def _llm_script(name, action="observe", args=None, hint="always",
                owner="agent", params=None):
    return Script(
        name=name, why_node="why:agent", owner=owner,
        relieves=("curiosity",),
        params=params if params is not None else
        {"action": action, "args": args or {}, "when_hint": hint},
        act=lambda ctx: Outcome(True, "did"),
    )


class TestDuplicateEconomics:
    def test_same_behavior_different_name_is_a_duplicate(self):
        eco = ScriptEcology()
        eco.spawn(_llm_script("watch-berries", "observe", {"focus": ["b:1"]}))
        new, dup = eco.spawn_unique(
            _llm_script("look-at-berries", "observe", {"focus": ["b:1"]}))
        assert new is None and dup.name == "watch-berries"
        assert eco.duplicates_rejected == 1
        assert eco.duplicate_log == [(0, "look-at-berries", "watch-berries")]

    def test_different_args_is_not_a_duplicate(self):
        eco = ScriptEcology()
        eco.spawn(_llm_script("watch-berries", "observe", {"focus": ["b:1"]}))
        new, dup = eco.spawn_unique(
            _llm_script("watch-pond", "observe", {"focus": ["pond:1"]}))
        assert new is not None and dup is None
        assert eco.population() == 2

    def test_when_hint_counts_toward_behavior(self):
        """always-watch vs every-5-watch are different behaviors."""
        eco = ScriptEcology()
        eco.spawn(_llm_script("watch", "observe", {"focus": ["b:1"]}, "always"))
        new, _ = eco.spawn_unique(
            _llm_script("watch2", "observe", {"focus": ["b:1"]}, "every:5"))
        assert new is not None

    def test_dead_original_means_reproposal_is_resurrection(self):
        """Only the LIVE population is searched: a dead script's behavior
        is free to propose again — that's revival, not duplication."""
        eco = ScriptEcology()
        first = eco.spawn(_llm_script("watch", "observe", {"focus": ["b:1"]}))
        eco._scripts.pop(first.id)            # it dies (necrology path aside)
        eco._by_name.pop(first.name)
        new, dup = eco.spawn_unique(
            _llm_script("watch-again", "observe", {"focus": ["b:1"]}))
        assert new is not None and dup is None

    def test_code_scripts_fall_back_to_name_signatures(self):
        eco = ScriptEcology()
        eco.spawn(Script(name="forage", why_node="w", owner="critter"))
        new, dup = eco.spawn_unique(
            Script(name="forage", why_node="w", owner="critter"))
        assert new is None and dup.name == "forage"

    def test_the_log_is_bounded(self):
        eco = ScriptEcology()
        eco.spawn(_llm_script("base", "observe", {"focus": ["b:1"]}))
        for i in range(250):
            eco.spawn_unique(_llm_script(f"clone-{i}", "observe",
                                         {"focus": ["b:1"]}))
        assert eco.duplicates_rejected == 250
        assert len(eco.duplicate_log) == 200   # the recent tail only


# ---------------------------------------------------------------------------
# the orchestrator seam: bloat is over
# ---------------------------------------------------------------------------
class _ScriptedProvider:
    """Says exactly one thing, every time — the repeat-offender model."""

    def __init__(self, text: str):
        self.text = text
        self.calls = 0

    def complete(self, system, user, max_tokens=800, temperature=0.7):
        from cognitive_ecology.agents.providers import Completion
        self.calls += 1
        return Completion(text=self.text, model="scripted",
                          prompt_tokens=(len(system) + len(user)) // 4,
                          completion_tokens=len(self.text) // 4)


_ONE_PROPOSAL = ('[{"name": "watch", "action": "observe", '
                 '"args": {"focus": ["b:1"]}, "relieves": ["curiosity"], '
                 '"focus": ["b:1"], "when_hint": "always"}]')


class TestOrchestratorSeam:
    def _agent(self):
        from cognitive_ecology.agents.orchestrator import LLMAgent
        from cognitive_ecology.agents.providers import StablePrefixSession
        rt = Runtime()
        rt.ensure_why("the agent helps", node_id="why:root")
        rt.ensure_why("by proposing scripts", parent="why:root",
                      node_id="why:agent")
        rt.ensure_tension("curiosity", growth=0.05)
        provider = _ScriptedProvider(_ONE_PROPOSAL)
        session = StablePrefixSession(provider, "prefix", label="agent")
        agent = LLMAgent("agent", "why:agent", session, every=1)
        rt.ensure_component(agent)
        return rt, agent

    def test_no_more_tick_variants(self):
        """The old seam spawned name~tick clones on every re-proposal;
        population bloated forever. Now: one live script per behavior."""
        rt, agent = self._agent()
        from cognitive_ecology.runtime import WorldSnapshot

        out1 = agent._propose(WorldSnapshot(rt))
        out2 = agent._propose(WorldSnapshot(rt))
        assert out1.ok
        assert not out2.ok                       # all duplicates this time
        assert "~" not in (out2.note or "")      # no variant names anywhere
        names = [s.name for s in rt.ecology.alive(owner="agent")]
        assert names == ["watch"]                # exactly one, no clones
        assert rt.ecology.duplicates_rejected == 1

    def test_the_demotion_is_visible_on_the_bus(self):
        rt, agent = self._agent()
        from cognitive_ecology.runtime import WorldSnapshot
        agent._propose(WorldSnapshot(rt))
        agent._propose(WorldSnapshot(rt))
        errors = [e for e in rt.bus.log() if e.kind.name == "ERROR"]
        assert any("duplicate rejected" in str(e.payload) for e in errors)

    def test_accept_rate_falls_on_duplicates(self):
        """The demotion is paid for: accept_rate counts spawns only, so
        the propose bid's expected value decays with every dupe."""
        rt, agent = self._agent()
        from cognitive_ecology.runtime import WorldSnapshot
        agent._propose(WorldSnapshot(rt))
        after_spawn = agent.accept_rate
        for _ in range(3):
            agent._propose(WorldSnapshot(rt))
        assert agent.accept_rate < after_spawn


# ---------------------------------------------------------------------------
# the nan hole, closed at both layers
# ---------------------------------------------------------------------------
class TestNanHole:
    def test_rest_rejects_nan_at_the_seam(self):
        from cognitive_ecology.agents.orchestrator import _act_rest
        rt = Runtime()
        rt.tensions.add("energy")
        rt.tensions.burden("energy", 0.9)

        class Ctx:
            tensions = rt.tensions

        out = _act_rest(Ctx(), {"tension": "energy", "amount": float("nan")})
        assert not out.ok and "finite" in out.note
        assert rt.tensions.level("energy") == pytest.approx(0.9)

    def test_relieve_no_ops_nan_at_the_kernel(self):
        rt = Runtime()
        rt.tensions.add("energy")
        rt.tensions.burden("energy", 0.8)
        assert rt.tensions.relieve("energy", float("nan")) == pytest.approx(0.8)
        assert rt.tensions.relieve("energy", float("inf")) == pytest.approx(0.8)

    def test_burden_no_ops_nan_at_the_kernel(self):
        rt = Runtime()
        rt.tensions.add("energy")
        assert rt.tensions.burden("energy", float("nan")) == 0.0
        assert rt.tensions.level("energy") == 0.0
