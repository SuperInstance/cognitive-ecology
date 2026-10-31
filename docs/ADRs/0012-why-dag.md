# ADR-0012 — The WHY DAG: purposes justified by several parents

- status: accepted (v0.4 round 13)
- date: 2026-11-01
- adopted from: live ideation round 009 (ranked #2 of the v0.4 frontier);
  pinning test quoted verbatim in tests/test_why_dag.py

## Context

Until v0.4 a purpose had exactly one parent: the WHY layer was a tree,
chosen in v0.2 for audit clarity. The first shared-purpose organism
breaks that: "maintain the shared index" is jointly justified by "serve
the archive" AND "serve the research group" — either lineage alone
warrants it. OPEN_QUESTIONS #1 asked which verdict policy a multi-parent
purpose needs: any-alive-parent? majority? weighted?

## Decision

### 1. Best-path semantics (OR)

A node **runs** iff at least one path to a root is fully ALIVE, and its
`justification()` is the strongest path's score (alive fraction ×
weakest-link freshness, probation capped per path). Killing one parent
of a jointly-justified purpose does not question it while another
parent's lineage warrants it; the purpose is exactly as strong as its
best living basis. Freshness follows the same rule: served through
either parent, fresh through that parent.

### 2. Cascade by surviving path, with a fixpoint

A kill cascades to UNKNOWN only descendants with **no surviving
fully-alive path** — no over-cascade (a surviving parent's lineage
shields the child). Cross-linked DAGs can strand a node whose last
living path ran through a *descendant* that cascades later in the same
sweep, so survivors are re-checked until a full pass cascades nothing
— no under-cascade. Monotone, terminating. Mirrors the same fixpoint
for the revive cascade: an UNKNOWN descendant returns iff its ancestors
on some path are all ALIVE (its own UNKNOWN-ness is the question being
decided).

### 3. Contradictions require destroyed warrant, not doubt

`contradictions()` = ALIVE nodes with **no fully-living path AND at
least one DEAD ancestor**. A node kept alive by another parent's
lineage is not a contradiction (it has living warrant); a node blocked
only by UNKNOWN ancestors is questionable, not contradictory. A tree
reduces to the v0.2 rule exactly.

### 4. Stamping serves the whole DAG lineage

`serving a purpose maintains its lineage` generalizes: a winning act
under a multi-parent node stamps every ALIVE ancestor over **all**
paths (primary path first, preserving the exact v0.2 tree order for
tree-shaped organisms, then extra ancestors in path order). The
auditor's service-derivation ground (society.py) walks every parent
edge to match.

### 5. Parents are fixed at declaration

`declare(parents=(a, b))` — no re-parenting API exists, so the purpose
graph is acyclic by construction; `paths()` enumerates routes without
cycle guards being reachable. The primary parent (first) is exposed as
`.parent` for tree-shaped code.

## Compatibility

- `declare(parent=...)` single-parent keeps the exact v0.2/v0.3 tree
  semantics: one path, BFS cascade order bit-for-bit, same journal
  stamp order, same verdict answers (pinned by
  `test_tree_cascade_order_is_bit_for_bit_v02` and the whole v0.3
  suite passing unchanged).
- Genesis rows now carry a parents TUPLE at index 1; v0.3 rows (a
  parent string or None) are normalized on load — old saved organisms
  load and verify. Receipt digests are computed fresh per verify, so
  the row-shape change is self-consistent within a version.
- The conservation auditor replays a DAG basis unchanged otherwise:
  cascades are recorded events (the necrology is the truth), so the
  replay applies records; it never re-derives cascades. Tampering a
  node's parents off the books fails the state-equivalence check
  (pinned).

## What is deliberately NOT here (yet)

- **Weighted parents** — a path's alive-fraction treats every link
  equally; a weighted basis (this parent matters 2x) would multiply
  path scores by a declared weight. Deferred until a play-test demands
  it.
- **Majority semantics** — OR was chosen over majority because it
  matches the treaty semantics (ADR-0011: non-sole treaties stand on
  whatever remains) and the epistemology (one living warrant is
  warrant). Majority remains an option if play-testing shows OR is too
  permissive.
- **DAG-aware attention** — novelty/EV estimation still sees focus
  sets, not the purpose topology.

## Consequences

- The WHY layer's public surface grew one concept (parents) and two
  methods (`paths()`, the fixpoint cascades); everything else is the
  same API with path-generalized semantics.
- Kill/revive on a DAG is O(paths × nodes) worst case; trees (the
  common case) are unchanged O(n).
- The society (ADR-0011) composes: a treaty may delegate a multi-parent
  purpose; the federation auditor's service check walks every parent
  edge (pinned by `test_treaty_onto_a_dag_beneficiary`).
