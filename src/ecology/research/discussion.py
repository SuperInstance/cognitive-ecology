"""The discussion runner: multi-round, cache-first, decision-gated.

The protocol (documented because the process is a product):

1. Every panelist sees the same append-only transcript. Their prompt is a
   byte-stable prefix (panel rules + topic + context + transcript so far)
   plus a tiny variable suffix (their role instruction). Append-only growth
   is exactly what prefix caching rewards: from round 2 on, most of every
   prompt is a cache hit (80-90% off on the DeepInfra panel).
2. Between rounds, the TypeSafe decision model (Jev) is asked *typed*
   questions about the round — which thread deserves attention, whether the
   disagreement is substantive — and its calibrated probabilities steer the
   next round's framing. Decision models route attention; they don't write prose.
3. Every turn carries provenance: provider, model, latency, tokens, cached
   tokens, cost. The transcript is a receipt, not just a text.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..llm.base import DecisionRequest, LLMClient, PromptSpec
from ..llm.typesafe import TypeSafeClient
from .panel import DEFAULT_PANEL, SYNTHESIZER, Participant

STABLE_PANEL_PROMPT = """You are one member of a research panel improving a persistent cognitive
ecology — a system where WHY (live justification of why anything deserves to exist)
is the conservation law governing processes, attention, scripts, and sleep.
The stack: L0 runtime, L1 event fabric, L2 world state graph, L3 budgeted
simulations, L4 script ecology, attention economy, sleep (consolidation),
LLM teachers (you), identity as attractor.

