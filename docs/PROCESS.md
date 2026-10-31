# Process — how this project works

*The owner's directive: "document extensively the process as you go,
thinking about the process as as important as the project and product."
This document is the operating manual for that.*

## The loop

1. **Research round** — subagents deep-read sources (the original
   conversation, digests, audits, provider docs) and return structured
   findings with citations. Nothing is invented; unverifiable claims are
   marked UNCONFIRMED.
2. **Build round** — a milestone lands as a commit: code + tests + docs
   together, pushed immediately ("push often"). Every push passes lint,
   tests, and the secrets scan.
3. **Experiment round** — the runnable question (week-in-a-box) is
   re-run and its numbers recorded. The experiment is allowed to fail the
   build's expectations; when it does, the finding goes in the journal and
   the fix goes in the code.
4. **Discussion round** — the live multi-model panel argues a topic with
   full provenance (provider, model, latency, tokens, cached tokens, cost
   per turn), Jev gates steer between rounds, and the transcript lands in
   `library/rounds/` as a receipt.
5. **Reflection round** — the journal, the open-questions ledger, and the
   ADRs absorb what happened. Questions are never deleted; they get probes.

## Rules of the road

- **The kernel is a pure function.** No I/O, no clock unless passed, no
  globals. The Rust `why` and the Python port are pinned to the same golden
  corpus; a pair that changes behavior is a semantic decision, not a
  refactor.
- **The runtime must survive zero LLMs** (Law 4). Teachers edit the
  organism from outside; nothing in a tick may call a provider.
- **Failures are content.** The MiniMax 401, the token-bucket hang, the
  routine-fires-on-everything bug — all documented in the journal with what
  they taught. A playtest that finds nothing is a playtest that ran wrong.
- **Provenance or it didn't happen.** Every panel turn, every decision
  gate, every cost is recorded. The transcript is a receipt, not a text.
- **Secrets never ship.** `.env` is gitignored; `scripts/check_secrets.py`
  runs in CI and pre-push; keys live in the environment and are never
  printed, echoed, or committed. A hit fails the build.
- **Cache-first, always.** Stable prefix + append-only transcript + session
  `prompt_cache_key`. Cache-read is 80–90% off list price on the panel
  models; the ledger makes the saving visible per model.

## Cadence

Milestones are small and pushed immediately. This session's shape:
kernel → organism layers → experiment → teachers → live rounds → docs →
tag. Each milestone ends with: lint clean, tests green, secrets scanned,
pushed.
