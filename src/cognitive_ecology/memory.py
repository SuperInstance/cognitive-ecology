"""L3 — Memory: the event stream becomes world structure.

Short-term memory is the event log (L1). Long-term memory is the World
Graph (L2). ``Memory`` is the thin, honest organ between them: on every
tick it consolidates recent events into graph mutations.

Rules of consolidation
----------------------
* STATE events refresh/upsert the entity they mention.
* SIGNAL events wire actors to what they spoke of.
* TENSION events keep one node per drive, with its current level.
* Entities that co-occur within the same tick get Hebbian edges
  ("what fires together wires together"), strengthened on repetition.
* Replay (during sleep) consolidates the same events again with a boost —
  the equivalent of hippocampal replay turning episodes into structure.

There is no embedding step, no re-index, no vector store. Consolidation is
cheap, local, and incremental — small enough to run every tick.
"""
from __future__ import annotations

from .events import EventKind
from .graph import WorldGraph


class Memory:
    """Consolidates events into the World Graph. That is all memory is here."""

    def __init__(self, graph: WorldGraph) -> None:
        self.graph = graph

    def consolidate(self, events, tick: int, boost: float = 1.0) -> int:
        """Fold a batch of events into the graph. Returns mutation count."""
        mutations = 0
        entities: list = []
        for ev in events:
            if ev.kind == EventKind.STATE and ev.payload:
                eid = str(ev.payload[0])
                props = ev.payload[1] if len(ev.payload) > 1 and isinstance(ev.payload[1], dict) else None
                if self.graph.has(eid):
                    self.graph.seen([eid], tick=tick)
                    if props:
                        self.graph.upsert(eid, self.graph.get(eid).kind, props, tick=tick)
                else:
                    self.graph.upsert(eid, "observed", props, tick=tick)
                mutations += 1
                entities.append(eid)

            elif ev.kind == EventKind.SIGNAL and ev.payload:
                target = str(ev.payload[0])
                actor = f"actor:{ev.src}"
                self.graph.upsert(actor, "actor", {}, tick=tick)
                if not self.graph.has(target):
                    self.graph.upsert(target, "mentioned", {}, tick=tick)
                else:
                    self.graph.seen([target], tick=tick)
                self.graph.link(actor, target, "spoke_of", tick=tick)
                mutations += 1
                entities.append(target)

            elif ev.kind == EventKind.TENSION and ev.payload:
                name = str(ev.payload[0])
                level = ev.payload[1] if len(ev.payload) > 1 else None
                props = {"level": level} if level is not None else None
                self.graph.upsert(f"tension:{name}", "tension", props, tick=tick)
                mutations += 1

        # Hebbian co-occurrence: entities sharing a tick get wired together.
        uniq = sorted(set(entities))[:8]  # cap keeps ticks O(small)
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                self.graph.link(uniq[i], uniq[j], "co", tick=tick, strengthen=0.05 * boost)
                mutations += 1
        return mutations

    def recall(self, cues, budget: int = 16):
        """Anti-RAG recall: traverse from cues, best-first, under budget."""
        return self.graph.walk(cues, budget=budget)

    def replay(self, events, tick: int) -> int:
        """Sleep replay: consolidate again, boosted. Episodes -> structure."""
        return self.consolidate(events, tick, boost=2.0)
