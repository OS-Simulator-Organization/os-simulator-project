"""CSV/log export and test controls in the shared manager tab template."""

import csv
import io

from streamlit.testing.v1 import AppTest

from src.core.controller import RealController
from src.core.controller_api import RunConfig
from src.dashboard.manager_view import events_csv, metrics_csv
from src.dashboard.test_runner import run_tests

FIXTURE = '''
def test_passes():
    assert 1 + 1 == 2

def test_fails():
    assert 3 == 4
'''


def render_tab(view: str, load: bool):
    import importlib

    from src.core.controller import RealController
    from src.core.controller_api import RunConfig
    from src.dashboard.manager_view import render_manager_tab

    controller = RealController()
    events = []
    if load:
        controller.load(RunConfig())
        events = controller.run().events
    render_manager_tab(importlib.import_module(f"src.dashboard.views.{view}").VIEW, controller.snapshot(), events)


def run(view: str, load: bool) -> AppTest:
    return AppTest.from_function(render_tab, kwargs={"view": view, "load": load}, default_timeout=30).run()


def downloads(app: AppTest) -> dict:
    return {b.label: b for b in app.get("download_button")}


def test_event_log_and_metrics_export_are_disabled_before_a_run():
    buttons = downloads(run("memory", load=False))
    assert buttons["Download event log (CSV)"].disabled
    assert buttons["Download metrics (CSV)"].disabled


def test_event_log_and_metrics_export_are_enabled_after_a_run():
    buttons = downloads(run("file_system", load=True))
    assert not buttons["Download event log (CSV)"].disabled
    assert not buttons["Download metrics (CSV)"].disabled


def test_metrics_csv_has_units():
    controller = RealController()
    controller.load(RunConfig())
    rows = list(csv.DictReader(io.StringIO(metrics_csv("Memory", controller.run().snapshot))))
    assert {"page_faults", "page_hits", "page_fault_rate"} <= {r["metric"] for r in rows}
    assert next(r for r in rows if r["metric"] == "page_fault_rate")["unit"] == "%"


def test_events_csv_has_one_row_per_event():
    controller = RealController()
    controller.load(RunConfig())
    events = [e.to_dict() for e in controller.run().events if e.manager == "File"]
    rows = list(csv.DictReader(io.StringIO(events_csv(events))))
    assert len(rows) == len(events) > 0
    assert {"timestamp", "manager", "action", "outcome"} <= set(rows[0])


def test_memory_and_file_tabs_have_a_test_button():
    for view, key, label in (("memory", "Memory-run-tests", "Run memory tests"),
                             ("file_system", "File System-run-tests", "Run file system tests")):
        button = run(view, load=False).button(key=key)
        assert button.label == label
        assert not button.disabled


def test_run_tests_reports_each_result(tmp_path):
    fixture = tmp_path / "test_fixture.py"
    fixture.write_text(FIXTURE)
    result = run_tests([str(fixture)])
    assert not result.passed
    assert {r["test"].split("::")[-1]: r["result"] for r in result.results} == {"test_passes": "PASSED", "test_fails": "FAILED"}
    assert "1 failed, 1 passed" in result.summary
