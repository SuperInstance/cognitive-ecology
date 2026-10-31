# Contributing

Small steps, always tested, never a secret.

## The loop

1. **Read the playbook** (`docs/07_playbook.md`). Play-tests are this
   project's unit of learning; code changes usually start as one.
2. **One variable per change.** The kernel is deterministic — respect
   that power; a change you cannot attribute is a change you cannot
   review.
3. **Add or adjust a test** for every behavioral change. The
   conservation laws and the veto law are pinned by tests on purpose:
   if your change breaks one, the change needs a manifesto-grade
   argument first (open an issue).
4. **Docs follow code.** New API surface without a
   `docs/03_layers_reference.md` row and, where relevant, an example or
   tutorial touch-up, is incomplete.

## Ground rules

- **Zero runtime dependencies** in the kernel. Stdlib only. Provider
  HTTP goes through `urllib`.
- **No secrets, ever.** Keys enter through environment variables only;
  CI's secret scan fails the build on key-shaped strings. If a credential
  touched your branch, rotate it before opening the PR.
- **Append-only by design.** Anything that deletes history (events,
  graph nodes, WHY nodes, necrology) will be rejected — propose an
  `OPEN_QUESTIONS.md` discussion instead.
- **Determinism**: seeds everywhere, no wall-clock inside organisms.
  Time is ticks.
- **Comments teach.** Module docstrings are the primary documentation
  layer; write them like the README depends on them (it does).

## Play-test contributions

Copy `templates/scenario_template.md`, run your scenario, and open an
issue with the filled template — even (especially) failed hypotheses.
Findings that change the kernel get a `docs/07_playbook.md` entry and
usually a regression test.

## Development setup

```bash
pip install -e ".[dev]"
make test          # the whole suite, ~2s
make world         # the ten-minute tour, end to end
make examples      # all five examples, keyless
make guard         # secret scan locally
```

## Commit style

Conventional-ish, present tense, scope optional:
`why: cascade-revive questions when an ancestor resurrects`.
Reference the play-test or issue when one exists.
