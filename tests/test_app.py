from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.dashboard.app import MANAGERS, TABS
from src.dashboard.mock_controller import MockController


ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def run_app() -> AppTest:
    return AppTest.from_file(str(ENTRYPOINT)).run()


def test_app_runs_without_errors():
    assert not run_app().exception


def test_every_area_has_a_tab():
    assert [tab.label for tab in run_app().tabs] == TABS


def test_sidebar_has_global_and_manager_sections():
    labels = [expander.label for expander in run_app().sidebar.expander]
    assert labels == ["Global", *MANAGERS]


def test_controller_survives_reruns():
    app = run_app()
    controller = app.session_state.controller
    app.run()
    assert isinstance(controller, MockController)
    assert app.session_state.controller is controller
