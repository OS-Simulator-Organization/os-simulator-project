from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller import RealController
from src.core.controller_api import MemoryConfig, RunConfig, ProcessConfig
from src.dashboard.memory_history import memory_history

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def finished_run(config: RunConfig):
    controller = RealController()
    controller.load(config)
    return controller.run().snapshot


def test_replay_matches_the_live_run():
    snapshot = finished_run(RunConfig())
    history = memory_history(snapshot.config, snapshot.tick)
    metrics = snapshot.metrics["Memory"]
    hits = sum(a["count"] for a in history["accesses"] if a["result"] == "Hit")
    faults = sum(a["count"] for a in history["accesses"] if a["result"] == "Fault")
    assert (hits, faults) == (metrics["page_hits"].value, metrics["page_faults"].value)


def test_every_frame_is_recorded_on_every_tick():
    snapshot = finished_run(RunConfig())
    history = memory_history(snapshot.config, snapshot.tick)
    baseline_frames = 4  # the baseline scenario always uses 4 frames
    assert len(history["frames"]) == snapshot.tick * baseline_frames


def test_baseline_trace_hits_and_faults_by_tick():
    # Baseline trace 0x0040, 0x10A0, 0x0044, 0x20B0 with 4096-byte pages is pages 0, 1, 0, 2.
    # P1 runs ticks 0-3 under the baseline Round Robin (q=4), but its third reference lands
    # on tick 2 and the fourth after it is dispatched again at tick 4.
    snapshot = finished_run(RunConfig())
    accesses = memory_history(snapshot.config, snapshot.tick)["accesses"]
    assert [(a["tick"], a["result"]) for a in accesses] == [(0, "Fault"), (1, "Fault"), (2, "Hit"), (3, "Fault")]


def test_free_frames_are_marked_free():
    config = RunConfig(memory=MemoryConfig(page_size=256, total_frames=3, fault_latency=0, trace=[256]))
    history = memory_history(config, 1)
    assert [row["page"] for row in history["frames"]] == [0, None, None]


def test_evictions_match_the_hand_calculation():
    # Pages 1 2 3 1 4 1 with 3 frames under FIFO: page 4 evicts page 1 (frame 0), then page 1 evicts page 2 (frame 1).
    config = RunConfig(
    scenario_id="custom",
    process=ProcessConfig(
        custom_workload=[
            {"pid": "P1", "arrival_time": 0, "burst_time": 20, "priority": 1}
        ]
    ),
    memory=MemoryConfig(
        page_size=256,
        total_frames=3,
        fault_latency=0,
        trace=[256, 512, 768, 256, 1024, 256]))
    controller = RealController()
    controller.load(config)
    snapshot = controller.run().snapshot
    evictions = memory_history(config, snapshot.tick)["evictions"]
    assert [(e["frame"], e["evicted"], e["loaded"]) for e in evictions] == [
        (0, "page 1", "page 4"), (1, "page 2", "page 1"),
    ]
    assert len(evictions) == snapshot.metrics["Memory"]["eviction_count"].value


def test_memory_tab_draws_both_over_time_charts_after_a_run():
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    app.sidebar.button[0].click().run()
    app.button(key="memory-run-to-end").click().run()
    assert not app.exception
    markdown = [m.value for m in app.markdown]
    assert "**Frame occupancy over time**" in markdown
    assert "**Page hits and faults over time**" in markdown
    captions = [c.value for c in app.caption]
    assert "No ticks run yet. Press Step or Run." not in captions
    assert any(b.label == "Download frames (CSV)" for b in app.get("download_button"))
