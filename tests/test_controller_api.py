import pytest
from src.core.controller import SimulationController, RealController
from src.core.controller_api import (
    ControllerStateError,
    ProcessConfig,
    RunConfig,
    RunStatus,
    SchedulingPolicy,
)


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


def test_real_controller_state_transitions():
    """Verifies that RealController rejects steps when NOT_LOADED and transitions to READY after load()."""
    controller = RealController()
    assert controller.status == RunStatus.NOT_LOADED

    # Attempting to step or run without loading should raise ControllerStateError
    with pytest.raises(ControllerStateError):
        controller.step()

    with pytest.raises(ControllerStateError):
        controller.run()

    # Load configuration
    config = RunConfig(seed=42, process=ProcessConfig(policy=SchedulingPolicy.FCFS))
    snap = controller.load(config)

    assert snap.status == RunStatus.READY
    assert controller.status == RunStatus.READY
    assert snap.tick == 0