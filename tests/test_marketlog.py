"""The market log: the organism's observation boundary (round 21, ADR-0015).

Wave-1 finding 3 was "the organism is invisible": the five attention
factors — the platform's core scientific object — were never logged.
These tests pin the read model that fixes it, and the three laws of its
discipline (the ideation-015 verdict):

  EXACT           the floats written are the floats the market scored —
                  no rounding, no re-derivation; json roundtrips
                  bit-for-bit;
  NOT SECOND TRUTH rows are a serialization of the market's own result,
                  deletable without loss to the organism;
  NON-PERTURBING  attaching (or removing) the log changes no decision
                  and no event — pinned by a bit-identical twin run.
"""
from __future__ import annotations

import json

import pytest

from cognitive_ecology import (
    AttentionBid, AttentionMarket, Executive, MarketLog, Runtime,
)
from cognitive_ecology.attention import ClearResult
from cognitive_ecology.scripts import Outcome, Script


# ---------------------------------------------------------------------------
# synthetic clearings — the unit laws
# ---------------------------------------------------------------------------
def _clear(log: MarketLog, tick=1, k=1):
    """One synthetic clearing: a winner, a live loser, a vetoed bid."""
    market = AttentionMarket()
    ex = Executive(market, max_actions=k, market_log=log)
    bids = [
        AttentionBid(src="a", label="win", urgency=1.0, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),
        AttentionBid(src="a", label="lose", urgency=0.5, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),
        AttentionBid(src="a", label="vetoed", urgency=0.9, justification=0.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),
    ]
    return ex.arbitrate(bids, top_k=k, ts=tick)


class TestExactness:
    def test_floats_roundtrip_bit_for_bit(self):
        log = MarketLog(keep=None)
        market = AttentionMarket()
        ex = Executive(market, max_actions=1, market_log=log)
        third = 1.0 / 3.0
        ex.arbitrate([
            AttentionBid(src="a", label="x", urgency=third,
                         justification=0.1 + 0.2, opportunity=1.0,
                         novelty=1.0, expected_value=third),
        ], top_k=1, ts=1)
        row = log.bids()[0]
        assert row["urgency"] == third                      # 0.333...
        assert row["justification"] == 0.30000000000000004  # not 0.3
        # and through the durable copy: json must not round at write time
        reloaded = MarketLog.from_jsonl(log.to_jsonl())
        assert reloaded.bids()[0] == row

    def test_attention_is_the_markets_own_number(self):
        log = MarketLog(keep=None)
        _clear(log)
        rows = {r["label"]: r for r in log.bids()}
        # the market's product, recomputed from the same frozen fields,
        # equals the stored attention to the last bit
        b = AttentionBid(src="a", label="lose", urgency=0.5, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0)
        assert rows["lose"]["attention"] == b.attention


class TestStatuses:
    def test_run_starved_vetoed_distinguished(self):
        log = MarketLog(keep=None)
        _clear(log)
        rows = {r["label"]: r for r in log.bids()}
        assert rows["win"]["status"] == "run"
        assert rows["lose"]["status"] == "starved"    # live, below cut
        assert rows["vetoed"]["status"] == "vetoed"   # attention <= 0

    def test_yield_recorded_for_resource_conflicts(self):
        log = MarketLog(keep=None)
        market = AttentionMarket()
        ex = Executive(market, max_actions=3, market_log=log)
        ex.arbitrate([
            AttentionBid(src="a", label="strong", urgency=1.0, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0,
                         resource="mic"),
            AttentionBid(src="b", label="weak", urgency=0.2, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0,
                         resource="mic"),
        ], top_k=3, ts=1)
        rows = {r["label"]: r for r in log.bids()}
        assert rows["strong"]["status"] == "run"
        assert rows["weak"]["status"] == "yield"

    def test_veto_reasons_name_the_zero_factor(self):
        log = MarketLog(keep=None)
        _clear(log)
        reasons = log.veto_reasons()
        assert reasons["vetoed"]["count"] == 1
        assert "justification" in reasons["vetoed"]["zero_factors"]

    def test_vetoed_never_runs_even_in_empty_market(self):
        log = MarketLog(keep=None)
        market = AttentionMarket()
        ex = Executive(market, max_actions=5, market_log=log)
        ex.arbitrate([
            AttentionBid(src="a", label="dead-purpose", justification=0.0),
        ], top_k=5, ts=1)
        assert log.bids()[0]["status"] == "vetoed"


