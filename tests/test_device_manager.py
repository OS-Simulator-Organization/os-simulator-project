import pytest
from src.core.models import DeviceType, DeviceState, DeviceRequestStatus
from src.managers.DeviceManager import DeviceManager


def test_initial_three_device_types():
    """Verifies DISK_1, PRINTER_1, and KEYBOARD_1 initialize properly."""
    dev_mgr = DeviceManager()
    assert len(dev_mgr.devices) == 3
    assert dev_mgr.devices["DISK_1"]["type"] == DeviceType.DISK
    assert dev_mgr.devices["PRINTER_1"]["type"] == DeviceType.PRINTER
    assert dev_mgr.devices["KEYBOARD_1"]["type"] == DeviceType.KEYBOARD

    for dev in dev_mgr.devices.values():
        assert dev["status"] == DeviceState.AVAILABLE


def test_request_lifecycle_and_burst_duration():
    """Verifies requests take their full burst_time before completing and emit block/unblock events."""
    dev_mgr = DeviceManager()
    dev_mgr.configure({"disk_policy": "FCFS"})
    dev_mgr.load({
        "io_requests": [
            {"request_id": "REQ-1", "device_id": "DISK_1", "pid": "P1", "arrival_time": 1, "burst_time": 3, "operation_type": "READ:40"},
            {"request_id": "REQ-2", "device_id": "PRINTER_1", "pid": "P2", "arrival_time": 1, "burst_time": 2, "operation_type": "PRINT"},
            {"request_id": "REQ-3", "device_id": "KEYBOARD_1", "pid": "P3", "arrival_time": 1, "burst_time": 1, "operation_type": "INPUT"},
        ]
    })

    # Tick 0: Nothing arrives yet
    assert dev_mgr.step(0) == []

    # Tick 1: REQ-1 arrives and is scheduled on DISK_1 (others stay queued because step schedules 1 per tick)
    ev1 = dev_mgr.step(1)
    assert any(e.event_type == "DEVICE_BLOCKED" and e.entity_id == "P1" for e in ev1)
    assert dev_mgr.devices["DISK_1"]["status"] == DeviceState.BUSY
    assert len(dev_mgr.completed_requests) == 0

    # Tick 2: REQ-1 decrements (rem=2), REQ-2 scheduled on PRINTER_1
    ev2 = dev_mgr.step(2)
    assert any(e.event_type == "DEVICE_BLOCKED" and e.entity_id == "P2" for e in ev2)
    assert len(dev_mgr.completed_requests) == 0

    # Tick 3: REQ-1 decrements (rem=1), REQ-2 decrements (rem=1), REQ-3 scheduled on KEYBOARD_1
    ev3 = dev_mgr.step(3)
    assert any(e.event_type == "DEVICE_BLOCKED" and e.entity_id == "P3" for e in ev3)
    assert len(dev_mgr.completed_requests) == 0

    # Tick 4: REQ-1 (rem=0), REQ-2 (rem=0), and REQ-3 (rem=0) all complete
    ev4 = dev_mgr.step(4)
    completed_ids = {r.request_id for r in dev_mgr.completed_requests}
    assert completed_ids == {"REQ-1", "REQ-2", "REQ-3"}
    assert all(r.status == DeviceRequestStatus.COMPLETED for r in dev_mgr.completed_requests)
    assert all(dev["status"] == DeviceState.AVAILABLE for dev in dev_mgr.devices.values())
    assert len([e for e in ev4 if e.event_type == "DEVICE_COMPLETED"]) == 3


def test_disk_scheduling_sstf_vs_fcfs():
    """Verifies SSTF chooses the closest cylinder request rather than arrival order."""
    dev_mgr = DeviceManager()
    dev_mgr.configure({"disk_policy": "SSTF"})
    # Head starts at 0. Cylinder 20 is closer than Cylinder 150.
    dev_mgr.load({
        "io_requests": [
            {"request_id": "FAR", "device_id": "DISK_1", "pid": "P1", "arrival_time": 0, "burst_time": 1, "operation_type": "READ:150"},
            {"request_id": "NEAR", "device_id": "DISK_1", "pid": "P2", "arrival_time": 0, "burst_time": 1, "operation_type": "READ:20"},
        ]
    })

    dev_mgr.step(0)
    assert dev_mgr.active_requests["DISK_1"].request_id == "NEAR"
    assert dev_mgr.total_seek_distance == 20


def test_disk_scheduling_scan():
    """Verifies SCAN moves in current scan_direction and reverses when no requests remain ahead."""
    dev_mgr = DeviceManager()
    dev_mgr.configure({"disk_policy": "SCAN"})
    dev_mgr.devices["DISK_1"]["head_position"] = 50
    dev_mgr.devices["DISK_1"]["scan_direction"] = 1  # Moving upward

    dev_mgr.load({
        "io_requests": [
            {"request_id": "DOWN", "device_id": "DISK_1", "pid": "P1", "arrival_time": 0, "burst_time": 1, "operation_type": "READ:10"},
            {"request_id": "UP", "device_id": "DISK_1", "pid": "P2", "arrival_time": 0, "burst_time": 1, "operation_type": "READ:80"},
        ]
    })

    dev_mgr.step(0)
    assert dev_mgr.active_requests["DISK_1"].request_id == "UP"

    # Tick 1 finishes UP and schedules DOWN by reversing direction
    dev_mgr.step(1)
    assert dev_mgr.active_requests["DISK_1"].request_id == "DOWN"
    assert dev_mgr.devices["DISK_1"]["scan_direction"] == -1


def test_device_failure_and_recovery():
    """Verifies failing a busy device fails its active request and recovery restores availability."""
    dev_mgr = DeviceManager()
    dev_mgr.load({
        "io_requests": [
            {"request_id": "REQ-FAIL", "device_id": "PRINTER_1", "pid": "P1", "arrival_time": 0, "burst_time": 5, "operation_type": "PRINT"}
        ]
    })
    dev_mgr.step(0)
    assert dev_mgr.devices["PRINTER_1"]["status"] == DeviceState.BUSY

    dev_mgr.fail_device("PRINTER_1")
    assert dev_mgr.devices["PRINTER_1"]["status"] == DeviceState.ERROR
    assert dev_mgr.failure_count == 1
    assert dev_mgr.completed_requests[0].status == DeviceRequestStatus.FAILED

    dev_mgr.recover_device("PRINTER_1")
    assert dev_mgr.devices["PRINTER_1"]["status"] == DeviceState.AVAILABLE


def test_snapshot_serializes_enums_to_strings():
    """Verifies snapshot converts DeviceState and DeviceRequestStatus enums into plain strings for Pandas/Arrow."""
    dev_mgr = DeviceManager()
    dev_mgr.load({
        "io_requests": [
            {"request_id": "REQ-1", "device_id": "KEYBOARD_1", "pid": "P1", "arrival_time": 0, "burst_time": 1, "operation_type": "INPUT"}
        ]
    })
    dev_mgr.run()
    snap = dev_mgr.snapshot()

    assert isinstance(snap["devices"]["KEYBOARD_1"]["status"], str)
    assert snap["completed_requests"][0]["status"] == "COMPLETED"