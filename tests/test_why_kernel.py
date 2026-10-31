"""Unit tests for the WHY kernel — mirroring why-core's own suite.

These duplicate a few corpus pairs inline so a regression is easy to read:
the semantic rules each get a name that says what law is being pinned.
"""

from __future__ import annotations

from ecology.why import (
    Provenance,
    Status,
    add_days,
    chain,
    dom_subtree,
    evaluate,
    is_valid_date,
    parse_attestation,
    parse_graph,
)


def _ev(graph_text: str, att_text: str, as_of: str | None = None):
    return evaluate(parse_graph(graph_text), parse_attestation(att_text), as_of)


# ---- dates ----


def test_date_validity() -> None:
    assert is_valid_date("2026-10-31")
    assert not is_valid_date("2026-1-31")
    assert not is_valid_date("2026-13-01")
    assert not is_valid_date("not-a-date")
    assert not is_valid_date("2026/10/31")


def test_add_days() -> None:
    assert add_days("2026-01-01", 30) == "2026-01-31"
    assert add_days("2026-12-31", 1) == "2027-01-01"
    assert add_days("2024-02-28", 1) == "2024-02-29"  # leap
    assert add_days("bad", 1) is None


# ---- pass 1: aliveness is explicit-only ----


def test_alive_propagation_explicit() -> None:
    ev = _ev(
        "role:analyst -> project:active (explicit)\nworkflow:deploy -> project:active (explicit)",
        "project:active alive 2024-01-01 casey",
    )
    assert ev.status_of("role:analyst") is Status.ALIVE
    assert ev.status_of("workflow:deploy") is Status.ALIVE


def test_inferred_edge_never_confers_liveness() -> None:
    ev = _ev(
        "app:legacy -> project:active (inferred)",
        "project:active alive 2024-01-01 casey",
    )
    assert ev.status_of("app:legacy") is Status.UNKNOWN


def test_inferred_edge_never_confers_dead() -> None:
    ev = _ev(
        "app:report -> project:old (explicit)\napp:legacy-export -> project:old (inferred)",
        "project:old dead 2023-04-12 ci",
    )
    assert ev.status_of("app:report") is Status.DEAD
    assert ev.status_of("app:legacy-export") is Status.UNKNOWN


def test_explicit_and_inferred_mixed_prefers_unknown() -> None:
    # The candidate live reason blocks a dead verdict (mixed_verdicts pair).
    ev = _ev(
        "app:report -> project:old (explicit)\napp:report -> project:active (inferred)",
        "project:old dead 2023-04-12 ci\nproject:active alive 2024-01-01 casey",
    )
    assert ev.status_of("app:report") is Status.UNKNOWN


# ---- pass 3/4: deadness vs unknown ----


def test_deadness_propagates_full_depth() -> None:
    # External audit 2026-10-30, Finding 2.
    ev = _ev(
        "leaf:x -> mid:y (explicit)\nmid:y -> root:dead (explicit)",
        "root:dead dead 2023-04-12 probe",
    )
    assert ev.status_of("root:dead") is Status.DEAD
    assert ev.status_of("mid:y") is Status.DEAD
    assert ev.status_of("leaf:x") is Status.DEAD


def test_dangling_branch_beats_dead_branch() -> None:
    ev = _ev(
        "leaf:a -> mid:b (explicit)\nmid:b -> root:dead (explicit)\nmid:b -> root:dangling (explicit)",
        "root:dead dead 2023-01-01 probe",
    )
    assert ev.status_of("root:dead") is Status.DEAD
    assert ev.status_of("root:dangling") is Status.UNKNOWN
    assert ev.status_of("mid:b") is Status.UNKNOWN
    assert ev.status_of("leaf:a") is Status.UNKNOWN


def test_unknown_when_unattested() -> None:
    ev = _ev("service:billing -> ticket:BILL-99 (inferred)", "")
    assert ev.status_of("service:billing") is Status.UNKNOWN
    assert ev.status_of("ticket:BILL-99") is Status.UNKNOWN


def test_absent_for_unseen_ids() -> None:
    ev = _ev("a:b -> c:d", "c:d alive 2024-01-01 x")
    assert ev.status_of("a:b") is Status.ALIVE
    assert ev.status_of("nope:nonsense") is Status.ABSENT


# ---- root mortality ----


def test_until_hard_expiry() -> None:
    ev = _ev(
        "app:tmp-role -> project:burst (explicit)",
        "project:burst alive 2024-01-01 ops until=2026-03-01",
        as_of="2026-02-01",
    )
    assert ev.status_of("project:burst") is Status.ALIVE
    ev = _ev(
        "app:tmp-role -> project:burst (explicit)",
        "project:burst alive 2024-01-01 ops until=2026-03-01",
        as_of="2026-04-01",
    )
    assert ev.status_of("project:burst") is Status.DEAD
    assert ev.status_of("app:tmp-role") is Status.DEAD
    assert ev.expired_roots == ["project:burst"]


