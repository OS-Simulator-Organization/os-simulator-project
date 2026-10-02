import pytest

from src.core.models import DeviceState, DeviceRequestStatus
from src.managers.DeviceManager import DeviceManager

def test_device_status():
    dev_mgr = DeviceManager()
    for dev in dev_mgr.devices.values():
        assert dev["status"] == DeviceState.AVAILABLE

def test_request_Status():
    dev_mgr = DeviceManager()
    for req in dev_mgr.completed_requests:
        assert req.status == DeviceRequestStatus.COMPLETED