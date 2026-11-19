import pytest
from src.core.controller import SimulationController, RealController
from src.core.controller_api import (
    ControllerStateError,
    DeviceConfig,
    DiskPolicy,
    METRIC_UNITS,
    ProcessConfig,
    RunConfig,
    RunStatus,
    SchedulingPolicy,
    NetworkConfig,
    NetworkPolicy
)
from src.core.models import ProcessState


def rr(quantum_ms):
    return RunConfig(process=ProcessConfig(SchedulingPolicy.ROUND_ROBIN, quantum_ms))


def test_identical_configs_are_equal():
    assert rr(4) == rr(4)
    assert rr(4) != rr(5)


def test_default_config_is_valid():
    assert RunConfig().validate() == []


def test_round_robin_requires_quantum():
    assert rr(None).validate()
    assert rr(0).validate()
    assert rr(4).validate() == []


def test_quantum_rejected_for_non_round_robin():
    config = RunConfig(process=ProcessConfig(SchedulingPolicy.FCFS, quantum_ms=4))
    assert config.validate()


def test_negative_context_switch_rejected():
    config = RunConfig(process=ProcessConfig(context_switch_ms=-1))
    assert config.validate()


def test_device_config_and_metric_units():
    """Verifies DeviceConfig defaults, validation, and device metric unit registrations."""
    cfg = DeviceConfig()
    assert cfg.disk_policy == DiskPolicy.FCFS
    assert cfg.validate() == []

    assert METRIC_UNITS["device_throughput"] == "req/s"
    assert METRIC_UNITS["total_seek_distance"] == "cylinders"
    assert METRIC_UNITS["device_failures"] == "count"


def test_real_controller_state_transitions():
    """Verifies RealController rejects steps when NOT_LOADED and transitions to READY after load()."""
    controller = RealController()
    assert controller.status == RunStatus.NOT_LOADED

    with pytest.raises(ControllerStateError):
        controller.step()

    with pytest.raises(ControllerStateError):
        controller.run()

    config = RunConfig(seed=42, process=ProcessConfig(policy=SchedulingPolicy.FCFS))
    snap = controller.load(config)

    assert snap.status == RunStatus.READY
    assert controller.status == RunStatus.READY
    assert snap.tick == 0
    assert "Device" in snap.metrics


def test_baseline_loads_three_device_requests_without_double_stepping():
    """Verifies baseline loads DISK_1, PRINTER_1, KEYBOARD_1 and respects burst durations (no double step)."""
    controller = RealController()
    snap = controller.load(RunConfig(scenario_id="baseline"))

    dev_mgr = controller.engine.get_manager("Device")
    assert len(dev_mgr.request_queue) == 3
    assert {r.device_id for r in dev_mgr.request_queue} == {"DISK_1", "PRINTER_1", "KEYBOARD_1"}

    # Step 3 ticks (clocks 0, 1, 2). REQ-1 arrives at 1 with burst_time=3, so it must NOT be finished at tick 2.
    controller.step()  # clock 0
    controller.step()  # clock 1 -> REQ-1 starts (rem=3)
    controller.step()  # clock 2 -> REQ-1 decrements (rem=2)
    assert len(dev_mgr.completed_requests) == 0

    # Step through completion of all 3 requests
    for _ in range(5):
        controller.step()

    assert len(dev_mgr.completed_requests) == 5

def test_network_config_and_metric_units():
    """Verifies NetworkConfig defaults, validation, and network metric unit registrations."""
    cfg = NetworkConfig()
    assert cfg.queue_policy == NetworkPolicy.FIFO
    assert cfg.buffer_capacity == 16
    assert cfg.validate() == []

    bad_cfg = NetworkConfig(buffer_capacity=0)
    assert bad_cfg.validate()

    assert METRIC_UNITS["delivered_packets"] == "count"
    assert METRIC_UNITS["dropped_packets"] == "count"
    assert METRIC_UNITS["avg_network_latency"] == "ms"


def test_real_controller_loads_and_steps_network_manager():
    """Verifies RealController registers and steps NetworkManager during baseline runs."""
    controller = RealController()
    config = RunConfig(
        seed=42,
        scenario_id="baseline",
        network=NetworkConfig(queue_policy=NetworkPolicy.PRIORITY),
    )
    snap = controller.load(config)

    assert "Network" in snap.metrics
    net_mgr = controller.engine.get_manager("Network")
    assert net_mgr is not None
    assert net_mgr.queue_policy == "PRIORITY"

    controller.step()
    assert len(net_mgr.delivered_packets) + len(net_mgr.dropped_packets) == 1
