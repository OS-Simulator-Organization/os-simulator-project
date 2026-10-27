import pytest
from src.core.importers import load_and_validate_processes, ValidationError
from src.core.models import ProcessState


def test_valid_processes_load():
    processes = load_and_validate_processes("data/processes.csv")
    assert len(processes) == 6
    assert processes[0].pid == "P1"
    assert processes[0].burst_time == 8
    assert processes[0].remaining_time == 8
    assert processes[0].state == ProcessState.NEW


def test_duplicate_pid_error(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("pid,owner_id,arrival_time,burst_time,priority\nP1,u1,0,5,1\nP1,u2,2,3,2\n")
    try:
        load_and_validate_processes(str(csv_file))
        assert False
    except ValidationError as err:
        assert "Duplicate process ID" in str(err)


def test_negative_arrival_error(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("pid,owner_id,arrival_time,burst_time,priority\nP1,u1,-1,5,1\n")
    try:
        load_and_validate_processes(str(csv_file))
        assert False
    except ValidationError as err:
        assert "arrival_time cannot be negative" in str(err)


def test_invalid_burst_error(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("pid,owner_id,arrival_time,burst_time,priority\nP1,u1,0,0,1\n")
    try:
        load_and_validate_processes(str(csv_file))
        assert False
    except ValidationError as err:
        assert "burst_time must be greater than 0" in str(err)


def test_missing_column_error(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("pid,arrival_time,priority\nP1,0,1\n")
    try:
        load_and_validate_processes(str(csv_file))
        assert False
    except ValidationError as err:
        assert "Missing required column" in str(err)