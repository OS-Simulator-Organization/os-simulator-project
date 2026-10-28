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
    assert app.get("vega_lite_chart")


def test_run_to_completion_records_every_event():
    app = click(loaded_app(), "process-run-to-end")
    assert snapshot(app).status is RunStatus.FINISHED
    assert len(app.session_state.events) > 1


def test_run_steps_on_its_own_until_paused():
    # The once-per-second timer doesn't fire under AppTest, so only Run's first step shows here.
    app = click(loaded_app(), "process-run")
    assert app.session_state["process-autoplay"]
    assert snapshot(app).tick == 1

    app = click(app, "process-pause")
    assert not app.session_state["process-autoplay"]


def test_pause_then_step_works():
    app = click(click(click(loaded_app(), "process-run"), "process-pause"), "process-step")
    assert snapshot(app).tick == 2


def test_reset_returns_to_tick_zero_with_the_same_config():
    app = click(loaded_app(), "process-run-to-end")
    config = snapshot(app).config
    app = click(app, "process-reset")
    assert snapshot(app).tick == 0
    assert snapshot(app).status is RunStatus.READY
    assert snapshot(app).config == config
    assert app.session_state.events == []