def test_review_by_soft_expiry() -> None:
    graph = "app:audit-role -> reg:SOC2 (explicit)"
    att = "reg:SOC2 alive 2024-01-01 security review-by=2026-01-01"
    within = _ev(graph, att, as_of="2026-01-15")  # inside 30-day grace
    assert within.status_of("reg:SOC2") is Status.ALIVE
    past = _ev(graph, att, as_of="2026-06-01")  # stale -> unknown, propagated
    assert past.status_of("reg:SOC2") is Status.UNKNOWN
    assert past.status_of("app:audit-role") is Status.UNKNOWN
    assert past.stale_roots == ["reg:SOC2"]


def test_no_clock_ignores_expiry() -> None:
    ev = _ev(
        "app:audit-role -> reg:SOC2 (explicit)",
        "reg:SOC2 alive 2024-01-01 security review-by=2020-01-01",
        as_of=None,
    )
    assert ev.status_of("reg:SOC2") is Status.ALIVE


# ---- conjunctive groups ----


def test_conjunctive_all_alive_confers_liveness() -> None:
    ev = _ev(
        "orderset:icu -> all-of: protocol:sepsis policy:condition-active",
        "protocol:sepsis alive 2024-01-01 med\npolicy:condition-active alive 2024-01-01 med",
    )
    assert ev.status_of("orderset:icu") is Status.ALIVE


def test_conjunctive_dead_member_short_circuits() -> None:
    # Dead beats unknown inside all-of: the group is definitively falsified.
    ev = _ev(
        "orderset:icu -> all-of: protocol:sepsis policy:maybe",
        "protocol:sepsis dead 2023-01-01 med",
    )
    assert ev.status_of("orderset:icu") is Status.DEAD


def test_conjunctive_undetermined_blocks_dead() -> None:
    ev = _ev(
        "orderset:icu -> all-of: protocol:sepsis policy:maybe",
        "protocol:sepsis alive 2024-01-01 med",
    )
    assert ev.status_of("orderset:icu") is Status.UNKNOWN


def test_conjunctive_confers_liveness_to_explicit_children() -> None:
    # A group-derived alive node must justify its own explicit children —
    # this is why Pass 1 is a fixpoint, not a single BFS.
    ev = _ev(
        "orderset:icu -> all-of: protocol:sepsis policy:active\n"
        "alert:sepsis -> orderset:icu (explicit)",
        "protocol:sepsis alive 2024-01-01 med\npolicy:active alive 2024-01-01 med",
    )
    assert ev.status_of("orderset:icu") is Status.ALIVE
    assert ev.status_of("alert:sepsis") is Status.ALIVE


# ---- chains and dominators ----


def test_chain_prefers_explicit_parent() -> None:
    g = parse_graph("a:x -> b:dead (explicit)\na:x -> c:live (inferred)")
    a = parse_attestation("b:dead dead 2023-01-01 p\nc:live alive 2024-01-01 p")
    ev = evaluate(g, a)
    result = chain(g, ev, "a:x")
    assert result[0] == "a:x"
    assert "b:dead" in result  # the explicit parent explains the verdict


def test_dominator_subtree_and_chain() -> None:
    g = parse_graph(
        "app:a -> root:live (explicit)\n"
        "app:b -> app:a (explicit)\n"
        "app:c -> app:a (explicit)\n"
        "app:d -> app:b (explicit)"
    )
    a = parse_attestation("root:live alive 2024-01-01 x")
    ev = evaluate(g, a)
    assert ev.status_of("app:d") is Status.ALIVE
    # Every live path to b/c/d passes through app:a (strict descendants).
    subtree = dom_subtree(ev.idom, "app:a")
    assert {"app:b", "app:c", "app:d"} <= subtree
    assert "app:a" not in subtree  # strict: the node itself is not its own gate
    assert dom_subtree(ev.idom, "app:d") == set()


def test_dominators_with_two_live_roots() -> None:
    g = parse_graph(
        "app:a -> root:one (explicit)\napp:b -> root:two (explicit)\napp:c -> app:a (explicit)"
    )
    a = parse_attestation("root:one alive 2024-01-01 x\nroot:two alive 2024-01-01 x")
    ev = evaluate(g, a)
    for node in ("app:a", "app:b", "app:c"):
        assert ev.status_of(node) is Status.ALIVE
    # With two roots, no single gate dominates both branches.
    assert "app:b" not in dom_subtree(ev.idom, "app:a")


def test_summary_counts() -> None:
    ev = _ev(
        "a:alive -> root:live (explicit)\na:dead -> root:dead (explicit)\na:cand -> root:live (inferred)",
        "root:live alive 2024-01-01 x\nroot:dead dead 2023-01-01 x",
    )
    counts = ev.summary()
    assert counts["alive"] == 2  # root:live + a:alive
    assert counts["dead"] == 2  # root:dead + a:dead
    assert counts["unknown"] == 1  # a:cand


def test_provenance_roundtrip() -> None:
    g = parse_graph("x:y -> a:b (inferred)")
    assert g.edges["x:y"][0][1] is Provenance.INFERRED
    assert g.discovered is None
    g2 = parse_graph("# discovered: 12\na:b -> c:d")
    assert g2.discovered == 12
    assert g2.wired() == 1
