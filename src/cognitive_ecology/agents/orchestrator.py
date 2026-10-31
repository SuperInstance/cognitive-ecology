"""The LLM as citizen: it proposes scripts, the ecology and market decide.

A conventional agent stack gives the model the throne: the prompt IS the
agent, and whatever the model says happens. Here the model is a resident
with proposal rights:

    LLM --proposes--> ScriptEcology --bids--> AttentionMarket --clears--> Executive

The LLM never executes anything. It emits PROPOSALS — small JSON objects
that parameterize scripts drawn from a FIXED ACTION LIBRARY. The library
is code the organism's author wrote and audited; the model can compose
within it but cannot escape it. No ``eval``, no generated code, no tool
surface beyond the typed actions. This is the safety boundary.

Proposal format (one JSON array):

    [
      {
        "name": "watch-cache-economics",
        "action": "search",                 # from the action library
        "args": {"topic": "cache economics"},
        "relieves": ["curiosity"],          # tension names it discharges
        "focus": ["topic:cache-economics"], # graph nodes it watches
        "when_hint": "always"               # 'always' | 'tension_above:<name>:<x>' | 'every:<n>'
      }
    ]

Invalid proposals are dropped (fail-soft), never retried blindly: the
agent's own accept-rate EMA feeds back into its attention bid, so an LLM
that proposes garbage eventually loses the market's ear.
"""
from __future__ import annotations

import math

import json
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from ..attention import AttentionBid
from ..events import EventKind
from ..scripts import Outcome, Script
from ..util import ema, slug, stable_hash


# ----------------------------------------------------------------------
# the safe action library — the LLM composes within it, never beyond it
# ----------------------------------------------------------------------
def _act_observe(ctx, args: dict) -> Outcome:
    focus = [str(x) for x in (args.get("focus") or [])][:8]
    if not focus:
        return Outcome(False, "observe needs args.focus=[node ids]")
    for nid in focus:
        if ctx.graph.has(nid):
            ctx.graph.seen([nid], tick=ctx.tick)
        else:
            ctx.graph.upsert(nid, "observed", {}, tick=ctx.tick)
        ctx.emit(EventKind.STATE, (nid, {"observed": 1}), src="agent")
    return Outcome(True, f"attended to {len(focus)} nodes")


def _act_note(ctx, args: dict) -> Outcome:
    text = str(args.get("text", "")).strip()
    if not text:
        return Outcome(False, "empty note")
    nid = f"note:{stable_hash(text)[:8]}"
    ctx.graph.upsert(nid, "note", {"text": text[:200]}, tick=ctx.tick)
    ctx.emit(EventKind.SIGNAL, ("journal", text[:200]), src="agent")
    return Outcome(True, f"noted {nid}")


def _act_search(ctx, args: dict) -> Outcome:
    topic = str(args.get("topic", "")).strip()
    if not topic:
        return Outcome(False, "empty topic")
    nid = f"topic:{slug(topic)}"
    existing = ctx.graph.get(nid)
    if existing is not None and existing.props.get("charted"):
        # Charting an already-charted topic is not progress: the script
        # succeeds once, then honestly fails, its expected-value falls,
        # and the market moves on. One-shot semantics keep the ecology
        # from clogging with eternally "successful" no-ops.
        return Outcome(False, f"{nid} already charted")
    ctx.graph.upsert(nid, "topic", {"label": topic[:80], "charted": 1}, tick=ctx.tick)
    for anchor in (args.get("link_to") or [])[:4]:
        anchor = str(anchor)
        if ctx.graph.has(anchor):
            ctx.graph.link(nid, anchor, "relates", tick=ctx.tick)
    ctx.emit(EventKind.STATE, (nid, {"charted": 1}), src="agent")
    return Outcome(True, f"charted {nid}")


def _act_message(ctx, args: dict) -> Outcome:
    target = str(args.get("target", "")).strip()
    text = str(args.get("text", "")).strip()
    if not (target and text):
        return Outcome(False, "message needs args.target and args.text")
    ctx.emit(EventKind.SIGNAL, (target, text[:200]), src="agent")
    return Outcome(True, f"signal -> {target}")


def _act_rest(ctx, args: dict) -> Outcome:
    name = str(args.get("tension", "energy"))
    if not ctx.tensions.has(name):
        return Outcome(False, f"unknown tension {name!r}")
    try:
        amount = float(args.get("amount", 0.3))
    except (TypeError, ValueError):
        return Outcome(False, "amount must be a number")
    # round 23 (wave-1 finding 7): a nan/inf amount used to slip through
    # to relieve(), where max(0.0, nan) silently zeroed the tension —
    # a free lunch. The seam rejects it; the kernel no-ops it. Both.
    if not math.isfinite(amount):
        return Outcome(False, f"amount must be finite, got {args.get('amount')!r}")
    ctx.tensions.relieve(name, amount)
    return Outcome(True, f"relieved {name} by {amount}")


