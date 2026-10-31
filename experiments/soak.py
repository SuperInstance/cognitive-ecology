"""The soak test — one organism, ten thousand ticks, every invariant.

Everything v0.3 built, running together under pressure:

* re-attestation economics (horizon on: serving, decaying, lapsing)
* probation on revival (a component that resurrects its purpose pays parole)
* the conservation auditor (full replay verification every N ticks)
* honest archival (periodic sweeps of ancient dead subtrees)
* the attention market with contention (more bidders than slots)

Receipts: tick throughput, log growth (events / necrology / journal),
hot-vs-cold tree sizes, lapse/revive counts, market stats, calibration,
verify() latency at the end, save/load round-trip + re-verify.

    python experiments/soak.py --ticks 10000
    python experiments/soak.py --ticks 2000 --seed 3   # quicker smoke
"""
from __future__ import annotations

import argparse
import random
import sys
import tempfile
import time

from cognitive_ecology import (
    AttentionBid, ColdStorage, ConservationAuditor, Outcome, Runtime,
    WhyState,
)

PROFILES = [
    # (id, urgency, success_p, true_rate, serves_forever)
    ("forager", 0.90, 0.90, 0.90, True),
    ("scout", 0.80, 0.90, 0.45, True),      # overconfident: calibration bait
    ("archivist", 0.75, 0.40, 0.40, True),  # humble
    ("wanderer", 0.70, 0.60, 0.60, True),
    ("idler", 0.85, 0.70, 0.70, False),     # stops serving -> purpose lapses
]


class SoakWorker:
    def __init__(self, cid, why_node, urgency, success_p, true_rate, rng):
        self.id = cid
        self.why_node = why_node
        self.urgency = urgency
        self.success_p = success_p
        self.true_rate = true_rate
        self._rng = rng
        self.serving = True

    def bid(self, ctx):
        if not self.serving:
            return
        jitter = 0.75 + 0.5 * self._rng.random()
        yield AttentionBid(
            src=self.id, label=f"{self.id}:work",
            urgency=min(1.0, self.urgency * jitter),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
            success_p=self.success_p,
        )

    def act(self, ctx, label):
        ok = self._rng.random() < self.true_rate
        if ok:
            ctx.tensions.relieve("energy", 0.08)
        return Outcome(ok, "ok" if ok else "missed")


def main() -> int:
    ap = argparse.ArgumentParser(description="the soak test")
    ap.add_argument("--ticks", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--horizon", type=int, default=300)
    ap.add_argument("--verify-every", type=int, default=1_000)
    ap.add_argument("--sweep-every", type=int, default=1_000)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rt = Runtime(seed=args.seed, top_k=3, attestation_horizon=args.horizon)
    rt.tensions.add("energy", growth=0.02)
    rt.tensions.add("curiosity", growth=0.01)
    rt.declare_why("stay alive", node_id="why:root")
    workers = {}
    for cid, urgency, p, rate, serves in PROFILES:
        rt.declare_why(f"be the {cid}", parent="why:root", node_id=f"why:{cid}")
        w = SoakWorker(cid, f"why:{cid}", urgency, p, rate,
                       random.Random(hash((cid, args.seed)) % 2**31))
        w.serving = serves
        rt.register(w)
        workers[cid] = w

    # a pruner kills a random stale purpose occasionally; an expander
    # declares new ones — the tree grows and churns like a real organism
    kills = decls = lapses = revives = 0
    verify_failures = []
    t0 = time.monotonic()
    last_verify_ok = None
    next_verify = args.verify_every
    next_sweep = args.sweep_every
    next_idler_stop = args.ticks // 4

    for tick in range(1, args.ticks + 1):
        if tick % 500 == 0:
            nid = f"why:x{tick}"
            rt.declare_why(f"emergent purpose {tick}", parent="why:root",
                           node_id=nid, tick=tick)
            decls += 1
            # some emergent purposes die young and never get served
            if rng.random() < 0.7:
                rt.why.kill(nid, reason=f"emergent purpose {tick} abandoned",
                            tick=tick)
                kills += 1
        if tick == next_idler_stop:
            workers["idler"].serving = False  # its purpose will lapse
        if tick >= next_sweep:
            ColdStorage(rt.why, min_age=args.horizon * 2).sweep(now=tick)
            next_sweep += args.sweep_every
        r = rt.tick()
        lapses += len(r.lapsed)
        if not r.conservation_ok is None and r.conservation_ok is False:
            print(f"CONSERVATION FAILED AT TICK {tick}")
            return 1
        if tick >= next_verify:
            receipt = rt.audit()
            if not receipt.ok:
                verify_failures.append((tick, receipt.summary()))
            last_verify_ok = receipt.ok
            next_verify += args.verify_every
    wall = time.monotonic() - t0

    # one revival ceremony near the end: the idler's purpose returns
    idler_why = "why:idler"
    if rt.why.has(idler_why) and rt.why.node(idler_why).state is WhyState.UNKNOWN:
        rt.why.revive(idler_why, reason="the idler re-justifies its purpose",
                      tick=rt.tick_no)
        revives += 1

    c = rt.why.conservation()
    final = rt.audit()
    verify_ms = (time.monotonic() - t0)  # includes run; time verify alone:
    t1 = time.monotonic()
    final = rt.audit()
    verify_time = (time.monotonic() - t1) * 1000

    print(f"--- soak receipts ({args.ticks} ticks, seed {args.seed}) ---")
    print(f"throughput     : {args.ticks / wall:,.0f} ticks/s ({wall:.1f}s)")
    print(f"events         : {len(rt.bus):,}")
    print(f"necrology      : {len(rt.why.necrology()):,} records")
    print(f"journal        : {len(rt.why.journal()):,} stamps")
    print(f"hot tree       : {len(rt.why.nodes()):,} nodes "
          f"(alive={c['alive']} dead={c['dead']} unknown={c['unknown']})")
    print(f"cold storage   : {c['archived']:,} nodes")
    print(f"ever declared  : {c['ever_declared']:,} "
          f"invariant_ok={c['invariant_ok']}")
    print(f"lapses         : {lapses:,}   revives: {revives}   "
          f"kills: {kills}   declared-mid-run: {decls}")
    print(f"verify (final) : {verify_time:.0f} ms, ok={final.ok}")
    print(f"verify checks  : {final.checks}")
    print(f"market         : {rt.market.stats()}")
    print(f"calibration    : {rt.calibration.verdict()}")
    m = ColdStorage(rt.why, min_age=args.horizon * 2).manifest()
    print(f"manifest rows  : {len(m)}")
    if verify_failures:
        print(f"VERIFY FAILURES: {verify_failures[:3]}")
        return 1

    # persistence round-trip under load, then re-verify from disk
    with tempfile.TemporaryDirectory() as d:
        rt.save(d)
        import json
        import os
        size = os.path.getsize(os.path.join(d, "state.json"))
        rt2 = Runtime.load(d, attach=lambda r: None)
        reverify = rt2.audit()
    print(f"save/load      : state.json {size / 1024:.0f} KiB; "
          f"re-verified from disk: ok={reverify.ok}")

    assert c["invariant_ok"], "conservation broke"
    assert final.ok and reverify.ok, "auditor failed"
    assert c["archived"] > 0, "expected archival to engage"
    assert lapses > 0, "expected lapses under an idler"
    print("\nSOAK PASSED: every invariant held across the whole run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