class TestArbiterRows:
    def test_arbiter_row_only_when_it_truly_arbitrated(self):
        log = MarketLog(keep=None)
        market = AttentionMarket()
        calls = {"n": 0}

        def promote_last(live, k):
            calls["n"] += 1
            return list(live[-1:]) + list(live[:-1])

        ex = Executive(market, max_actions=1, arbiter=promote_last,
                       market_log=log)
        # two live bids, one slot: contention -> the arbiter runs
        ex.arbitrate([
            AttentionBid(src="a", label="first", urgency=0.9, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0),
            AttentionBid(src="a", label="second", urgency=0.8, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0),
        ], top_k=1, ts=1)
        arb_rows = [r for r in log.rows() if r["kind"] == "arbiter"]
        assert calls["n"] == 1
        assert len(arb_rows) == 1
        assert arb_rows[0]["pick"] == "second"
        assert arb_rows[0]["divergent"] is True
        # the promoted bid really ran
        rows = {r["label"]: r for r in log.bids()}
        assert rows["second"]["status"] == "run"

    def test_no_arbiter_row_without_contention(self):
        log = MarketLog(keep=None)
        market = AttentionMarket()
        ex = Executive(market, max_actions=3, arbiter=lambda live, k: live,
                       market_log=log)
        ex.arbitrate([AttentionBid(src="a", label="only")], top_k=3, ts=1)
        assert not [r for r in log.rows() if r["kind"] == "arbiter"]

    def test_degraded_arbiter_writes_no_row(self):
        log = MarketLog(keep=None)
        market = AttentionMarket()

        def broken(live, k):
            raise RuntimeError("judgment failed")

        ex = Executive(market, max_actions=1, arbiter=broken, market_log=log)
        ex.arbitrate([
            AttentionBid(src="a", label="first", urgency=0.9, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0),
            AttentionBid(src="a", label="second", urgency=0.8, justification=1.0,
                         opportunity=1.0, novelty=1.0, expected_value=1.0),
        ], top_k=1, ts=1)
        assert not [r for r in log.rows() if r["kind"] == "arbiter"]
        # the shadow cleared deterministically: stronger bid ran
        rows = {r["label"]: r for r in log.bids()}
        assert rows["first"]["status"] == "run"


class TestReader:
    def test_summary_counts(self):
        log = MarketLog(keep=None)
        _clear(log)  # 1 run, 1 starved, 1 vetoed
        s = log.summary()
        assert s["bids"] == 3 and s["clears"] == 1
        assert s["run"] == 1 and s["starved"] == 1 and s["vetoed"] == 1
        assert s["clear_rate"] == pytest.approx(1 / 3)
        assert s["top_winners"] == [("win", 1)]

    def test_bounded_keep_retains_the_tail(self):
        log = MarketLog(keep=3)
        for t in range(5):
            _clear(log, tick=t)  # 3 bid rows per clearing
        assert len(log) == 3
        # only the last clearing survives — all of it, in order
        assert [r["tick"] for r in log.bids()] == [4, 4, 4]

    def test_jsonl_roundtrip(self):
        log = MarketLog(keep=None)
        _clear(log, tick=1)
        _clear(log, tick=2)
        text = log.to_jsonl()
        again = MarketLog.from_jsonl(text)
        assert again.rows() == log.rows()
        assert again.summary() == log.summary()
        # every line is a valid json object (the analyst's first promise)
        for line in text.splitlines():
            assert isinstance(json.loads(line), dict)


# ---------------------------------------------------------------------------
# the organism: integration + non-perturbation
# ---------------------------------------------------------------------------
def _build(seed=7):
    from experiments.minimal_world import build_world
    return build_world(seed)


