"""cognitive-ecology — a Python kernel for agents that persist like organisms.

Zero dependencies. Zero LLM calls required to run the kernel.

Layer map (each layer is one module):
  L0 runtime.py        the process, not the agent — ticks, never calls a model
  L1 events.py         MIDI-style immutable events (~100 bytes), causal chains
  L2 graph.py          the World Graph — anti-RAG knowledge with biography
  L3 memory.py         events consolidate into the graph (Hebbian, decay)
  L4 scripts.py        Script Ecology — agents are populations of small scripts
  L5 attention.py      Attention Market + executive.py the arbiter
  L6 why.py            WHY — purpose, conserved forever (the crown)
  L7 identity.py       the slowly-drifting self-model
  L8 sleep.py          offline consolidation: replay, prune, dream

Cross-cutting: tension.py (homeostatic drives), simulations.py
(counterfactual rollouts), agents/ (LLMs and decision models as citizens).
"""
from .why import NecroRecord, WhyNode, WhyState, WhyTree, WhyVerdict
from .events import Event, EventBus, EventKind
from .graph import GEdge, GNode, WalkResult, WorldGraph
from .memory import Memory
from .attention import FACTORS, AttentionBid, AttentionMarket, ClearResult
from .tension import Tension, TensionField
from .scripts import Outcome, Script, ScriptEcology
from .executive import Decision, Executive
from .simulations import Forecast, Simulator
from .identity import Commitment, Identity
from .sleep import SleepCycle, SleepStats
from .runtime import Component, Runtime, TickReport, WorldSnapshot

__version__ = "0.2.0"

__all__ = [
    "AttentionBid", "AttentionMarket", "ClearResult", "Commitment", "Component",
    "Decision", "Event", "EventBus", "EventKind", "Executive", "FACTORS",
    "Forecast", "GEdge", "GNode", "Identity", "Memory", "NecroRecord",
    "Outcome", "Runtime", "Script", "ScriptEcology", "Simulator", "SleepCycle",
    "SleepStats", "Tension", "TensionField", "TickReport", "WalkResult",
    "WhyNode", "WhyState", "WhyTree", "WhyVerdict", "WorldGraph",
    "WorldSnapshot",
]
