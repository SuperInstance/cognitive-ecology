"""The soak test, pinned: every v0.3 invariant under one long run.

A shorter version of experiments/soak.py (which does 10k ticks with
receipts) — same organism shape, same invariants, fast enough for CI.
"""
import random

from cognitive_ecology import (
    AttentionBid, ColdStorage, Outcome, Runtime, WhyState,
)

PROFILES = [
    ("forager", 0.90, 0.90, 0.90, True),
    ("scout", 0.80, 0.90, 0.45, True),
    ("archivist", 0.75, 0.40, 0.40, True),
    ("idler", 0.85, 0.70, 0.70, False),  # stops serving -> its purpose lapses
]


class _SoakWorker:
    def __init__(self, cid, why_node, urgency, p, rate, rng):
        self.id, self.why_node = cid, why_node
        self.urgency, self.success_p, self.true_rate = urgency, p, rate
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
            ctx.tensions.relieve("energy", 0.1)
        return Outcome(ok, "ok" if ok else "missed")


TICKS = 1_500
HORIZON = 300


def test_soak_every_invariant_holds():
    rng = random.Random(7)
    rt = Runtime(seed=7, top_k=2, attestation_horizon=HORIZON)
    rt.tensions.add("energy", growth=0.02)
    rt.declare_why("stay alive", node_id="why:root")
    for cid, urgency, p, rate, serves in PROFILES:
        rt.declare_why(f"be the {cid}", parent="why:root", node_id=f"why:{cid}")
        w = _SoakWorker(cid, f"why:{cid}", urgency, p, rate,
                        random.Random(hash(cid) % 2**31))
        w.serving = serves
        rt.register(w)

    lapses = 0
    for tick in range(1, TICKS + 1):
        if tick == TICKS // 3:  # an emergent purpose that dies young
            rt.declare_why("emergent", parent="why:root",
                           node_id="why:emergent", tick=tick)
            rt.why.kill("why:emergent", reason="abandoned", tick=tick)
        if tick == TICKS // 2:
            rt._components["idler"].serving = False
        if tick % 400 == 0:
            ColdStorage(rt.why, min_age=HORIZON).sweep(now=tick)
        r = rt.tick()
        lapses += len(r.lapsed)
        assert r.conservation_ok is not False, f"conservation broke at {tick}"

    c = rt.why.conservation()
    receipt = rt.audit()
    assert receipt.ok, receipt.summary()
    assert c["invariant_ok"]
    assert c["archived"] > 0, "archival should have engaged"
    assert lapses > 0, "the idler's purpose should have lapsed"
    # the idler's revival ceremony works end-to-end
    if rt.why.node("why:idler").state is WhyState.UNKNOWN:
        rt.why.revive("why:idler", reason="re-justified after the pause",
                      tick=rt.tick_no)
        assert rt.why.justification("why:idler") <= 0.5  # parole
    # calibration was scored across the run
    assert len(rt.calibration) > 500
    assert rt.calibration.brier() is not None


def test_soak_is_deterministic():
    """Same seed, same organism, same receipts — bit for bit."""
    def run(seed):
        rt = Runtime(seed=seed, top_k=2, attestation_horizon=HORIZON)
        rt.tensions.add("energy", growth=0.02)
        rt.declare_why("stay alive", node_id="why:root")
        for cid, urgency, p, rate, serves in PROFILES:
            rt.declare_why(f"be the {cid}", parent="why:root",
                           node_id=f"why:{cid}")
            w = _SoakWorker(cid, f"why:{cid}", urgency, p, rate,
                            random.Random(hash(cid) % 2**31))
            w.serving = serves
            rt.register(w)
        rt._components["idler"].serving = False
        rt.run(300)
        return rt.audit()

    r1, r2 = run(11), run(11)
    assert r1.ok and r2.ok
    assert r1.live_digest == r2.live_digest
    assert r1.chain_head == r2.chain_head
    assert r1.transition_records == r2.transition_records
