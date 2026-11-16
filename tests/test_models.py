from src.core.models import (
    Device,
    DeviceRequest,
    DeviceRequestStatus,
    DeviceState,
    DeviceType,
)


def test_device_model_defaults():
    """Verifies Device dataclass fields and default AVAILABLE state."""
    dev = Device(device_id="DISK_1", device_type=DeviceType.DISK)
    assert dev.device_id == "DISK_1"
    assert dev.device_type == DeviceType.DISK
    assert dev.state == DeviceState.AVAILABLE
    assert dev.current_request_id is None


def test_device_request_model_fields_and_defaults():
    """Verifies DeviceRequest uses process_id (not pid) and initializes timing/status defaults."""
    req = DeviceRequest(
        request_id="REQ-10",
        device_id="PRINTER_1",
        process_id="P2",
        operation_type="PRINT",
    )
    assert req.request_id == "REQ-10"
    assert req.device_id == "PRINTER_1"
    assert req.process_id == "P2"
    assert req.operation_type == "PRINT"
    assert req.status == DeviceRequestStatus.PENDING
    assert req.arrival_time == 0.0
    assert req.waiting_time == 0.0
    assert req.start_time is None
    assert req.completion_time is None


def test_device_enums_cover_required_states():
    """Verifies required device types, device states, and request lifecycle statuses exist."""
    assert {DeviceType.DISK, DeviceType.PRINTER, DeviceType.KEYBOARD}.issubset(set(DeviceType))
    assert {DeviceState.AVAILABLE, DeviceState.BUSY, DeviceState.OFFLINE, DeviceState.ERROR} == set(DeviceState)
    assert {
        DeviceRequestStatus.PENDING,
        DeviceRequestStatus.IN_PROGRESS,
        DeviceRequestStatus.COMPLETED,
        DeviceRequestStatus.FAILED,
        DeviceRequestStatus.CANCELED,
    } == set(DeviceRequestStatus)