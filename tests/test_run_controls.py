"""Usability tests for the shared simulation controls: stop condition, speed and reset."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller_api import RunStatus
from src.dashboard.run_controls import SPEED, STOP_AT, USE_STOP

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def loaded_app() -> AppTest:
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    return app.sidebar.button[0].click().run()


def snapshot(app: AppTest):
    return app.session_state.controller.snapshot()


def test_run_to_completion_stops_at_the_stop_tick():
    app = loaded_app()
    app.checkbox(key=USE_STOP).check().run()
    app.number_input(key=STOP_AT).set_value(7).run()
    app.button(key="memory-run-to-end").click().run()
    assert snapshot(app).tick == 7
    assert snapshot(app).status is RunStatus.PAUSED


def test_run_to_completion_finishes_without_a_stop_tick():
    app = loaded_app()
    app.button(key="file-run-to-end").click().run()
    assert snapshot(app).status is RunStatus.FINISHED


def test_stop_tick_input_is_disabled_until_turned_on():
    app = loaded_app()
    assert app.number_input(key=STOP_AT).disabled
    app.checkbox(key=USE_STOP).check().run()
    assert not app.number_input(key=STOP_AT).disabled


def test_speed_setting_is_shared_by_every_tab():
    app = loaded_app()
    app.select_slider(key=SPEED).set_value(4).run()
    assert app.session_state[SPEED] == 4
    assert not app.exception