ACTION_LIBRARY: dict = {
    "observe": (_act_observe, "attend to graph nodes (args: focus=[ids])"),
    "note": (_act_note, "write a note into the world (args: text)"),
    "search": (_act_search, "chart a new topic node (args: topic, link_to=[ids])"),
    "message": (_act_message, "signal another actor (args: target, text)"),
    "rest": (_act_rest, "relieve a tension (args: tension, amount)"),
}

ACTION_LIBRARY_DOC = "\n".join(
    f"- {name}: {doc}" for name, (_, doc) in sorted(ACTION_LIBRARY.items())
)


# ----------------------------------------------------------------------
# safe plumbing: when-hints and action binding
# ----------------------------------------------------------------------
def build_when(hint: str) -> Optional[Callable]:
    """A tiny, safe trigger DSL. Unknown hints mean 'always'."""
    hint = (hint or "always").strip()
    if hint == "always" or not hint:
        return None
    if hint.startswith("tension_above:"):
        parts = hint.split(":")
        if len(parts) == 3:
            name = parts[1]
            try:
                threshold = float(parts[2])
            except ValueError:
                return None
            return lambda ctx, n=name, t=threshold: ctx.tensions.level(n) >= t
        return None
    if hint.startswith("every:"):
        try:
            n = max(1, int(hint.split(":")[1]))
        except (ValueError, IndexError):
            return None
        return lambda ctx, n=n: ctx.tick % n == 0
    return None


