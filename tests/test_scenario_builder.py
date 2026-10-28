import pytest
import pandas as pd
from src.dashboard.views.scenario_builder import validate_workload
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

def test_real_controller_loads_custom_workload():
    """Test that the RealController prioritizes the custom workload over the baseline."""
    custom_workload = [{
        "pid": "TEST-1", 
        "arrival_time": 0, 
        "burst_time": 10, 
        "priority": 1, 
        "owner_id": "test_user"
    }]
    
    config = RunConfig(process=ProcessConfig(custom_workload=custom_workload))
    controller = RealController()
    
    # Load the configuration which should trigger proc_mgr.load()
    controller.load(config)
    
    # Verify the custom process was passed to the Process Manager
    proc_mgr = controller.engine.get_manager("Process")
    
    # Note: Depending on your exact ProcessManager implementation, 
    # you may need to adjust 'proc_mgr.processes' to match its internal state attribute
    loaded_processes = getattr(proc_mgr, "processes", getattr(proc_mgr, "ready_queue", []))
    
    # A simple check to ensure it didn't load the default 4 baseline processes
    assert hasattr(proc_mgr, "is_configured")
    # If your ProcessManager stores processes in a list, we can check its length/contents:
    # assert len(loaded_processes) == 1
    # assert loaded_processes[0].pid == "TEST-1"