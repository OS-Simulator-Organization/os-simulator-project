from src.core.controller import RealController
from src.core.controller_api import RunConfig
from src.dashboard.network_topology import link_usage, route_edges, topology_dot

LINKS = [
    {"edge": "A-B", "src": "A", "dst": "B", "bandwidth": 100, "latency": 1.0, "status": "UP"},
    {"edge": "B-C", "src": "B", "dst": "C", "bandwidth": 50, "latency": 2.0, "status": "DOWN"},
]


def test_route_edges_match_in_both_directions():
    assert route_edges(["A", "B", "C"]) == {("A", "B"), ("B", "C"), ("B", "A"), ("C", "B")}


def test_topology_marks_the_route_and_down_links_in_words():
    dot = topology_dot(["A", "B", "C"], LINKS, ["A", "B"])
    assert '"A" -- "B" [label="1 ms · 100 B/ms · route"' in dot
    assert "DOWN" in dot


def test_baseline_link_usage_from_delivered_packets():
    controller = RealController()
    controller.load(RunConfig())
    result = controller.run()
    links = controller.engine.get_manager("Network").snapshot()["topology"]["links"]
    usage = {row["link"]: (row["packets"], row["bytes"]) for row in link_usage(result.events, links)}
    # PKT-1 A->B->C 128B, PKT-2 A->D 64B, PKT-3 B->C 256B
    assert usage == {"NodeA-NodeB": (1, 128), "NodeB-NodeC": (2, 384), "NodeA-NodeD": (1, 64), "NodeD-NodeC": (0, 0)}