Panel rules:
- Concrete over abstract: name layers, modules, mechanisms, numbers.
- Attack ideas, never people; steelman before you strike.
- Each contribution must be <= 250 words.
- End with a single line starting "OPEN QUESTION:" if you have one."""


@dataclass
class Turn:
    participant: str
    role: str
    round_no: int
    text: str
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float | None = None


@dataclass
class DecisionTurn:
    round_no: int
    questions: dict
    answers: dict
    model: str = ""
    latency_ms: int = 0
    cost_usd: float | None = None


@dataclass
class Transcript:
    topic: str
    turns: list[Turn] = field(default_factory=list)
    decisions: list[DecisionTurn] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    total_cost_usd: float = 0.0

    def render(self, upto_round: int | None = None) -> str:
        lines: list[str] = []
        for turn in self.turns:
            if upto_round is not None and turn.round_no > upto_round:
                continue
            lines.append(f"[{turn.participant}/{turn.role}] (r{turn.round_no}):\n{turn.text}\n")
        for decision in self.decisions:
            if upto_round is not None and decision.round_no > upto_round:
                continue
            summary = {k: _clip_value(v) for k, v in decision.answers.items()}
            lines.append(f"[jev/decision] (r{decision.round_no}): {summary}\n")
        return "\n".join(lines)


def _clip_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, tuple):
        return "(" + ", ".join(_clip_value(v) for v in value) + ")"
    return str(value)


class Discussion:
    def __init__(
        self,
        topic: str,
        context: str,
        participants: list[Participant],
        clients: dict[str, LLMClient],
        *,
        decider: TypeSafeClient | None = None,
        synthesizer: Participant = SYNTHESIZER,
    ):
        self.topic = topic
        self.context = context
        self.participants = participants
        self.clients = clients
        self.decider = decider
        self.synthesizer = synthesizer
        self.transcript = Transcript(topic=topic)

    # ---- the loop ----

    def run(self, rounds: int = 2) -> Transcript:
        for round_no in range(1, rounds + 1):
            self._run_round(round_no)
            if self.decider is not None:
                self._decision_gate(round_no)
        self._synthesize(rounds)
        self._collect_open_questions()
        return self.transcript

    def _run_round(self, round_no: int) -> None:
        for participant in self.participants:
            client = self.clients.get(participant.provider)
            if client is None:
                continue
            spec = PromptSpec(
                stable_prefix=self._stable_prefix(),
                variable_suffix=(
                    f"YOUR TURN — you are '{participant.name}', the {participant.role}. "
                    f"{participant.instruction}"
                ),
                max_tokens=700,
                temperature=0.7,
            )
            # A dropped panelist must not kill the round: the seat goes
            # vacant, the vacancy is recorded, the panel continues.
            try:
                response = client.complete(spec, participant.model, role=participant.role)
            except Exception as exc:  # noqa: BLE001 - panel resilience
                self.transcript.turns.append(
                    Turn(
                        participant=participant.name,
                        role=participant.role,
                        round_no=round_no,
                        text=f"(seat vacant this round — provider error: {exc})",
                        provider=participant.provider,
                        model=participant.model,
                    )
                )
                continue
            turn = Turn(
                participant=participant.name,
                role=participant.role,
                round_no=round_no,
                text=response.text.strip(),
                provider=response.provider,
                model=response.model,
                latency_ms=response.latency_ms,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                cached_tokens=response.cache_hit_tokens,
                cost_usd=response.usage.cost_usd,
            )
            self.transcript.turns.append(turn)
            self.transcript.total_cost_usd += response.usage.cost_usd or 0.0

    def _decision_gate(self, round_no: int) -> None:
        """Typed questions for Jev about the round just completed."""
        names = [p.name for p in self.participants]
        questions: dict[str, dict] = {}
        name_q, question = TypeSafeClient.choice(
            "next_focus",
            "Which panelist's thread deserves the most attention in the next round?",
            {n: f"Continue from {n}'s line of reasoning" for n in names},
        )
        questions[name_q] = question
        name_q2, question2 = TypeSafeClient.noul(
            "substantive",
            "Is the current disagreement between panelists substantive (about fundamentals) "
            "rather than about wording?",
        )
        questions[name_q2] = question2
        name_q3, question3 = TypeSafeClient.score(
            "coherence",
            "How coherent is the panel's emerging position?",
            ["Contradictory", "Partially aligned", "Aligned with open edges", "Converged"],
        )
        questions[name_q3] = question3

        request = DecisionRequest(
            state={
                "topic": self.topic,
                "round": round_no,
                "transcript_last_round": self.transcript.render(upto_round=round_no)[-6000:],
            },
            questions=questions,
        )
        try:
            response = self.decider.decide(request, role="round-gate")
        except Exception as exc:  # noqa: BLE001 - a failed gate is recorded, not fatal
            self.transcript.decisions.append(
                DecisionTurn(
                    round_no=round_no,
                    questions={},
                    answers={"gate_error": str(exc)[:200]},
                )
            )
            return
        answers = {name: ans.value for name, ans in response.answers.items()}
        self.transcript.decisions.append(
            DecisionTurn(
                round_no=round_no,
                questions={k: v.get("instructions", "")[:120] for k, v in questions.items()},
                answers=answers,
                model=response.model,
                latency_ms=response.latency_ms,
            )
        )
        self.transcript.total_cost_usd += response.usage.cost_usd or 0.0

    def _synthesize(self, rounds: int) -> None:
        client = self.clients.get(self.synthesizer.provider)
        if client is None:
            return
        spec = PromptSpec(
            stable_prefix=self._stable_prefix(),
            variable_suffix=f"YOUR TURN — you are '{self.synthesizer.name}', the "
            f"{self.synthesizer.role}. {self.synthesizer.instruction}",
            max_tokens=900,
            temperature=0.4,
        )
        response = client.complete(spec, self.synthesizer.model, role="synthesizer")
        self.transcript.turns.append(
            Turn(
                participant=self.synthesizer.name,
                role=self.synthesizer.role,
                round_no=rounds,
                text=response.text.strip(),
                provider=response.provider,
                model=response.model,
                latency_ms=response.latency_ms,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                cached_tokens=response.cache_hit_tokens,
                cost_usd=response.usage.cost_usd,
            )
        )
        self.transcript.total_cost_usd += response.usage.cost_usd or 0.0

    def _collect_open_questions(self) -> None:
        for turn in self.transcript.turns:
            for match in re.findall(r"^OPEN QUESTION:\s*(.+)$", turn.text, flags=re.MULTILINE):
                self.transcript.open_questions.append(match.strip())

    # ---- prompts ----

    def _stable_prefix(self) -> str:
        return (
            f"{STABLE_PANEL_PROMPT}\n\nTOPIC: {self.topic}\n\nCONTEXT DOCUMENT:\n"
            f"{self.context}\n\nTRANSCRIPT SO FAR:\n{self.transcript.render() or '(none yet)'}"
        )

    # ---- output ----

    def to_markdown(self) -> str:
        lines = [
            f"# Panel discussion: {self.topic}",
            "",
            f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
            f"{len(self.participants) + 1} panelists, decision model: "
            f"{'jev' if self.decider else 'none'}*",
            "",
            "## Context",
            "",
            self.context,
            "",
            "## Transcript",
            "",
        ]
        for turn in self.transcript.turns:
            lines.append(f"### {turn.participant} ({turn.role}) — round {turn.round_no}")
            lines.append(
                f"*{turn.provider}/{turn.model} — {turn.latency_ms}ms, "
                f"{turn.prompt_tokens}in/{turn.completion_tokens}out "
                f"({turn.cached_tokens} cached)*"
                + (f" — ${turn.cost_usd:.6f}" if turn.cost_usd is not None else "")
            )
            lines.append("")
            lines.append(turn.text)
            lines.append("")
        for decision in self.transcript.decisions:
            lines.append(f"### decision gate — round {decision.round_no}")
            lines.append(f"*{decision.model} — {decision.latency_ms}ms*")
            lines.append("")
            for question, answer in decision.answers.items():
                lines.append(f"- **{question}**: {_clip_value(answer)}")
            lines.append("")
        if self.transcript.open_questions:
            lines.append("## Open questions surfaced")
            lines.append("")
            for question in self.transcript.open_questions:
                lines.append(f"- {question}")
            lines.append("")
        cost = self.transcript.total_cost_usd
        lines.append(f"---\n*Recorded cost (provider-reported only): ${cost:.6f}*")
        return "\n".join(lines)


def next_round_number(library_dir: Path) -> int:
    """library/rounds/001-*.md -> next is 002."""
    if not library_dir.exists():
        return 1
    numbers = [
        int(m.group(1))
        for p in library_dir.glob("[0-9][0-9][0-9]-*.md")
        if (m := re.match(r"(\d{3})-", p.name))
    ]
    return max(numbers, default=0) + 1


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "discussion"


def run_panel_cli(args) -> int:
    from ..config import Settings
    from ..llm.deepinfra import DeepInfraClient
    from ..llm.ledger import Ledger
    from ..llm.minimax import MiniMaxClient

    repo_root = Path(__file__).resolve().parents[3]
    settings = Settings.from_env(repo_root / ".env")
    ledger = Ledger(repo_root / settings.ledger_path)

    clients: dict[str, LLMClient] = {}
    if settings.deepinfra_api_key:
        clients["deepinfra"] = DeepInfraClient(settings, ledger=ledger)
    if settings.minimax_api_key:
        clients["minimax"] = MiniMaxClient(settings, ledger=ledger)
    if not clients:
        print(
            "no provider keys found (need DEEPINFRA_API_KEY / MINIMAX_API_KEY)",
            file=sys.stderr,
        )
        return 2

    decider = TypeSafeClient(settings, ledger=ledger) if settings.typesafe_api_key else None
    participants = [p for p in DEFAULT_PANEL if p.provider in clients]
    if not participants:
        print("no panelists available for the configured providers", file=sys.stderr)
        return 2

    context = Path(args.context).read_text() if args.context else "(no context document supplied)"
    discussion = Discussion(
        topic=args.topic,
        context=context,
        participants=participants,
        clients=clients,
        decider=decider,
    )
    transcript = discussion.run(rounds=args.rounds)

    out_dir = repo_root / "library" / "rounds"
    out_dir.mkdir(parents=True, exist_ok=True)
    number = next_round_number(out_dir)
    out_path = Path(args.out) if args.out else out_dir / f"{number:03d}-{slugify(args.topic)}.md"
    out_path.write_text(discussion.to_markdown())

    total_tokens_in = sum(t.prompt_tokens for t in transcript.turns)
    total_cached = sum(t.cached_tokens for t in transcript.turns)
    print(f"panel complete: {len(transcript.turns)} turns, {len(transcript.decisions)} decisions")
    print(
        f"tokens: {total_tokens_in} in ({total_cached} cached), "
        f"cost ${transcript.total_cost_usd:.6f}"
    )
    print(f"written: {out_path}")
    ledger.close()
    return 0
