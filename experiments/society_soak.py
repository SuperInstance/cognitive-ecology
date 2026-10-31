"""The society soak — two organisms, treaties, everything, for a long time.

Everything v0.4 built, running together under pressure:

* WHY-DAG purposes (a jointly-justified purpose with two parents)
* society-basis treaties (A's shared-index purpose served by B)
* the exchange: service routed, hard propagation on provider death,
  soft strangulation on neglect
* journal compaction (both books, every epoch)
* the conservation auditor on BOTH organisms + the federation auditor
* re-attestation economics, archival, market contention per organism

The story arc: B serves A's delegated purpose for a third of the run;
B's provider purpose is then killed (hard propagation: treaty breaks,
A's purpose questioned with a receipt); A revives, re-delegates to a
second archive C, which serves until the end. Every epoch: compact
both journals, verify both books, audit the federation.

Receipts: throughput, both organisms' log growth (bounded journals!),
treaty ledger, exchange events, federation receipts, save/load.

    python experiments/society_soak.py --ticks 6000
    python experiments/society_soak.py --ticks 1200   # quicker smoke
"""
from __future__ import annotations

import argparse
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cognitive_ecology import (  # noqa: E402
    AttentionBid, ConservationAuditor, Outcome, Runtime, Society, WhyState,
)
from cognitive_ecology.compaction import JournalCompactor  # noqa: E402


class Server:
    """An archive's serving component — the provider side of a treaty."""

    def __init__(self, cid, why_node, rng, true_rate=0.9):
        self.id, self.why_node = cid, why_node
        self.true_rate, self._rng = true_rate, rng
        self.serving = True

    def bid(self, ctx):
        if not self.serving:
            return
        jitter = 0.7 + 0.6 * self._rng.random()
        yield AttentionBid(
            src=self.id, label=f"{self.id}:serve",
            urgency=min(1.0, 0.85 * jitter),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0)

    def act(self, ctx, label):
        return Outcome(self._rng.random() < self.true_rate, "served")


class Worker:
    """Each organism's local work — so every member is a real organism."""

    def __init__(self, cid, why_node, rng, true_rate=0.8):
        self.id, self.why_node = cid, why_node
        self.true_rate, self._rng = true_rate, rng

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label=f"{self.id}:work",
            urgency=min(1.0, 0.6 + 0.4 * self._rng.random()),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0)

    def act(self, ctx, label):
        return Outcome(self._rng.random() < self.true_rate, "worked")


