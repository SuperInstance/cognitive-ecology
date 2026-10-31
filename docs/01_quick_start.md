# Quick Start

From zero to a living organism in five minutes. No API keys, no LLM, no
network — the kernel is fully functional without any model.

## 1. Install

```bash
git clone <your-fork-url> cognitive-ecology
cd cognitive-ecology
pip install -e ".[dev]"      # zero runtime dependencies; dev = pytest only
```

Python 3.10+. Nothing else. (There is no `requirements.txt` because there
are no requirements.)

## 2. The 60-second organism

```python
from cognitive_ecology import Runtime, Script, Outcome

rt = Runtime(seed=7, top_k=1)                      # L0: a body, 1 action/tick
rt.declare_why("understand why I run", node_id="why:root")   # L6: purpose
rt.tensions.add("curiosity", growth=0.05)                    # drives

def _observe(ctx):                  # the action: look, ease the drive
    if ctx.tensions.level("curiosity") > 0.3:   # only when it has built up
        ctx.tensions.relieve("curiosity", 0.4)
    return Outcome(True, "looked")

rt.ecology.spawn(Script(                                     # L4: a behavior
    name="observe", why_node="why:root", owner="tiny",
    relieves=("curiosity",),
    act=_observe,
), tick=0)

class Tiny:                                    # a component relays its scripts
    id, why_node = "tiny", "why:root"
    def bid(self, ctx):  return ctx.ecology.bids(ctx, owner="tiny")
    def act(self, ctx, label): return ctx.ecology.fire(label, ctx)

rt.register(Tiny())               # a plain instance — no constructor args
for report in rt.run(10):
    print(report.tick, report.ran, report.tensions)
```

Every tick the runtime asks `why_should_this_run()`; the script bids for
attention (`urgency × justification × opportunity × novelty ×
expected_value`); the market clears the winner; memory consolidates the
tick's events into the world graph.

Watch `report.tensions`: curiosity rises, `observe` eases it, and the
level *oscillates* instead of climbing — that is homeostasis. A drive
pinned at 0 or at 1 is a diagnosis, not a design (see
[07_playbook.md](07_playbook.md)).

## 3. The ten-minute tour (recommended next)

```bash
python experiments/minimal_world.py
```

This runs the full story: life under the attention market → the root WHY
is killed (nothing runs, nothing is deleted) → resurrection → sleep with
dreams → save to disk → load into a fresh process and keep living. Read
`experiments/minimal_world.py` afterwards; it is the annotated tour.

## 4. Add an LLM citizen (optional)

```bash
export DEEPINFRA_API_KEY=...        # env-only. never a file, never a commit
python examples/02_research_assistant/main.py
```

The model joins as a *citizen*: it proposes parameterized scripts from a
safe action library; the WHY tree decides what may exist, the attention
market decides what runs. Prompt calls run under a stable-prefix cache
session that measures cached tokens and estimated savings
(cached input on `tencent/Hy4-preview` bills at ~1/20th of fresh input).

## Where to go next

| If you want to... | Read |
|---|---|
| understand the layer stack and design decisions | [02_architecture.md](02_architecture.md) |
| look up one layer's exact API | [03_layers_reference.md](03_layers_reference.md) |
| understand the WHY conservation law deeply | [04_why_conservation.md](04_why_conservation.md) |
| tune agent behavior | [05_attention_economics.md](05_attention_economics.md) |
| wire up LLMs / prompt caching | [06_agents_and_providers.md](06_agents_and_providers.md) |
| use decision models (typesafe.ai-style) | [08_decision_models.md](08_decision_models.md) |
| run your own play-tests | [07_playbook.md](07_playbook.md) + [templates/scenario_template.md](../templates/scenario_template.md) |
| build something now | [tutorials/](tutorials/) — four hands-on tutorials |
| browse runnable examples | [examples/](../examples/) — eight organisms, all keyless-runnable |
