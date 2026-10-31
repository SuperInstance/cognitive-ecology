# Example 08 — The Society (purpose that crosses organisms)

**What this teaches:** v0.4's society-basis federation (ADR-0011).
Until now, an organism's purpose basis was entirely local. The moment
two organisms exist, a new kind of purpose appears — **delegated
purpose**: A's purpose whose service happens inside B. This example
runs three organisms (a researcher, two archives) and watches the
whole life of a delegation:

- **ACT 1 — the treaty works.** A delegates its "keep the shared index
  fresh" purpose to B's archive via a sole treaty. B serves every tick,
  and the exchange re-stamps A's chain **on A's own books** with
  provenance `treaty:1` — A never runs a component under that purpose,
  yet its justification holds at 1.000.
- **ACT 2 — neglect, the soft path.** B goes quiet (its archive
  purpose stays ALIVE — nobody died, no event fires). A's stamps simply
  stop. A's own freshness economics strangles the delegation (watch
  justification decay), and A's OWN reaper lapses it at the audit
  sweep. The receipt on A's books is a lapse record — doubt that grew
  at home.
- **ACT 3 — death, the hard path.** A revives (recorded, on parole),
  establishes a new treaty with archive C, and C serves — parole ends
  by genuine service. Then C's provider purpose is KILLED: in the same
  step, the exchange breaks the treaty and QUESTIONS A's node, with a
  receipt naming the treaty, the cause, and the doubter.
- **ACT 4 — the audits.** Every member's conservation receipt replays
  (genesis + necrology + journal, bit for bit); the federation receipt
  checks that the books AGREE (no active treaty on a dead endpoint,
  every treaty-provenance stamp derivable from the provider's journal,
  break receipts present); and the treaty ledger shows the append-only
  history — broken is forever.

**Run it:**

```bash
python examples/08_society/main.py
```

No API keys. No network. No dependencies beyond the kernel.

**What this play-test found (and fixed):** the first run exposed a
real cross-layer bug — the conservation auditor's replay ordered
same-tick entries as stamps-before-transitions, which cannot express
"revive at tick *t*, then a treaty-routed stamp lands at the same
tick *t*." The replay now uses three phases at equal ticks
(to-ALIVE transitions → stamps → other transitions), pinned by
`test_same_tick_revive_then_routed_stamp_replays`.