def build_organism(name, seed, horizon, with_dag=True):
    rt = Runtime(seed=seed, top_k=2, idle_window=999,
                 attestation_horizon=horizon)
    rt.tensions.add("energy", growth=0.04)
    rt.declare_why(f"{name} persists", node_id="why:root")
    rt.declare_why("mind my own work", parent="why:root", node_id="why:work")
    rt.register(Worker(f"{name}.worker", "why:work", random.Random(seed + 7)))
    if with_dag:
        # a jointly-justified purpose: two parents, best-path semantics
        rt.declare_why("curiosity", node_id="why:curio")
        rt.declare_why("explore jointly", parents=("why:root", "why:curio"),
                       node_id="why:joint")
        rt.register(Worker(f"{name}.explorer", "why:joint",
                           random.Random(seed + 8), true_rate=0.7))
    return rt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--horizon", type=int, default=400)
    ap.add_argument("--epoch", type=int, default=500)
    ap.add_argument("--compact", action="store_true", default=True)
    args = ap.parse_args()

    # --- the society: A (researcher) leans on B then C (archives) -----
    a = build_organism("A", args.seed, args.horizon)
    a.declare_why("keep the shared index fresh", parent="why:root",
                  node_id="why:index")  # delegated, never locally served
    b = build_organism("B", args.seed + 1, args.horizon, with_dag=False)
    b.declare_why("serve the archive", parent="why:root", node_id="why:serve")
    b.register(Server("B.server", "why:serve", random.Random(args.seed + 9)))
    c = build_organism("C", args.seed + 2, args.horizon, with_dag=False)
    c.declare_why("serve the second archive", parent="why:root",
                  node_id="why:serve")
    c.register(Server("C.server", "why:serve", random.Random(args.seed + 10)))
    # C runs its own archive from the start (a standby archive still
    # maintains its own purpose); A simply has no treaty with it yet

    soc = Society(name="the archives")
    soc.join(a, name="A")
    soc.join(b, name="B")
    soc.join(c, name="C")
    t1 = soc.establish_treaty(
        "B", "why:serve", "A", "why:index",
        "A's index freshness is served by B's archive", tick=0)

    kill_at = args.ticks // 3
    redelegate_at = kill_at + args.horizon // 2
    print(f"society soak: {args.ticks} ticks, horizon {args.horizon}, "
          f"epoch {args.epoch}; B dies at {kill_at}, "
          f"A re-delegates to C at ~{redelegate_at}")

    started = time.monotonic()
    epoch_receipts = []
    fed_audits = 0
    for tick in range(1, args.ticks + 1):
        if tick == kill_at:
            b.why.kill("why:serve", "the B archive closed", tick=tick)
        if tick == redelegate_at and a.why.node("why:index").state is WhyState.UNKNOWN:
            a.why.revive("why:index", "the index matters; try archive C",
                         tick=tick)
            soc.establish_treaty(
                "C", "why:serve", "A", "why:index",
                "A's index freshness is served by C's archive", tick=tick)
        soc.step()
        if tick % args.epoch == 0:
            if args.compact:
                JournalCompactor(a.why).compact()
                for m in (b, c):
                    JournalCompactor(m.why).compact()
            r_a = ConservationAuditor().verify(a.why)
            r_b = ConservationAuditor().verify(b.why)
            r_c = ConservationAuditor().verify(c.why)
            assert r_a.ok and r_b.ok and r_c.ok, \
                f"conservation failed at tick {tick}"
            fr = soc.audit()
            assert fr.ok, f"federation failed at tick {tick}: {fr.summary()}"
            fed_audits += 1
            epoch_receipts.append(
                (tick, len(a.why.journal()), len(b.why.journal()),
                 len(c.why.journal())))
    wall = time.monotonic() - started

    # --- receipts ----------------------------------------------------------
    print(f"\n--- society soak receipts (seed {args.seed}) ---")
    print(f"ticks          : {args.ticks} in {wall:.1f}s "
          f"({args.ticks / wall:,.0f} ticks/s, lockstep, 3 organisms)")
    print(f"epoch audits   : {fed_audits} federation + "
          f"{fed_audits * 3} conservation, all green")
    if epoch_receipts:
        print("journal sizes  : "
              + " ".join(f"{t}:A{ja}/B{jb}/C{jc}"
                         for t, ja, jb, jc in epoch_receipts[-4:]))
    print(f"events         : A {len(a.bus)} / B {len(b.bus)} / C {len(c.bus)}")
    print(f"necrology      : A {len(a.why.necrology())} / "
          f"B {len(b.why.necrology())} / C {len(c.why.necrology())}")
    ca = a.why.conservation()
    print(f"A conservation : alive={ca['alive']} dead={ca['dead']} "
          f"unknown={ca['unknown']} ever={ca['ever_declared']} "
          f"invariant_ok={ca['invariant_ok']}")
    print("\ntreaty ledger (append-only):")
    for t in soc.treaties():
        print(f"  {t.id}: {t.status:<7} {t.statement}")
        if t.status != "active":
            print(f"    broken at {t.broken_at}: {t.broken_reason[:90]}")
    q = [r for r in a.why.necrology() if r.node_id == "why:index"]
    print("\nA's delegated purpose history (the receipts):")
    for r in q:
        print(f"  tick {r.tick:>5}: {r.from_state.value} -> "
              f"{r.to_state.value} ({r.reason[:80]})")

    # final receipts + save/load round-trip
    r_final = ConservationAuditor().verify(a.why)
    fr_final = soc.audit()
    assert r_final.ok and fr_final.ok
    print(f"\nfinal verify   : A {r_final.summary()}")
    print(f"federation     : {fr_final.summary()}")
    with tempfile.TemporaryDirectory() as td:
        a.save(td)
        import json, os
        with open(os.path.join(td, "state.json")) as f:
            state = json.load(f)
        assert state["conservation_receipt"]["ok"]
        print(f"save/load      : state.json "
              f"{os.path.getsize(os.path.join(td, 'state.json')) // 1024} KiB, "
              f"receipt embedded ok")

    print("\nSOCIETY SOAK PASSED: every invariant held across the whole run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
