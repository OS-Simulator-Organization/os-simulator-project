import pytest
from src.core.controller import RealController
from src.core.controller_api import RunConfig, RunStatus

def test_real_controller_file_and_memory_live_stepping():
    """Verifies that RealController steps Memory and File managers simultaneously."""
    controller = RealController()
    
    # 1. Load baseline scenario
    snapshot = controller.load(RunConfig(scenario_id="baseline"))
    assert snapshot.status == RunStatus.READY
    assert snapshot.tick == 0

    # 2. Step simulation clock once
    step_res = controller.step()
    
    # 3. Assert clock advanced
    assert step_res.snapshot.tick == 1

    # 4. Assert File and Memory metrics exist in the snapshot
    metrics = step_res.snapshot.metrics
    assert "Memory" in metrics, "Memory subsystem metrics missing from snapshot"
    assert "File" in metrics, "File subsystem metrics missing from snapshot"

    # 5. Step simulation continuously to verify event generation
    run_res = controller.run(until_tick=5)
    
    # Check that events were generated across managers
    event_managers = {evt.manager for evt in run_res.events}
    assert "Process" in event_managers or "Memory" in event_managers or "File" in event_managers

def test_file_manager_read_write_events():
    """Verifies that FileManager processes queued I/O requests when stepped."""
    controller = RealController()
    controller.load(RunConfig(scenario_id="baseline"))
    
    # Run through baseline ticks where file requests are scheduled
    res = controller.run(until_tick=4)
    
    file_events = [evt for evt in res.events if evt.manager == "File"]
    assert len(file_events) > 0, "FileManager failed to generate live event records"