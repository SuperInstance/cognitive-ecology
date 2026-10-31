"""Integration test: the week in a box.

The manifesto's core question, executable:

    What is the smallest persistent world that can improve itself
    while nobody is watching?

Assertions are on *capability accumulation*, not on specific noise:
sleep must compile routines, the script ecology must learn, weak scripts
must retire themselves, and killing a root must break justification
without deleting anything.
"""

from __future__ import annotations

from ecology.demo import TinyMud, WeekInABox


def test_tiny_mud_starts_with_seeded_machinery() -> None:
    mud = TinyMud(seed=1)
    census = mud.scripts.census()
    assert census["candidate"] == 17  # 12 good + 3 mediocre + 2 flaky
    assert mud.scripts.census()["active"] == 0


def test_week_accumulates_capability() -> None:
    report = WeekInABox(seed=42, days=7).run()
    # sleep compiled the recurring telemetry signatures into routines
    assert len(report.sleep_born_scripts) >= 2
    assert any("cpu" in name for name in report.sleep_born_scripts)
    # those routines ran on real observations: capability, not decoration
    assert report.observations_handled_by_sleep_born >= 20
    # the born routines graduated to active through their own success
    assert len(report.promoted) >= 2
    # weak/flaky seeds retired themselves by their own utility
    assert len(report.retired) >= 4
    # learned utility actually accumulated in the ecology
    assert report.total_utility > 1.0
    # seven days of reports
    assert len(report.days) == 7


def test_week_is_deterministic_under_a_seed() -> None:
    a = WeekInABox(seed=7, days=3).run()
    b = WeekInABox(seed=7, days=3).run()
    assert a.sleep_born_scripts == b.sleep_born_scripts
    assert a.retired == b.retired
    assert a.total_utility == b.total_utility


def test_killing_a_root_breaks_justification_without_deleting() -> None:
    report = WeekInABox(seed=42, days=7).run()
    # day 4: goal:legacy-demo is attested dead; its dependents must appear
    assert "goal:legacy-demo" in report.why_broken
    assert "script:seed-mediocre-1" in report.why_broken
    # ...but nothing was deleted: the why graph still knows every node
    assert report.days[-1].necessity.get("dead", 0) >= 7
