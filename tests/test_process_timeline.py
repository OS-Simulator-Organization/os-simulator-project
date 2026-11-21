from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller import RealController
from src.core.controller_api import RunConfig
from src.core.events import EventRecord
from src.dashboard.process_timeline import state_intervals, transitions

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def change(time, pid, before, after, message=""):
    return EventRecord(timestamp=time, manager="Process", event_type="X", entity_id=pid, action="A",
                       previous_state=before, new_state=after, outcome="SUCCESS", explanatory_message=message)


def test_intervals_follow_running_blocked_ready():
    events = [
        change(0, "P1", "NEW", "READY"),
        change(1, "P1", "READY", "RUNNING"),
        change(3, "P1", "RUNNING", "WAITING", "Blocked by Memory manager"),
        change(5, "P1", "WAITING", "READY", "Unblocked by Memory manager"),
        change(6, "P1", "READY", "RUNNING"),
        change(8, "P1", "RUNNING", "TERMINATED"),
    ]
    rows = state_intervals(events, now=10)
    assert [(r["state"], r["start (ms)"], r["end (ms)"]) for r in rows] == [
        ("Ready", 0, 1), ("Running", 1, 3), ("Blocked", 3, 5), ("Ready", 5, 6), ("Running", 6, 8),
    ]
    assert rows[2]["reason"] == "Blocked by Memory manager"


def test_open_state_ends_now_and_same_state_events_are_ignored():
    events = [change(0, "P2", "NEW", "READY"), change(2, "P2", "READY", "READY"), change(4, "P2", "READY", "RUNNING")]
    rows = state_intervals(events, now=7)
    assert [(r["state"], r["start (ms)"], r["end (ms)"]) for r in rows] == [("Ready", 0, 4), ("Running", 4, 7)]
    assert len(transitions(events)) == 2


def test_baseline_run_shows_memory_faults_blocking_and_releasing_processes():
    controller = RealController()
    controller.load(RunConfig())
    steps = [(t["process"], t["from"], t["to"], t["reason"]) for t in transitions(controller.run().events)]
    assert ("P1", "Running", "Blocked", "Blocked by Memory manager") in steps
    assert ("P1", "Blocked", "Ready", "Unblocked by Memory manager") in steps


def test_process_tab_draws_the_timeline_after_a_run():
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    app.sidebar.button[0].click().run()
    app.button(key="process-run-to-end").click().run()
    assert not app.exception
    assert "**Process state timeline**" in [m.value for m in app.markdown]
    assert "No state changes yet. Press Step or Run." not in [c.value for c in app.caption]