def _sanitize(value):
    """JSON primitives only — the boundary between model output and code."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, list):
        return [_sanitize(v) for v in value][:16]
    if isinstance(value, dict):
        return {str(k)[:32]: _sanitize(v) for k, v in list(value.items())[:16]}
    return str(value)[:200]


def _bind_action(action: str, args: dict) -> Callable:
    fn = ACTION_LIBRARY[action][0]
    safe_args = _sanitize(args) if isinstance(args, dict) else {}

    def _runner(ctx, _fn=fn, _args=safe_args):
        return _fn(ctx, _args)

    return _runner


# ----------------------------------------------------------------------
# proposal parsing — strict, fail-soft
# ----------------------------------------------------------------------
def parse_proposals(text: str) -> Tuple[List[dict], str]:
    """Extract + validate proposals from model output.

    Returns (valid_proposals, note_about_what_failed). Never raises: a
    model that emits garbage simply produces zero proposals, and its
    accept-rate (hence its attention) decays.
    """
    candidates: list = []
    stripped = text.strip()

    def _try_parse(blob: str):
        try:
            return json.loads(blob)
        except (json.JSONDecodeError, ValueError):
            return None

    parsed = _try_parse(stripped)
    if parsed is None:
        # try the first ```json fence
        if "```" in stripped:
            for chunk in stripped.split("```"):
                chunk = chunk.strip()
                if chunk.startswith("json"):
                    chunk = chunk[4:].strip()
                parsed = _try_parse(chunk)
                if parsed is not None:
                    break
    if parsed is None:
        # last resort: first balanced [ ... ] or { ... }
        for opener, closer in (("[", "]"), ("{", "}")):
            start = stripped.find(opener)
            if start == -1:
                continue
            depth = 0
            for i in range(start, len(stripped)):
                if stripped[i] == opener:
                    depth += 1
                elif stripped[i] == closer:
                    depth -= 1
                    if depth == 0:
                        parsed = _try_parse(stripped[start:i + 1])
                        break
            if parsed is not None:
                break

    if parsed is None:
        return [], "no JSON found in model output"

    if isinstance(parsed, dict) and "proposals" in parsed:
        parsed = parsed["proposals"]
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return [], "JSON was neither array nor object"

    valid: list = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        action = str(item.get("action", "")).strip()
        if not name or action not in ACTION_LIBRARY:
            continue
        args = item.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        valid.append({
            "name": name[:48],
            "action": action,
            "args": _sanitize(args),
            "relieves": [str(r)[:24] for r in (item.get("relieves") or [])[:4]],
            "focus": [str(f)[:64] for f in (item.get("focus") or [])[:8]],
            "when_hint": str(item.get("when_hint", "always"))[:48],
        })
    dropped = len(parsed) - len(valid)
    note = f"{len(valid)} valid, {dropped} dropped" if parsed else "empty list"
    return valid, note


# ----------------------------------------------------------------------
# the agent component
# ----------------------------------------------------------------------
class LLMAgent:
    """An LLM-backed component: proposes scripts, obeys the market.

    Prompt discipline (the whole caching game):
      STABLE PREFIX   identity introspect + action library + output contract
                      -> frozen in the StablePrefixSession
      VOLATILE SUFFIX tensions, world digest, recent events, the current ask
                      -> rebuilt every call, lives in the user message
    """

    def __init__(self, agent_id: str, why_node: str, session,
                 every: int = 5, max_proposals: int = 3) -> None:
        self.id = agent_id
        self.why_node = why_node
        self.session = session
        self.every = max(1, every)
        self.max_proposals = max_proposals
        self.accept_rate = 0.5   # EMA of "did proposals survive validation"
        self.last_propose = 0    # for proposal staleness (see bid())

    # -- Component protocol --------------------------------------------
    def bid(self, ctx):
        """Bid for this tick: my spawned scripts compete, plus 'propose'.

        Note the staleness term in the propose bid's urgency: spawned
        scripts that thrive can outcompete the proposer in a fair market
        (their success rates rise above the proposer's accept rate), which
        would starve the organism of new ideas forever. An agent that has
        not proposed in ~30 ticks gets bored with its own repertoire —
        homeostasis for the ideation organ.
        """
        bids = list(ctx.ecology.bids(ctx, owner=self.id))
        if ctx.tick % self.every == 0:
            curiosity = (ctx.tensions.level("curiosity")
                         if ctx.tensions.has("curiosity") else 0.4)
            staleness = min(1.0, (ctx.tick - self.last_propose) / 30.0)
            bids.append(AttentionBid(
                src=self.id, label="propose",
                urgency=max(curiosity, staleness),
                justification=ctx.why.justification(self.why_node),
                opportunity=1.0,
                novelty=min(1.0, ctx.graph.churn_since(ctx.tick - 20)),
                expected_value=self.accept_rate,
            ))
        return bids

    def act(self, ctx, label: str) -> Outcome:
        if label == "propose":
            return self._propose(ctx)
        return ctx.ecology.fire(label, ctx)  # relay to a spawned script

    # -- the proposal turn ----------------------------------------------
    def _suffix(self, ctx) -> str:
        recent = [
            f"{e.kind.name}:{e.src}:{str(e.payload[0])[:24]}"
            for e in ctx.recent(6)
        ]
        return "\n".join([
            "## Current state (volatile)",
            f"tick: {ctx.tick}",
            f"tensions: {ctx.tensions.snapshot()}",
            f"recent events: {recent}",
            "",
            "## World digest",
            ctx.digest(24),
            "",
            "## Task",
            "Propose 1-3 scripts as a JSON array. Each object needs:",
            "name, action (from the library), args, relieves (tension names),",
            "focus (graph node ids), when_hint ('always' | 'tension_above:<name>:<x>' | 'every:<n>').",
            "Reply with the JSON array only.",
        ])

    def _propose(self, ctx) -> Outcome:
        completion = self.session.call(self._suffix(ctx), max_tokens=700,
                                       temperature=0.7)
        self.last_propose = ctx.tick
        proposals, note = parse_proposals(completion.text)
        spawned: list = []
        rejected: list = []
        for p in proposals[: self.max_proposals]:
            script = Script(
                name=p["name"],
                why_node=self.why_node,
                owner=self.id,
                relieves=tuple(p["relieves"]),
                focus=tuple(p["focus"]),
                when=build_when(p["when_hint"]),
                act=_bind_action(p["action"], p["args"]),
                params={"action": p["action"], "args": p["args"],
                        "when_hint": p["when_hint"]},
            )
            try:
                new, dup = ctx.ecology.spawn_unique(script, tick=ctx.tick)
            except ValueError:
                # name is live with a DIFFERENT behavior: name-squatting,
                # not a behavior duplicate — reject it too (round 23:
                # the ~tick variant hack is gone; bloat is over)
                new, dup = None, script
            if new is not None:
                spawned.append(new.name)
            else:
                rejected.append(f"{script.name}=={dup.name if dup else '?'}")
                # the demotion is VISIBLE: the model reads recent events,
                # so its next proposal turn sees what was rejected and why
                ctx.emit(
                    EventKind.ERROR,
                    ("proposal", "duplicate rejected",
                     f"{script.name} already exists as "
                     f"{dup.name if dup else 'a live name'}"),
                    src=self.id,
                )
        # duplicates demote: accept_rate counts SPAWNS only, so repeated
        # re-proposals lose expected value and the propose bid starves
        self.accept_rate = ema(self.accept_rate, 1.0 if spawned else 0.0)
        if spawned:
            extra = f"; {len(rejected)} duplicate(s) rejected" if rejected else ""
            return Outcome(True, f"spawned {spawned}{extra} ({note})")
        if rejected:
            return Outcome(False, f"{len(rejected)} duplicate proposal(s) "
                                  f"rejected ({note})")
        return Outcome(False, f"no valid proposals ({note})")
