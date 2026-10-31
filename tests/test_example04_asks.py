"""The world-not-bus ingest law, pinned by its own bug (round 22).

Wave-1 found examples/04 teaching a lossy pattern: player asks were
emitted on the event bus and read back through a 10-event window,
racing the top-k scheduler. An ask the NPC didn't answer within the
window was forgotten forever — even by the remember-everything NPC
after a restart. These tests pin the fixed example so the pattern
cannot quietly return:

  1. an ask is persisted into the WORLD GRAPH at ingest time;
  2. it survives whether or not the NPC ever answers it;
  3. it survives a save/load restart;
  4. the NPC answers from the graph, working the queue.

The example module is imported by path (it lives outside the package).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "04_game_npc" / "main.py"


@pytest.fixture(scope="module")
def ex():
    """Load examples/04 as a module (it self-inserts src/ on sys.path)."""
    spec = importlib.util.spec_from_file_location("example04", EXAMPLE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _questions_in_graph(rt) -> list:
    return sorted(
        e.dst for e in rt.graph.edges_of("player:you") if e.rel == "asked"
    )


class TestIngestLaw:
    def test_asks_are_persisted_at_ingest(self, ex, tmp_path):
        rt = ex.build_world()
        ex.player_visit(rt, "visit", ["tell me about the old mill"])
        # durable the moment the player speaks — not when the NPC answers
        assert _questions_in_graph(rt) == ["question:tell-me-about-the-old-mill"]

    def test_an_unanswered_ask_survives_the_scheduler(self, ex):
        """THE regression: the ask never won attention (the NPC never
        gossip'd), yet it is still in the world — and the NPC can
        answer it later from the graph, not from a lost bus window."""
        rt = ex.build_world()
        # ask without running any ticks: no attention was ever spent
        rt.graph.seen(["player:you"], tick=rt.tick_no)
        for ask in ("tell me about the pond", "what about the north road?"):
            qid = f"question:{ask.replace('?', '').replace(' ', '-').lower()}"
            rt.graph.upsert(qid, "question", {"text": ask}, tick=rt.tick_no)
            rt.graph.link("player:you", qid, "asked", tick=rt.tick_no)
        assert len(_questions_in_graph(rt)) == 2
        # now let Merle live: gossip reads the GRAPH queue, not the bus
        answered = []
        for _ in range(6):
            for r in rt.run(2):
                answered.extend(r.ran)
        assert "gossip" in answered, "gossip must find graph-persisted asks"
        rumors = [e.dst for e in rt.graph.edges_of("player:you")
                  if e.rel == "asked_about"]
        assert rumors, "the ask became an answered rumor"

    def test_gossip_works_the_queue_not_one_topic(self, ex):
        rt = ex.build_world()
        ex.player_visit(rt, "v1", ["tell me about the old mill"])
        ex.player_visit(rt, "v2", ["what about the north road?"])
        rumors = set()
        for _ in range(8):
            for r in rt.run(2):
                pass
            rumors = {e.dst for e in rt.graph.edges_of("player:you")
                      if e.rel == "asked_about"}
            if len(rumors) >= 2:
                break
        assert len(rumors) >= 2, "both asks should get answered eventually"

    def test_asks_survive_restart_even_unanswered(self, ex, tmp_path):
        """The persistence promise, extended: even a never-answered ask
        is remembered after the server restarts."""
        rt = ex.build_world()
        # ask about something, run NO ticks (the NPC never answered)
        rt.graph.seen(["player:you"], tick=rt.tick_no)
        rt.graph.upsert("question:the-pond", "question",
                        {"text": "what about the pond?"}, tick=rt.tick_no)
        rt.graph.link("player:you", "question:the-pond", "asked",
                      tick=rt.tick_no)
        rt.save(str(tmp_path / "merle"))
        rt2 = type(rt).load(str(tmp_path / "merle"), attach=ex.attach)
        assert "question:the-pond" in _questions_in_graph(rt2)
        # and reminisce can acknowledge the unfinished business
        out = None
        for _ in range(6):
            for r in rt2.run(2):
                if "reminisce" in r.ran:
                    out = r
        assert out is not None
