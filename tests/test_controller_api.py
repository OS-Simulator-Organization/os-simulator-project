from src.core.controller_api import ProcessConfig, RunConfig, SchedulingPolicy


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
