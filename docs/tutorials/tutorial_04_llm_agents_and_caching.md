# Tutorial 04 — LLM Agents and the Caching Game

*Goal: run a real model as a citizen of an ecology, and make iteration
cheap with prompt-cache economics. Time: ~30 minutes + an API key (a
MockProvider path exists for keyless runs). Builds on
[Tutorial 03](tutorial_03_attention_market.md).*

## The setup that makes an LLM a citizen

Three rules, all enforced by code rather than hope:

1. **The model proposes; the organism decides.** `LLMAgent` (in
   `agents/orchestrator.py`) submits a "propose" bid like any script.
   The WHY tree gates whether it may exist; the attention market gates
   whether it runs; its own accept-rate feeds its expected value.
2. **Proposals are typed and confined.** The model may only parameterize
   scripts from the fixed `ACTION_LIBRARY` (`observe`, `note`, `search`,
   `message`, `rest`). No `eval`, no arbitrary code. Invalid JSON is
   dropped silently — fail-soft, like everything here.
3. **The prompt has a frozen head.** Everything stable (identity,
   action library, output contract) is the system prompt, set once. The
   volatile world (tensions, digest, recent events, the ask) rides in
   the user message. This is the entire caching strategy.

## Step 1 — wire the agent

```python
# tutorial04.py
import os
from cognitive_ecology import Identity, Runtime
from cognitive_ecology.agents import (
    ACTION_LIBRARY_DOC, LLMAgent, MockProvider,
    OpenAICompatProvider, StablePrefixSession,
)

rt = Runtime(seed=3, top_k=2)
rt.declare_why("learn things and persist", node_id="why:root")
rt.tensions.add("curiosity", growth=0.05)
rt.identity = Identity("scout", why=rt.why)

PREFIX = (
    "You are scout, a citizen of a cognitive-ecology organism.\n"
    "## Action library\n" + ACTION_LIBRARY_DOC + "\n"
    "## Output contract\n"
    'Reply with a JSON array of 1-3 proposals: {"name": str, '
    '"action": str, "args": dict, "relieves": [str], "focus": [str], '
    '"when_hint": "always"|"tension_above:<name>:<x>"|"every:<n>"}'
)

provider = (OpenAICompatProvider.from_env("DEEPINFRA")
            if os.environ.get("DEEPINFRA_API_KEY") else MockProvider())
session = StablePrefixSession(provider, PREFIX,
                              journal_path="runs/tutorial04-journal.jsonl",
                              label="scout")
rt.register(LLMAgent("scout", "why:root", session, every=5))
rt.run(50)

for s in rt.ecology.alive():
    print(f"{s.name:28s} fires={s.fires:3d} success={s.success_rate:.2f}")
print(session.stats())
```

Run it twice: once keyless (MockProvider, deterministic), once with
`DEEPINFRA_API_KEY` set. The keyless run exercises the same pipeline —
proposals, spawning, market competition — with simulated caching.

## Step 2 — read what happened

With a real model you should see, roughly:

- the agent proposes every ~5 ticks (when its bid wins);
- proposals become live scripts (`BIRTH` events) that then compete for
  attention *against their own proposer* — the first genuinely
  surprising dynamic in LLM organisms (see below);
- spawned scripts fire, succeed or honestly fail (`search` on a charted
  topic fails: re-charting is not progress), and their EV moves;
- `session.stats()` reports `cache_hit_rate`, `cached_tokens`, and
  `est_saved_usd`.

## Step 3 — the economics (why the frozen head matters)

DeepInfra prices for `tencent/Hy4-preview` (checked 2026-10-31): input
$0.834/M tokens, **cached input $0.042/M**, output $2.501/M — cached
prefix tokens are ~20× cheaper, and caching is automatic for identical
prefixes (plus an optional session `prompt_cache_key`).

Your PREFIX is maybe 600–900 tokens. Small. Now scale the idea:

| Prefix size | 100 uncached iterations | 100 cached iterations | Saving |
|---|---|---|---|
| 900 tok | $0.075 | $0.004 | $0.071 |
| 6,000 tok | $0.50 | $0.025 | $0.475 |
| 50,000 tok | $4.17 | $0.21 | $3.96 |

The stable prefix is what lets you put a *large* identity + action
library + world charter in every call without paying for it every call.
The discipline that keeps the cache hitting:

- `Identity.introspect()` is memoized — mid-session commitments do NOT
  rewrite the prefix; `drift()` does, deliberately, between sessions.
- The world digest changes every tick — so it lives in the suffix, never
  the prefix.
- `StablePrefixSession.set_prefix(reason)` is the only sanctioned way to
  change the head, and every change is counted and journaled.

Run the tutorial twice in a row and diff `runs/tutorial04-journal.jsonl`:
the second run's first call should already report `cached_tokens` if it
came fast enough after the first (caches are time-limited at the
provider — the journal makes hit/miss visible instead of folkloric).

## Step 4 — the proposer starvation problem (learned by dogfooding)

Watch closely: after a few successful proposals, the spawned scripts'
success rates climb toward 1.0 — above the proposer's accept-rate. The
children outcompete their parent; the LLM proposes once and never again.
The market is *correctly* rewarding the doers over the talker.

The kernel's fix is homeostatic, not hierarchical: the proposer's urgency
includes a **staleness** term — an agent that hasn't proposed in ~30
ticks gets bored with its own repertoire (see `LLMAgent.bid`). That
single term turned "proposes once" into "proposes, watches its ideas
compete, re-proposes when they saturate" in the dogfood runs.

The general lesson for your own organisms: **organs that feed the market
need their own drives**, or the market will quietly retire them.

## Step 5 — what the model can and cannot do here

Can: propose new behaviors (within the library), set their triggers
(`when_hint` DSL), choose their focus and which tensions they relieve —
i.e., *compose an ecology*.

Cannot: execute code, edit the WHY tree, bypass the market, touch
another component's state, or persist anything without going through
events and the graph. When its WHY chain breaks, its scripts simply stop
bidding: the model keeps talking, the organism stops acting.

That last sentence is the constitutional arrangement of this whole
project, and you have now built it.

## Exercises

1. Add a new action to `ACTION_LIBRARY` (say, `defer` — park one of the
   agent's own scripts). One audited function; the model gains a verb.
2. Set `every=25` and watch proposer starvation arrive on schedule;
   then set the staleness divisor to 10 (in `LLMAgent.bid`) and watch
   the proposer get restless sooner.
3. Point `OpenAICompatProvider.from_env("TYPESAFE")` at a decision
   endpoint and replace the proposal turn with a *choice* among existing
   scripts (see `examples/03_decision_desk` and
   [08_decision_models.md](../08_decision_models.md)).
4. Prompt-cache forensics: deliberately put the tick number in the
   PREFIX and watch `cache_hit_rate` collapse to 0. Then put it back in
   the suffix where it belongs.

Next steps: [the playbook](../07_playbook.md) for running your own
play-tests, and [templates/scenario_template.md](../../templates/scenario_template.md)
for the eight seeded scenarios waiting to be built.
