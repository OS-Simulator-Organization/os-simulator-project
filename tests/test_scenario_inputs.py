import pytest

from src.core.controller import RealController
from src.core.controller_api import FileConfig, RunConfig
from src.dashboard.scenario_inputs import DEFAULT_FILE_SCRIPT, KINDS, KINDS_BY_KEY, clean_rows, validate_rows

FILE_SCRIPT = KINDS_BY_KEY["file_script"]


def test_every_example_is_valid():
    for kind in KINDS:
        assert validate_rows(kind, list(kind.defaults)) == [], kind.key


def test_default_file_script_runs_with_twelve_plus_commands_and_six_intentional_errors():
    requests = [{k: v for k, v in row.items() if v is not None} for row in DEFAULT_FILE_SCRIPT]
    assert len(requests) >= 12
    controller = RealController()
    controller.load(RunConfig(files=FileConfig(io_requests=requests)))
    result = controller.run(until_tick=200)
    file_events = [e for e in result.events if e.manager == "File"]
    assert len(file_events) == len(requests)
    assert sum(e.outcome == "ERROR" for e in file_events) == 6
    assert result.snapshot.status.value == "FINISHED"


@pytest.mark.parametrize("row, error", [
    ({"arrival_time": -1}, "File script row 1: arrival_time cannot be negative."),
    ({"pid": "proc1"}, "File script row 1: pid must follow the 'P#' format (e.g. P1)."),
    ({"op": "FORMAT"}, "File script row 1: op must be one of CREATE, READ, WRITE, DELETE."),
    ({"path": "docs"}, "File script row 1: path must start with '/'."),
    ({"arrival_time": "soon"}, "File script row 1: arrival_time must be a whole number."),
])
def test_file_script_errors_are_specific(row, error):
    valid = {"arrival_time": 1, "pid": "P1", "op": "READ", "path": "/a.txt"}
    assert validate_rows(FILE_SCRIPT, [{**valid, **row}]) == [error]


def test_duplicate_ids_links_to_self_and_unknown_permissions_are_rejected():
    users = [{"user_id": "u1", "username": "a", "role": "USER", "permissions": "r"},
             {"user_id": "u1", "username": "b", "role": "USER", "permissions": "r, fly"}]
    assert validate_rows(KINDS_BY_KEY["users"], users) == [
        "Users and policies row 2: duplicate user_id 'u1'.",
        "Users and policies row 2: unknown permission(s) fly; use r, w, x, admin, network.",
    ]
    link = {"src": "NodeA", "dst": "NodeA", "bandwidth": 10, "latency": 1, "status": "UP"}
    assert validate_rows(KINDS_BY_KEY["links"], [link]) == ["Network links row 1: src and dst must be different nodes."]


def test_clean_rows_drops_empty_rows_and_makes_whole_numbers_int():
    assert clean_rows([{"a": 2.0, "b": "x"}, {"a": float("nan"), "b": " "}]) == [{"a": 2, "b": "x"}]
