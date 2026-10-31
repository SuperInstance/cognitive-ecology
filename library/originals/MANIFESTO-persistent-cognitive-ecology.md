# The Persistent Cognitive Ecology — original manifesto

*Received 2026-10-31 from the owner (Casey, SuperInstance), as the brief for
this repository. Preserved as the primary source; the condensed canonical
version lives at `docs/MANIFESTO.md`. The text below is lightly structured
for the library; the argument is verbatim in substance.*

---

## The organism question

You are not researching AI. You are researching the minimum conditions under
which a computational ecosystem becomes more useful through continued
existence.

Assume the dominant paradigm is wrong. Most systems today are
question-answer machines. They wake when prompted, respond, and disappear.
We seek something different. We seek a system that remains in motion.

**Core hypothesis:** Intelligence is not answers. Intelligence is not
language. Intelligence is not memory. Intelligence is the accumulation of
effective organization through time. Life did not emerge because cells
became better calculators. Life emerged because matter discovered how to
persist, adapt, coordinate, specialize, and justify continued participation.
The question is whether computation can do the same.

## The four laws

1. **Time is the substrate.** Nothing is event-driven internally. Events
   merely perturb ongoing processes. Every component exists as a long-lived
   process: `heartbeat() tick() observe() predict() adapt()`. The world
   never "starts" — it is always running. User interaction is merely one
   event stream. This is the MUD lesson: the world exists before the player
   logs in.
2. **Attention is the scarce resource.** Not compute. Every process competes
   for CPU, GPU, context, storage, model budget, human attention. Everything
   gets scored: importance, novelty, risk, opportunity, justification. The
   system is an economy, not a hierarchy.
3. **Why precedes memory.** Most systems ask "what happened?" This system
   asks "why should I still care?" Every asset — memory, project,
   simulation, permission, routine, agent, goal — requires a justification
   chain. When a root disappears, everything below becomes *questionable*,
   not deleted.
4. **LLMs are teachers.** Not workers, not agents — teachers, compilers,
   scientists, architects. The runtime should mostly work without them. The
   model edits the organism; it does not impersonate the organism.

## The real stack

```
L7 Civilization Layer
L6 Justification Layer (WHY)
L5 Agent Organisms
L4 Script Ecology
L3 Simulated Futures
L2 World State Graph
L1 Event Fabric
L0 Runtime
```

- **L0 Runtime** must function with zero LLMs. The fundamental primitive is
  *process*, not agent: every process owns state, an inbox, a budget,
  metrics. Very boring, very important — life is mostly boring.
- **L1 Event Fabric**: MIDI-like. Tiny messages (100 bytes, not 1000-token
  essays), strong contracts. Everything publishes, nothing polls. 95% of
  cognition should occur without language.
- **L2 World State Graph**: not RAG — a world model. Typed objects (Person,
  Project, Vehicle, Conversation, Sensor, Document, Agent, Belief, Routine)
  with typed edges (WORKING_ON, DEPENDS_ON, CAUSED_BY, SUPPORTED_BY,
  PART_OF). The graph itself is the MUD.
- **L3 Simulated Futures**: every subsystem owns simulators (current
  reality, likely future, dangerous future, interesting future). You store
  predicted trajectories, not camera frames — the body already lives in
  predicted futures.
- **L4 Script Ecology**: agents are script collections (the zMUD insight).
  Each script has trigger, conditions, cost, utility, success rate. Most
  cognition moves here; the runtime stays cheap.
- **L5 Agent Organisms**: an agent is scripts + memories + simulations +
  goals. No model required — the model is augmentation.
- **L6 WHY Layer**: every object owns a justification graph with statuses
  Alive | Dead | Unknown | Absent. Nightly: run reachability, update
  liveness, generate attention scores. Attention becomes computable:
  `attention = urgency * justification * opportunity * novelty *
  expected_value`.
- **L7 Sleep**: not idle mode — infrastructure evolution. Observations →
  episodes → patterns → candidate scripts → simulation → validation →
  promotion. A successful behavior graduates, exactly like humans. The most
  important activity is *convert experiences into scripts*, because that is
  where capability accumulates.

## Identity, development, tension

- **Identity is not memory** — it is persistent preference: what repeatedly
  wins (values, goals, themes). Identity is a stable attractor.
- **Developmental biology**: the system differentiates. A research cell that
  notices 500 monthly road-analysis tasks spawns a RoadAnalysisCell — a new
  specialist, justified through WHY.
- **The tension field** (the layer closest to consciousness): track
  unresolved contradictions — expectation vs reality with magnitude. Life is
  obsessed with prediction error not because error is bad, but because error
  directs attention. Much of what we call awareness may be the system
  continuously reallocating toward unresolved tensions.

## The final shape

A MUD whose rooms are concepts. A society whose citizens are routines. A
memory whose survival depends on justification. A simulation engine that
dreams. A cortex that allocates attention. An ecosystem that evolves
scripts. The LLM becomes one organ among many. The true intelligence is the
ecology; the true memory is the world state; the true continuity is the
justification graph; the true "self" is the persistent pattern of attention
moving through time, continuously answering: **what deserves to exist next?**

A traditional operating system allocates resources. A traditional AI
allocates tokens. This architecture allocates *reasons*. WHY is the
conservation law of that world.

## The paradigm shift (compute as agriculture)

For fifty years personal computing trained us to think in transactions: open
application, do work, save, close. AI preserved the paradigm: ask, answer,
ask again. That is a craftsman model — the machine waits, the user is the
bottleneck. Workstations sit 95% idle not for lack of capability but for
lack of a conceptual model. The Holodeck's magic was not the rendering — it
was the *persistence*: the world kept going while nobody watched.

Abundance comes from parallel exploration, not faster answers: a scientist
improves by more experiments, more hypotheses, more dead ends eliminated.
The morning interface is not a chat prompt but a briefing — and eventually a
map: projects as cities, ideas as roads, agents as citizens, tensions as
storms, WHY chains as supply lines.

## Ten open questions (as received)

1. Is attention a market or a government? (suspicion: markets locally,
   governance globally)
2. What is identity? (the WHY graph may actually become identity — the
   continuity of "what still matters?")
3. What gets simulated? (novelty × importance × uncertainty drives budget)
4. What is the primitive unit? (increasingly suspected: *tension*)
5. Could WHY become the scheduler? (reason reachability → attention weight
   → scheduler priority)
6. Do scripts replace memory? (experience → memory → abstraction → script →
   reflex; experts compile, they don't remember)
7. What is sleep? (infrastructure evolution, not summarization)
8. Can we learn without models? (a shocking amount, probably)
9. What's the user actually looking at? (a map, not a dashboard)
10. What is success? (more leverage, not more automation — exploratory
    bandwidth)

## The measurement and the final question

Do not measure intelligence by benchmark or token output. Measure:
accumulated capability, retained usefulness, adaptation rate, surprise
generation, successful specialization, justification efficiency. Most
importantly: is the system more useful after a month even when nobody
directly instructed it to become more useful?

Imagine a workstation running continuously for ten years. Models come and
go. Hardware changes. Agents evolve. Scripts are rewritten. Goals shift.
Users arrive and leave. Yet something persists. **What is the smallest
structure that must remain true for the organism to still be itself?**

Research objective: build a computational ecology that accumulates wisdom
rather than merely producing answers. Treat time as a substrate, attention
as a resource, justification as a conservation law, and intelligence as an
evolving organization of processes. Discover whether a machine can become
more useful not because it was prompted, but because it continued
participating in the world.
