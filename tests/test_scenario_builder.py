import pytest
import pandas as pd
from src.dashboard.views.scenario_builder import to_workload, validate_workload
from src.core.controller_api import RunConfig, ProcessConfig
from src.core.controller import RealController

def test_scenario_builder_validation_success():
    """Test that a valid workload DataFrame passes validation with zero errors."""
    valid_data = pd.DataFrame([
        {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 1},
        {"pid": "P2", "arrival_time": 2, "burst_time": 3, "priority": 2},
    ])
    errors = validate_workload(valid_data)
    assert len(errors) == 0, "Expected no validation errors for valid data."

def test_scenario_builder_validation_errors():
    """Test that invalid workload properties generate the correct error messages."""
    invalid_data = pd.DataFrame([
        {"pid": "P1", "arrival_time": -1, "burst_time": 0, "priority": 1},
        {"pid": "P1", "arrival_time": 2, "burst_time": 3, "priority": 2},
    ])
    errors = validate_workload(invalid_data)
    
    assert len(errors) == 3, "Expected exactly 3 validation errors."
    assert any("Arrival time must be >= 0" in e for e in errors), "Failed to catch negative arrival time."
    assert any("Burst time must be > 0" in e for e in errors), "Failed to catch zero/negative burst time."
    assert any("Process IDs must be unique" in e for e in errors), "Failed to catch duplicate PIDs."

def test_scenario_builder_empty_workload():
    """Test that an empty DataFrame is flagged as an error."""
    empty_data = pd.DataFrame()
    errors = validate_workload(empty_data)
    assert len(errors) == 1
    assert "Workload cannot be empty." in errors[0]

def test_scenario_builder_validation_missing_column():
    """Test that a table without a required column is rejected instead of crashing."""
    errors = validate_workload(pd.DataFrame([{"pid": "P1", "arrival_time": 0}]))
    assert errors == ["Missing required column(s): burst_time."]

def test_scenario_builder_validation_bad_values():
    """Test that text in number columns and blank PIDs are flagged."""
    errors = validate_workload(pd.DataFrame([
        {"pid": "P1", "arrival_time": "soon", "burst_time": 3},
        {"pid": None, "arrival_time": 0, "burst_time": 2},
    ]))
    assert errors == ["P1: Arrival time must be >= 0.", "Row 2: Process ID cannot be empty."]

def test_to_workload_fills_optional_fields():
    """Test that blank priority/owner get defaults so RealController can build Processes."""
    df = pd.DataFrame([{"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": None}])
    assert to_workload(df) == [
        {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 1.0, "owner_id": "default_user"}
    ]

def load_pids(config: RunConfig) -> list:
    controller = RealController()
    controller.load(config)
    return [p.pid for p in controller.engine.get_manager("Process").workload]

def test_real_controller_loads_custom_workload():
    """Test that the RealController uses the custom workload instead of the baseline."""
    custom_workload = [{"pid": "TEST-1", "arrival_time": 0, "burst_time": 10, "priority": 1, "owner_id": "test_user"}]
    assert load_pids(RunConfig(process=ProcessConfig(custom_workload=custom_workload))) == ["TEST-1"]

def test_real_controller_loads_baseline_without_custom_workload():
    """Test that the baseline workload still loads when no custom workload is given."""
    assert load_pids(RunConfig()) == ["P1", "P2", "P3", "P4"]
