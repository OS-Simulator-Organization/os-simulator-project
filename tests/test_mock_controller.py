import pytest

from src.core.controller_api import (
    PROCESS_METRIC_UNITS,
    ControllerAPI,
    ControllerStateError,
    ProcessConfig,
    RunConfig,
    RunStatus,
    SchedulingPolicy,
)
from src.dashboard.mock_controller import PROCESS_TIMELINE, MockController


def loaded() -> MockController:
    controller = MockController()
    controller.load(RunConfig())
    return controller


def metric_values(snapshot):
    return {key: metric.value for key, metric in snapshot.metrics["Process"].items()}


def test_satisfies_controller_api():
    controller: ControllerAPI = MockController()
    for name in ("load", "step", "run", "reset", "snapshot"):
        assert callable(getattr(controller, name))
    assert controller.supported_policies == {SchedulingPolicy.FCFS}


def test_starts_not_loaded():
    snapshot = MockController().snapshot()
    assert snapshot.status is RunStatus.NOT_LOADED
    assert snapshot.tick == 0
    assert snapshot.metrics == {}


@pytest.mark.parametrize("command", ["step", "run", "reset"])
def test_commands_before_load_raise(command):
    with pytest.raises(ControllerStateError):
        getattr(MockController(), command)()


def test_load_rejects_invalid_config():
    config = RunConfig(process=ProcessConfig(context_switch_ms=-1))
    with pytest.raises(ValueError):
        MockController().load(config)


@pytest.mark.parametrize("policy", [p for p in SchedulingPolicy if p is not SchedulingPolicy.FCFS])
def test_load_rejects_unsupported_policy(policy):
    quantum = 4 if policy is SchedulingPolicy.ROUND_ROBIN else None
    config = RunConfig(process=ProcessConfig(policy, quantum_ms=quantum))
    with pytest.raises(ValueError, match="not supported"):
        MockController().load(config)


def test_load_starts_ready_at_tick_zero():
    config = RunConfig(seed=7)
    snapshot = MockController().load(config)
    assert snapshot.status is RunStatus.READY
    assert snapshot.tick == 0
    assert snapshot.config == config
    assert snapshot.run_id


def test_first_step_admits_and_dispatches_p1():
    result = loaded().step()
    assert result.snapshot.tick == 1
    assert [(e.entity_id, e.new_state) for e in result.events] == [("P1", "READY"), ("P1", "RUNNING")]


def test_step_returns_only_new_events():
    controller = loaded()
    controller.step()
    assert [e.entity_id for e in controller.step().events] == ["P2"]


def test_run_finishes_with_every_event():
    result = loaded().run()
    assert result.snapshot.status is RunStatus.FINISHED
    assert result.snapshot.tick == len(PROCESS_TIMELINE)
    assert len(result.events) == sum(len(events) for events in PROCESS_TIMELINE)


def test_run_until_tick_stops_there():
    result = loaded().run(until_tick=3)
    assert result.snapshot.tick == 3
    assert result.snapshot.status is RunStatus.READY
    assert [e.entity_id for e in result.events] == ["P1", "P1", "P2", "P3"]


def test_run_until_past_tick_does_nothing():
    controller = loaded()
    controller.run(until_tick=5)
    result = controller.run(until_tick=2)
    assert result.events == []
    assert result.snapshot.tick == 5


@pytest.mark.parametrize("command", ["step", "run"])
def test_commands_after_finish_raise(command):
    controller = loaded()
    controller.run()
    with pytest.raises(ControllerStateError):
        getattr(controller, command)()


def test_reset_replays_the_same_run():
    controller = loaded()
    first = [e.to_dict() for e in controller.run().events]
    snapshot = controller.reset()
    assert snapshot.tick == 0
    assert snapshot.status is RunStatus.READY
    assert [e.to_dict() for e in controller.run().events] == first


def test_each_load_and_reset_gets_a_new_run_id():
    controller = MockController()
    ids = [controller.load(RunConfig()).run_id, controller.reset().run_id, controller.load(RunConfig()).run_id]
    assert len(set(ids)) == 3


def test_load_after_finish_starts_over():
    controller = loaded()
    controller.run()
    assert controller.load(RunConfig(seed=1)).status is RunStatus.READY


def test_events_match_schema_and_never_run_ahead_of_the_clock():
    controller = loaded()
    while controller.snapshot().status is RunStatus.READY:
        result = controller.step()
        for event in result.events:
            assert event.validate()
            assert event.timestamp <= result.snapshot.tick


def test_each_process_follows_its_lifecycle_in_order():
    states = {}
    for event in loaded().run().events:
        assert event.previous_state == states.get(event.entity_id, "NEW")
        states[event.entity_id] = event.new_state
    assert set(states.values()) == {"TERMINATED"}


def test_only_one_process_runs_at_a_time():
    running = set()
    for event in loaded().run().events:
        if event.new_state == "RUNNING":
            assert not running
            running.add(event.entity_id)
        elif event.new_state == "TERMINATED":
            running.remove(event.entity_id)


def test_metrics_report_every_key_with_units_at_every_tick():
    controller = loaded()
    while controller.snapshot().status is RunStatus.READY:
        metrics = controller.step().snapshot.metrics["Process"]
        assert {key: m.unit for key, m in metrics.items()} == PROCESS_METRIC_UNITS


def test_metrics_at_load_are_zero():
    assert set(metric_values(MockController().load(RunConfig())).values()) == {0}


def test_metrics_mid_run():
    values = metric_values(loaded().run(until_tick=5).snapshot)
    assert values == pytest.approx({
        "avg_waiting_time": 0,
        "avg_turnaround_time": 4,
        "avg_response_time": 1.5,
        "cpu_utilization": 100,
        "throughput": 200,
        "context_switches": 1,
    })


def test_metrics_at_finish():
    values = metric_values(loaded().run().snapshot)
    assert values == pytest.approx({
        "avg_waiting_time": 8 / 3,
        "avg_turnaround_time": 17 / 3,
        "avg_response_time": 8 / 3,
        "cpu_utilization": 100,
        "throughput": 3000 / 9,
        "context_switches": 2,
    })
