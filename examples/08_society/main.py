"""The society: purpose that crosses organisms, in one screen.

Three organisms. A is a researcher that leans on external archives for
its shared-index purpose. B is the first archive. C is the second.

You will watch the whole life of a delegation:

  ACT 1  the treaty works — B serves, and A's purpose stays fresh ON
         A'S OWN BOOKS with provenance `treaty:1` (A never runs a
         component under it);
  ACT 2  neglect, the soft path — B goes quiet (its archive purpose
         stays ALIVE, it just stops serving); nobody dies, no event
         fires; A's stamps simply stop, A's own economics strangle the
         delegation, and A's OWN reaper lapses it;
  ACT 3  death, the hard path — A revives, delegates to C, C serves,
         and then C's provider purpose is KILLED: the exchange breaks
         the treaty and QUESTIONS A's node, with a receipt naming the
         treaty and the doubter, in the same step;
  ACT 4  the audits — every member's conservation receipt, the
         federation receipt, and the treaty ledger where broken
         treaties are never deleted.

Zero LLM calls. Zero keys. Zero new dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    ACTIVE, BROKEN, AttentionBid, ConservationAuditor, EventKind,
    Outcome, Runtime, Society, WhyState,
)

HORIZON = 90


class Server:
    """An archive's serving component — switchable for act 2."""

    def __init__(self, cid, why_node):
        self.id, self.why_node = cid, why_node
        self.on = True

    def bid(self, ctx):
        if not self.on:
            return
        yield AttentionBid(
            src=self.id, label=f"{self.id}:serve",
            urgency=0.6, justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        return Outcome(True, "served the archive")


class NoteTaker:
    """A's local work — so A is an organism, not a shell."""

    id, why_node = "A.notes", "why:notes"

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label="A.notes:write",
            urgency=0.5, justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        return Outcome(True, "wrote notes")


def archive(name):
    rt = Runtime(seed=11, idle_window=999)
    rt.declare_why(f"the {name} archive exists", node_id="why:root")
    rt.declare_why("serve the archive", parent="why:root", node_id="why:serve")
    rt.register(Server(f"{name}.server", "why:serve"))
    return rt


# --- the organisms -------------------------------------------------------
a = Runtime(seed=5, idle_window=999, attestation_horizon=HORIZON)
a.declare_why("do good research", node_id="why:root")
a.declare_why("keep the shared index fresh", parent="why:root", node_id="why:index")
a.declare_why("write up what I learn", parent="why:root", node_id="why:notes")
a.register(NoteTaker())
b, c = archive("B"), archive("C")

soc = Society(name="the archives")
soc.join(a, name="A")
soc.join(b, name="B")
soc.join(c, name="C")

print(f"attestation horizon: {HORIZON} ticks — delegation is a subscription\n")


def beat(tick, note=""):
    node = a.why.node("why:index")
    prov = node.last_attested_by or "never served"
    print(f"{tick:>5}  just={a.why.justification('why:index'):.3f}  "
          f"state={node.state.value:<7} served_by={prov:<10}  {note}")


# --- ACT 1: the treaty works ---------------------------------------------
t1 = soc.establish_treaty(
    provider="B", provider_node="why:serve",
    beneficiary="A", beneficiary_node="why:index",
    statement="A's index freshness is served by B's archive", tick=0)
print(f"ACT 1  treaty {t1.id} established: A's index <-- B's archive (sole basis)")
soc.run(60)
beat(60, "60 ticks of service — all of it on A's books, provenance treaty:1")

# --- ACT 2: neglect — the soft path --------------------------------------
b.component("B.server").on = False
print("\nACT 2  B goes quiet (its purpose stays ALIVE; nobody died)")
soc.run(60)
beat(120, "A's stamps stopped at 60 — freshness decaying on A's own books")
soc.run(60)
beat(180, "A's OWN reaper lapsed the node: doubtful, not broken")
assert a.why.node("why:index").state is WhyState.UNKNOWN
rec = [r for r in a.why.necrology() if r.node_id == "why:index"][-1]
print(f"       receipt on A's books: {rec.reason}")
assert soc.treaties()[0].status == BROKEN

# --- ACT 3: death — the hard path ----------------------------------------
a.why.revive("why:index", "the index matters; try the second archive", tick=181)
t2 = soc.establish_treaty(
    provider="C", provider_node="why:serve",
    beneficiary="A", beneficiary_node="why:index",
    statement="A's index freshness is served by C's archive", tick=181)
print(f"\nACT 3  revived on parole; treaty {t2.id} with C established")
soc.run(15)
beat(196, "C serves — parole ended by genuine service, fresh again")
assert a.why.justification("why:index") == 1.0

c.why.kill("why:serve", "the C archive shut down", tick=197)
soc.step()
beat(197, "C's provider purpose KILLED -> the exchange questions A's node")
assert a.why.node("why:index").state is WhyState.UNKNOWN
rec = [r for r in a.why.necrology() if r.node_id == "why:index"][-1]
print(f"       receipt on A's books: {rec.reason}")
assert t2.status == BROKEN and "shut down" in t2.broken_reason

# --- ACT 4: the audits ---------------------------------------------------
print("\nACT 4  the audits")
for name, rt in soc.members().items():
    r = ConservationAuditor().verify(rt.why)
    print(f"  {name}: {r.summary()}")
    assert r.ok
fr = soc.audit()
print(f"  {fr.summary()}")
assert fr.ok

print("\n--- the treaty ledger (append-only: broken is forever) ---")
for t in soc.treaties():
    print(f"  {t.id}: {t.status:<7} {t.statement}")
    if t.status != ACTIVE:
        print(f"       broken at tick {t.broken_at}: {t.broken_reason}")

print("\nlesson 1: service routes; the beneficiary's own economics enforces.")
print("lesson 2: neglect is soft (your own reaper), death is hard (a receipt).")
print("lesson 3: a delegation leaves fingerprints on BOTH organisms' books.")
