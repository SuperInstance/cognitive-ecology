"""A personal journal organism: anti-RAG recall + a nag that learns manners.

Two demos:
  1. RECALL   "why was I tired on thursday?" answered by walking the graph
              (co-occurrence + recency + weight) versus a literal keyword
              search — walk finds the story, keywords find the word
  2. BURDEN   a check-in script that discharges a checkin-debt tension;
              once the debt is paid its urgency hits zero and the VETO LAW
              stops it from clearing, no matter how empty the market is
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    Event, EventKind, Outcome, Runtime, Script,
)

ENTRIES = [
    ("monday",    "slept well. long run in the morning. energy all day."),
    ("tuesday",   "coffee at dawn, then the deadline crunch. headachy by nine."),
    ("wednesday", "no run. two coffees. deadline still looming. slept badly."),
    ("thursday",  "exhausted. third coffee before noon. skipped the run again. deadline shipped at six."),
    ("friday",    "slept ten hours. no coffee. slow walk instead of a run. calm."),
    ("saturday",  "long run. picnic. no screens. great sleep."),
    ("sunday",    "quiet. planned the week. early to bed."),
]

CONCEPTS = ["run", "coffee", "deadline", "slept well", "slept badly",
            "exhausted", "calm", "screens", "sleep", "headachy", "tired"]


def concepts_in(text: str) -> list:
    t = text.lower()
    found = [c for c in CONCEPTS if c in t]
    if "exhausted" in t:
        found.append("tired")  # a tiny synonym bridge, standing in for parsing
    return found


def ingest(rt: Runtime) -> None:
    for tick, (day, text) in enumerate(ENTRIES, start=1):
        rt.graph.upsert(f"day:{day}", "day", {"text": text}, tick=tick)
        batch = []
        for c in concepts_in(text):
            rt.graph.upsert(f"concept:{c}", "concept", {}, tick=tick)
            rt.graph.link(f"day:{day}", f"concept:{c}", "about", tick=tick)
            batch.append(Event(kind=EventKind.STATE, ts=tick, src="journal",
                               payload=(f"concept:{c}", {})))
        rt.memory.consolidate(batch, tick=tick)  # Hebbian: co-firing wires
    print(f"[ingest] {len(ENTRIES)} entries -> {rt.graph.node_count()} nodes, "
          f"{rt.graph.edge_count()} edges (co-occurrence built by memory)")


def recall_by_walk(rt: Runtime, question: str, budget: int = 8) -> list:
    """Anti-RAG recall: cues -> best-first traversal."""
    cues = [f"concept:{c}" for c in concepts_in(question) if rt.graph.has(f"concept:{c}")]
    walked = rt.graph.walk(cues, budget=budget)
    return walked.ids


def recall_by_keyword(question: str) -> list:
    """The naive baseline: literal substring matches over the raw text."""
    words = [w for w in question.lower().split() if w in CONCEPTS or w in
             [d for d, _ in ENTRIES]]
    hits = []
    for day, text in ENTRIES:
        if any(w in text or w == day for w in words):
            hits.append(f"day:{day}")
    return hits


def act_check_in(ctx) -> Outcome:
    ctx.tensions.relieve("checkin_debt", 0.45)
    ctx.emit(EventKind.SIGNAL, ("you", "journal check-in: how did today go?"),
             src="journal")
    return Outcome(True, "asked")


class JournalOrganism:
    id = "journal"
    why_node = "why:journal"

    def __init__(self, rt: Runtime):
        # a nag with manners: it only bids when the debt actually crosses
        # its trigger threshold (the `when` is the opportunity factor)
        rt.ecology.spawn(Script(
            name="check-in", why_node="why:journal", owner="journal",
            relieves=("checkin_debt",),
            when=lambda ctx: ctx.tensions.level("checkin_debt") > 0.2,
            act=act_check_in,
        ), tick=rt.tick_no)

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner="journal")

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


def main() -> None:
    rt = Runtime(seed=4, top_k=1)
    rt.declare_why("keep an honest record of the week", node_id="why:journal")
    rt.tensions.add("checkin_debt", growth=0.1,
                    description="the journal wants its daily entry")

    ingest(rt)

    question = "why was I tired on thursday?"
    print(f'\n[recall] "{question}"')
    walked = recall_by_walk(rt, question)
    print("  walk found:     " + ", ".join(walked))
    keywords = recall_by_keyword(question)
    print("  keyword search: " + (", ".join(keywords) or "(nothing)"))
    print("  -> the walk surfaces sleep/deadline/coffee around 'tired':")
    print("     the STORY of the tiredness, not just the word.")

    # ---------------------------------------------------------------- burden
    print("\n[burden] the check-in nag, and the veto law")
    rt.register(JournalOrganism(rt))
    nag_ticks = []
    for report in rt.run(12):
        if "check-in" in report.ran:
            nag_ticks.append(report.tick)
    print(f"   nagged at ticks {nag_ticks} — only when the debt crossed 0.20;")
    print("   between nags the trigger was false, so the bid never existed.")
    print("   and once the debt is paid, urgency -> 0, attention -> 0, and the")
    print("   market refuses to clear it (the veto law: scarcity is not desperation)")

    print("\n[graph] the week, as the organism knows it:")
    for line in rt.graph.digest(12).splitlines()[1:]:
        print("   " + line)


if __name__ == "__main__":
    main()
