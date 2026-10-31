"""Re-attestation economics — the experiment that prices liveness.

Two purposes are declared at birth. One is served by a worker every day;
the other is not. The organism runs for a year (480 ticks = 2 ticks/hour,
or whatever it is in your world). Watch:

  * the served purpose holds justification 1.0 for the whole run;
  * the unserved purpose decays after its grace window, chokes in the
    market, and lapses to UNKNOWN at the audit past the horizon;
  * at tick 300 the owner re-justifies the lapsed purpose ("the archive
    became relevant again") — it buys a fresh horizon and holds it;
  * at no point is anything deleted: conservation holds at every audit.

Zero LLM calls. Run: python experiments/reattestation_economics.py
"""
import sys

from cognitive_ecology import AttentionBid, Outcome, Runtime, WhyState

HORIZON = 120
RUN = 480
REVIVE_IDLE_AT = 150   # revive without serving it
REVIVE_SERVED_AT = 300  # revive AND start serving it


class Worker:
    """Serves the forage purpose: bids and acts every tick it can."""

    def __init__(self):
        self.id = "worker"
        self.why_node = "why:forage"

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label="worker:forage",
            urgency=max(0.4, ctx.tensions.level("energy")),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        ctx.tensions.relieve("energy", 0.35)
        return Outcome(True, "foraged")


class Archivist:
    """Serves the archive purpose. Joins the organism mid-life."""

    def __init__(self):
        self.id = "archivist"
        self.why_node = "why:archive"

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label="archivist:file",
            urgency=max(0.4, ctx.tensions.level("order")),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        ctx.tensions.relieve("order", 0.4)
        return Outcome(True, "filed logs")


def main():
    rt = Runtime(seed=7, attestation_horizon=HORIZON)
    rt.tensions.add("energy", growth=0.03)
    rt.tensions.add("order", growth=0.02)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage for energy", parent="why:root", node_id="why:forage")
    rt.declare_why("archive the old logs", parent="why:root", node_id="why:archive")
    rt.register(Worker())

    print(f"re-attestation economics: horizon={HORIZON} ticks, run={RUN} ticks")
    print(f"{'tick':>5} {'forage just':>12} {'archive just':>13} "
          f"{'forage':>8} {'archive':>8}  event")
    lapses = revives = 0
    for tick in range(1, RUN + 1):
        note = ""
        if tick == REVIVE_IDLE_AT and \
                rt.why.node("why:archive").state is WhyState.UNKNOWN:
            rt.why.revive("why:archive",
                          reason="owner re-justified (but hired nobody)", tick=tick)
            revives += 1
            note = "REVIVED without service"
        if tick == REVIVE_SERVED_AT and \
                rt.why.node("why:archive").state is WhyState.UNKNOWN:
            rt.why.revive("why:archive",
                          reason="archive became relevant again", tick=tick)
            rt.register(Archivist())  # and this time, someone serves it
            revives += 1
            note = "REVIVED and served (archivist joins)"
        r = rt.tick()
        lapses += len(r.lapsed)
        if tick % 40 == 0 or r.lapsed or note:
            f, a = rt.why.node("why:forage"), rt.why.node("why:archive")
            if r.lapsed:
                note = f"LAPSED: {','.join(r.lapsed)}"
            print(f"{tick:>5} {rt.why.justification('why:forage'):>12.3f} "
                  f"{rt.why.justification('why:archive'):>13.3f} "
                  f"{f.state.value:>8} {a.state.value:>8}  {note}")

    c = rt.why.conservation()
    print("\n--- receipts ---")
    print(f"lapses recorded : {lapses}")
    print(f"revives         : {revives}")
    print(f"ever declared   : {c['ever_declared']} (must be 3: nothing deleted)")
    print(f"invariant ok    : {c['invariant_ok']}")
    print(f"necrology lines : {len(rt.why.necrology())}")
    assert c["invariant_ok"] and c["ever_declared"] == 3
    assert rt.why.node("why:forage").state is WhyState.ALIVE
    assert rt.why.node("why:archive").state is WhyState.ALIVE
    assert lapses >= 2 and revives == 2
    print("lesson 1: revival without service buys exactly one more horizon "
          "(the archive lapsed twice).")
    print("lesson 2: revival WITH service holds (the archivist kept it fresh "
          "to the end).")
    print("conservation held across the whole run — use it or lose it, "
          "lose it or re-justify it, never delete it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
