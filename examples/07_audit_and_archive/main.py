"""The proof-carrying organism: audit the books, tamper with history, fail.

v0.3 turns "nothing was deleted" from a claim into a checkable receipt:
the genesis block + the necrology + the attestation journal replay to
exactly the living tree — or the receipt names the lie. Then ancient
dead purposes move to cold storage without deleting anything, and come
back through a recorded two-act ceremony.

You will: print a valid receipt, flip a state off the books (caught),
rewrite history (caught by the hash chain), sweep a dead subtree into
cold storage (books stay balanced), and restore it (still DEAD, reason
recorded — resurrection is a separate act).

Zero LLM calls. Zero keys.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    ColdStorage, ConservationAuditor, Runtime, WhyState,
)

rt = Runtime(seed=7, top_k=1)
rt.declare_why("stay alive", node_id="why:root")
rt.declare_why("do the daily work", parent="why:root", node_id="why:work")
rt.declare_why("an old mission", parent="why:root", node_id="why:old")
rt.declare_why("its old subtask", parent="why:old", node_id="why:oldsub")
rt.why.stamp_chain("why:work", tick=5, by="worker")
rt.why.stamp_chain("why:work", tick=10, by="worker")
rt.why.kill("why:old", reason="mission closed in 2019", tick=12)  # cascade
rt.why.now = 5000  # eons pass

auditor = ConservationAuditor()

print("1) a healthy organism carries a valid receipt")
r = auditor.verify(rt.why)
print("  ", r.summary())
assert r.ok

print("\n2) flipping a state off the books is caught")
rt.why.node("why:oldsub").state = WhyState.ALIVE  # never went through the log
r = auditor.verify(rt.why)
print("  ", r.summary())
assert not r.ok and r.checks["state_equivalence"] is False
rt.why.node("why:oldsub").state = WhyState.UNKNOWN  # put it back

print("\n3) rewriting history breaks the chain head")
chain_before = auditor.chain(rt.why.necrology(), rt.why.journal())
rt.why._necrology[0].reason  # noqa: B018 - reading the record we will forge
import dataclasses  # noqa: E402
forged = dataclasses.replace(rt.why._necrology[0], reason="mission closed politely")
rt.why._necrology[0] = forged
chain_after = auditor.chain(rt.why.necrology(), rt.why.journal())
print(f"   chain before: {chain_before[:24]}...")
print(f"   chain after : {chain_after[:24]}...  "
      f"({'BROKEN' if chain_before != chain_after else 'unchanged?!'})")
assert chain_before != chain_after
# restore the true record
rt.why._necrology[0] = dataclasses.replace(forged, reason="mission closed in 2019")
assert auditor.verify(rt.why).ok

print("\n4) ancient dead subtrees go to cold storage — books stay balanced")
cs = ColdStorage(rt.why, min_age=1000)
archived = cs.sweep()
print(f"   archived: {archived}   ({cs.summary()})")
c = rt.why.conservation()
print(f"   hot {len(rt.why.nodes())} + cold {c['archived']} == "
      f"ever {c['ever_declared']}  invariant_ok={c['invariant_ok']}")
assert c["invariant_ok"]
assert auditor.verify(rt.why).ok  # cold nodes verify against the manifest

print("\n5) restoration is a recorded two-act ceremony")
cs.restore("why:old", reason="the mission became relevant again", tick=5001)
print("   act 1: restored — still DEAD, reason in the necrology")
print("         ", [x.reason for x in rt.why.necrology()
                    if "restored from cold storage" in x.reason][0])
rt.why.resurrect("why:old", "new evidence for the old mission", tick=5002)
print("   act 2: resurrected — ALIVE, on parole "
      f"(justification {rt.why.justification('why:old'):.2f}, capped at 0.5)")
assert rt.why.node("why:old").probation is True
assert rt.why.justification("why:old") <= 0.5

r = auditor.verify(rt.why)
print("\n6) the whole story replays to the living tree")
print("  ", r.summary())
assert r.ok
print("\nconservation is not a claim. it is a receipt.")
