import csv
import io
import json
import os

from src.core.controller import RealController
from src.core.controller_api import RunConfig
from src.dashboard.export import all_metrics_csv, config_json, events_csv, summary_report


def finished_run():
    controller = RealController()
    controller.load(RunConfig(seed=3))
    result = controller.run()
    return result.snapshot, result.events


def test_config_json_saves_enum_values_as_text():
    data = json.loads(config_json(RunConfig(seed=3)))
    assert data["seed"] == 3
    assert data["process"]["policy"] == "FCFS"
    assert data["memory"]["algorithm"] == "FIFO"


def test_full_event_log_keeps_every_event():
    _, events = finished_run()
    rows = list(csv.DictReader(io.StringIO(events_csv(events))))
    assert len(rows) == len(events)
    assert {r["manager"] for r in rows} >= {"Process", "Memory", "File"}


def test_all_metrics_csv_covers_every_manager_with_units():
    snapshot, _ = finished_run()
    rows = list(csv.DictReader(io.StringIO(all_metrics_csv(snapshot))))
    assert {r["manager"] for r in rows} == set(snapshot.metrics)
    assert next(r for r in rows if r["metric"] == "page_fault_rate")["unit"] == "%"


def test_summary_report_names_the_run_and_has_no_host_details():
    snapshot, events = finished_run()
    report = summary_report(snapshot, events)
    assert snapshot.run_id in report
    assert "## Memory" in report
    assert os.getcwd() not in report
    assert os.path.expanduser("~") not in report
