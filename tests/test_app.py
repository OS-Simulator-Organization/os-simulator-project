from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.dashboard.app import TABS
from src.dashboard.mock_controller import MockController
from src.dashboard.views import VIEWS


ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def run_app() -> AppTest:
    return AppTest.from_file(str(ENTRYPOINT), default_timeout=10).run()


def test_app_runs_without_errors():
    assert not run_app().exception


def test_every_area_has_a_tab():
    assert [tab.label for tab in run_app().tabs] == TABS


def test_sidebar_has_global_and_manager_sections():
    labels = [expander.label for expander in run_app().sidebar.expander]
    assert labels == ["Global", *[view.name for view in VIEWS]]


def test_controller_survives_reruns():
    app = run_app()
    controller = app.session_state.controller
    app.run()
    assert isinstance(controller, MockController)
    assert app.session_state.controller is controller


def test_manager_tabs_use_the_shared_template():
    subheaders = [subheader.value for subheader in run_app().subheader]
    for view in VIEWS:
        assert view.name in subheaders
