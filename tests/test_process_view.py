from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.core.controller_api import RunStatus

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def loaded_app() -> AppTest:
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=10).run()
    return app.sidebar.button[0].click().run()


def click(app: AppTest, key: str) -> AppTest:
    return app.button(key=key).click().run()


def snapshot(app: AppTest):
    return app.session_state.controller.snapshot()


def test_step_draws_the_chart_and_fills_the_event_log():
    app = click(loaded_app(), "process-step")
    assert not app.exception
    assert snapshot(app).tick == 1
    assert app.session_state.events
    assert app.get("arrow_vega_lite_chart")


def test_run_to_completion_records_every_event():
    app = click(loaded_app(), "process-run")
    assert snapshot(app).status is RunStatus.FINISHED
    assert len(app.session_state.events) > 1


def test_run_until_tick_pauses_then_step_continues():
    app = loaded_app()
    app.number_input(key="process-until-tick").set_value(3)
    app = click(app, "process-run-until")
    assert snapshot(app).status is RunStatus.PAUSED
    assert snapshot(app).tick == 3

    app = click(app, "process-step")
    assert snapshot(app).tick == 4


def test_pause_then_step_works():
    app = click(click(loaded_app(), "process-pause"), "process-step")
    assert snapshot(app).tick == 1


def test_reset_returns_to_tick_zero_with_the_same_config():
    app = click(loaded_app(), "process-run")
    config = snapshot(app).config
    app = click(app, "process-reset")
    assert snapshot(app).tick == 0
    assert snapshot(app).status is RunStatus.READY
    assert snapshot(app).config == config
    assert app.session_state.events == []