class TestOrganismIntegration:
    def test_every_bid_of_every_tick_is_logged(self):
        rt = _build()
        reports = rt.run(20)
        logged_ticks = {r["tick"] for r in rt.market_log.bids()}
        assert logged_ticks == {rep.tick for rep in reports}
        # per tick, the log's run set is the report's ran set
        for rep in reports[:5]:
            ran_logged = {r["label"] for r in rt.market_log.bids()
                          if r["tick"] == rep.tick and r["status"] == "run"}
            assert ran_logged == set(rep.ran)

    def test_non_perturbing_bit_identical_twin(self):
        """The law of the read model: observation changes nothing.

        Two identical organisms — one whose log is read after every
        tick, one never touched — must produce byte-identical event
        streams. (The log is wired in both; the variable is READING it,
        and reading must not matter. Construction is identical because
        the log is always attached: there is no off-switch to forget.)
        """
        rt_a, rt_b = _build(seed=11), _build(seed=11)
        for rep in rt_a.run(30):
            assert len(rt_a.market_log) > 0  # read it, summarize it
            _ = rt_a.market_log.summary()
        rt_b.run(30)
        assert rt_a.bus.to_jsonl() == rt_b.bus.to_jsonl()

    def test_determinism_extends_to_the_log(self):
        rt_a, rt_b = _build(seed=5), _build(seed=5)
        rt_a.run(25)
        rt_b.run(25)
        assert rt_a.market_log.to_jsonl() == rt_b.market_log.to_jsonl()

    def test_veto_reasons_on_a_real_organism(self):
        """A killed purpose must show up as a justification veto.

        Truth worth pinning: the script ecology's ``bids()`` pre-gates
        zero-justification scripts UPSTREAM of the market, so an ecology
        script never appears as a vetoed bid. Veto rows come from
        components that submit raw bids (LLM proposal agents, custom
        components) — the veto law protects the market no matter who
        speaks. Here: a raw-bid worker whose purpose is killed mid-life.
        """
        rt = Runtime(seed=7, top_k=3, idle_window=999)
        rt.tensions.add("energy", growth=0.05)
        rt.declare_why("stay alive", node_id="why:root")
        rt.declare_why("work", parent="why:root", node_id="why:work")
        rt.declare_why("the task itself", parent="why:root", node_id="why:task")

        class Worker:
            """Component gate reads why:work (alive); the BID's purpose is
            why:task — killable without gating the component off."""

            id = "w"
            why_node = "why:work"

            def bid(self, ctx):
                yield AttentionBid(
                    src=self.id, label="w:work",
                    urgency=max(0.3, ctx.tensions.level("energy")),
                    justification=ctx.why.justification("why:task"),
                    opportunity=1.0, novelty=1.0, expected_value=1.0,
                )

            def act(self, ctx, label):
                return Outcome(True, "did it")

        rt.register(Worker())
        rt.run(3)
        assert all(r["status"] == "run" for r in rt.market_log.bids())
        rt.why.kill("why:task", reason="test: purpose revoked")
        rt.run(3)
        reasons = rt.market_log.veto_reasons()
        assert "w:work" in reasons
        assert "justification" in reasons["w:work"]["zero_factors"]
        # and the run/act split is visible in the summary
        s = rt.market_log.summary()
        assert s["vetoed"] >= 3 and s["run"] >= 3

    def test_loaded_organism_starts_a_fresh_log(self, tmp_path):
        """The log is observation, not state: it never rides in save()."""
        rt = _build()
        rt.run(10)
        assert len(rt.market_log) > 0
        rt.save(str(tmp_path / "s"))

        class TinyBidder:
            id = "tiny"
            why_node = "why:critter"

            def bid(self, ctx):
                yield AttentionBid(src=self.id, label="tiny:beat",
                                   urgency=0.5, justification=1.0,
                                   opportunity=1.0, novelty=1.0,
                                   expected_value=1.0)

            def act(self, ctx, label):
                return Outcome(True, "beat")

        rt2 = Runtime.load(
            str(tmp_path / "s"), attach=lambda r: r.register(TinyBidder())
        )
        assert len(rt2.market_log) == 0          # fresh: history is the host's
        rt2.run(3)
        ticks = {r["tick"] for r in rt2.market_log.bids()}
        assert ticks == {11, 12, 13}             # and it observes the new life
