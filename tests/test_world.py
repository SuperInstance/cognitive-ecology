"""L2 world state graph tests."""

from __future__ import annotations

from ecology.world import WorldGraph


def test_nodes_and_edges_roundtrip(tmp_path) -> None:
    world = WorldGraph(tmp_path / "world.db")
    world.add_node("project:ecology", "project", {"maturity": "pattern"}, tick=1)
    world.add_node("goal:ship-v01", "goal", {}, tick=1)
    world.add_edge("project:ecology", "goal:ship-v01", "SUPPORTS")
    world.persist()
    world.close()

    reloaded = WorldGraph(tmp_path / "world.db")
    node = reloaded.node("project:ecology")
    assert node is not None and node.type == "project"
    assert node.attrs["maturity"] == "pattern"
    assert reloaded.neighbors("project:ecology", "SUPPORTS") == ["goal:ship-v01"]
    assert reloaded.predecessors("goal:ship-v01") == ["project:ecology"]


def test_memory_graduation_only_upward() -> None:
    world = WorldGraph()
    world.add_node("memory:obs-1", "memory", {"maturity": "observation"})
    assert world.graduate("memory:obs-1", "episode") is True
    assert world.graduate("memory:obs-1", "policy") is True
    assert world.graduate("memory:obs-1", "episode") is False  # never backward
    assert world.graduate("memory:obs-1", "nonsense") is False
    assert world.node("memory:obs-1").attrs["maturity"] == "policy"


def test_census_by_type() -> None:
    world = WorldGraph()
    world.add_node("a", "project")
    world.add_node("b", "project")
    world.add_node("c", "routine")
    assert world.census() == {"project": 2, "routine": 1}
