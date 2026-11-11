from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller_api import MemoryConfig, RunConfig
from src.dashboard.views.comparison import compare_replacement_policies, side_by_side

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"

# Pages 1 2 3 1 4 1 (256-byte pages) with 3 frames, worked by hand:
#   FIFO: F F F H F(evicts 1) F(evicts 2)  -> 5 faults, 1 hit, 2 evictions
#   LRU:  F F F H F(evicts 2) H            -> 4 faults, 2 hits, 1 eviction
LOCALITY = RunConfig(scenario_id="custom",
                     memory=MemoryConfig(page_size=256, total_frames=3, fault_latency=0,
                                         trace=[256, 512, 768, 256, 1024, 256]))


def by_policy(config: RunConfig) -> dict:
    return {row["policy"]: row for row in compare_replacement_policies(config)}


def test_fifo_and_lru_match_the_hand_calculation():
    rows = by_policy(LOCALITY)
    assert (rows["FIFO"]["Faults"], rows["FIFO"]["Hits"], rows["FIFO"]["Evictions"]) == (5, 1, 2)
    assert (rows["LRU"]["Faults"], rows["LRU"]["Hits"], rows["LRU"]["Evictions"]) == (4, 2, 1)


def test_both_policies_see_the_same_references():
    rows = by_policy(LOCALITY)
    assert rows["FIFO"]["References"] == rows["LRU"]["References"] == 6


def test_comparison_is_reproducible():
    assert compare_replacement_policies(LOCALITY) == compare_replacement_policies(LOCALITY)


def test_baseline_without_custom_traces_uses_the_baseline_trace():
    rows = by_policy(RunConfig())
    assert rows["FIFO"]["References"] == rows["LRU"]["References"] == 4


def test_side_by_side_has_a_column_per_policy():
    table = side_by_side(compare_replacement_policies(LOCALITY))
    assert table[2] == {"metric": "Faults", "FIFO": 4, "LRU": 4}


def test_comparison_tab_runs_and_shows_table_and_chart():
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    app.button(key="run-memory-comparison").click().run()
    assert not app.exception
    assert [r["policy"] for r in app.session_state["memory-comparison"]] == ["FIFO", "LRU"]
    assert app.get("vega_lite_chart")
