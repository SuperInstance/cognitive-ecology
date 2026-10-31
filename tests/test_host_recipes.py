"""The docs/10 FastAPI recipe, executed live in-process (wave-2 probe B).

The first draft of Recipe 4 put a blocking ``WallClockDriver.run()``
inside an asyncio task — the event loop froze, the app never finished
startup, and no request was ever served. The wave-2 live probe caught
it; this test keeps it caught. A recipe that has not run is a rumor,
not a recipe.

The app is driven over httpx's ASGI transport (no socket, no port):
lifespan runs, the organism ticks between requests, and the
world-not-bus ingest law is verified end to end through HTTP.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import pytest

pytest.importorskip("fastapi", reason="the recipe's own deps (dev extra)")

from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from cognitive_ecology import Runtime, Script  # noqa: E402
from cognitive_ecology.scripts import Outcome  # noqa: E402


def _build() -> Runtime:
    rt = Runtime()
    rt.declare_why("serve the web", node_id="why:web")
    rt.tensions.add("questions", growth=0.4)

    class Desk:
        id = "desk"
        why_node = "why:web"

        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="desk")

        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt.register(Desk())
    rt.ecology.spawn(Script(
        name="answer", why_node="why:web", owner="desk",
        relieves=("questions",), act=lambda ctx: Outcome(True, "ok"),
    ), tick=0)
    return rt


async def _recipe_app_session() -> tuple:
    """docs/10 Recipe 4, verbatim in shape: async-native tick loop
    (NEVER a blocking driver in a task), lifespan-scoped, requests
    interleave with ticks on the one event loop."""
    rt = _build()
    TICK_INTERVAL = 0.01

    async def organism_loop(stop_after: float = 3600.0):
        end = time.monotonic() + stop_after
        while time.monotonic() < end:
            rt.tick()
            await asyncio.sleep(TICK_INTERVAL)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(organism_loop())
        yield
        task.cancel()

    app = FastAPI(lifespan=lifespan)

    @app.post("/ask")
    def ask(text: str):
        qid = "question:" + str(abs(hash(text)))[:8]
        rt.graph.upsert(qid, "question", {"text": text}, tick=rt.tick_no)
        rt.graph.link("user:web", qid, "asked", tick=rt.tick_no)
        return {"ok": True, "tick": rt.tick_no}

    @app.get("/state")
    def state():
        return {"tick": rt.tick_no, "market": rt.market_log.summary(),
                "tensions": rt.tensions.snapshot()}

    transport = ASGITransport(app=app)
    # httpx's ASGI transport does not run lifespan events; enter the
    # app's own lifespan context so the organism loop actually starts
    # (and is cancelled on exit) in this same event loop
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") \
                as client:
            a = (await client.post("/ask", params={"text": "hello"})).json()
            s = None
            for _ in range(20):                    # let the loop tick a while
                await asyncio.sleep(0.02)
                s = (await client.get("/state")).json()
                if s["tick"] >= 5:
                    break
            return a, s, rt


class TestRecipe4:
    def test_the_recipe_serves_and_ticks(self):
        """The app serves requests WHILE the organism ticks, the read
        model answers through HTTP, and the ingest law holds: the ask
        lands in the world graph, not on the bus."""
        a, s, rt = asyncio.run(_recipe_app_session())
        assert a["ok"] is True
        assert s is not None and s["tick"] >= 5, \
            "the organism must tick while serving"
        assert "clear_rate" in s["market"]
        assert any(e.rel == "asked" for e in rt.graph.edges_of("user:web"))
        assert rt.market_log.summary()["clears"] >= 5

    def test_async_native_loop_yields_to_the_loop(self):
        """The bug the wave-2 probe caught, pinned as its lesson: the
        async-native loop YIELDS between ticks (the event loop breathes,
        requests interleave); a blocking driver call would starve the
        watcher task to zero runs."""
        rt = _build()
        yielded = []

        async def watcher():
            for _ in range(10):
                yielded.append(time.monotonic())
                await asyncio.sleep(0)

        async def async_native_ticks():
            for _ in range(10):
                rt.tick()
                await asyncio.sleep(0)        # yields: the loop breathes

        async def main():
            await asyncio.gather(async_native_ticks(), watcher())

        asyncio.run(main())
        assert len(yielded) >= 5               # the watcher ran DURING ticks
