from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller import RealController
from src.core.controller_api import RunConfig
from src.core.events import EventRecord
from src.dashboard.overview import ACTIVE, NOT_CONNECTED, WAITING, event_summary, manager_cards

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def event(manager, outcome):
    return EventRecord(timestamp=0, manager=manager, event_type="E", entity_id="x", action="A",
                       previous_state="", new_state="", outcome=outcome)


def cards_by_name(controller, events=()):
    return {c["manager"]: c for c in manager_cards(controller.snapshot(), list(events), list(controller.engine.managers))}


def test_registered_managers_wait_until_a_run_is_loaded():
    cards = cards_by_name(RealController())
    assert cards["Process"]["status"] == WAITING
    assert cards["Parallel"]["status"] == NOT_CONNECTED


def test_registered_managers_are_active_after_load():
    controller = RealController()
    controller.load(RunConfig())
    cards = cards_by_name(controller)
    assert cards["Memory"]["status"] == ACTIVE
    assert cards["Security"]["status"] == NOT_CONNECTED


def test_cards_count_events_and_problems():
    cards = cards_by_name(RealController(), [event("File", "ERROR"), event("File", "SUCCESS")])
    assert (cards["File System"]["events"], cards["File System"]["problems"]) == (2, 1)


def test_event_summary_counts_outcomes_per_manager():
    assert event_summary([event("File", "ERROR"), event("File", "SUCCESS"), event("Process", "SUCCESS")]) == [
        {"manager": "File", "ERROR": 1, "SUCCESS": 1, "total": 2},
        {"manager": "Process", "ERROR": 0, "SUCCESS": 1, "total": 1},
    ]


def test_overview_shows_run_state_and_warnings_after_load():
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert {m.label for m in app.metric} >= {"Current time", "Active scenario", "Run state", "Seed"}
    assert any("Not connected to the controller yet" in w.value for w in app.warning)
