import pytest

from src.core.models import Process
from src.managers.process_manager import ProcessManager


def make_manager() -> ProcessManager:
    manager = ProcessManager()
    manager.configure({"policy": "FCFS"})
    manager.load([
        Process(pid="P1", owner_id="user_admin", arrival_time=1, burst_time=3, priority=1),
        Process(pid="P2", owner_id="user_admin", arrival_time=2, burst_time=4, priority=2),
        Process(pid="P3", owner_id="user_admin", arrival_time=9, burst_time=1, priority=3),
    ])
    return manager


def test_utilization_stays_within_bounds_at_every_tick():
    manager = make_manager()
    observed = []
    for _ in range(20):
        if manager.is_finished():
            break
        manager.step(manager.current_time + 1)
        metrics = manager.metrics()
        observed.append(metrics["utilization"])
        assert 0.0 <= metrics["utilization"] <= 100.0
    else:
        pytest.fail("simulation did not finish within 20 ticks")

    assert manager.is_finished()
    # The first tick is busy even though no process has completed yet; the
    # denominator is elapsed time, so it is 100% rather than 0%.
    assert observed[0] == pytest.approx(100.0)
    assert manager.metrics()["utilization"] == pytest.approx(100.0 * 8 / len(manager.gantt_ticks))


def test_throughput_is_reported_per_second():
    manager = make_manager()
    manager.run()

    assert len(manager.completed_processes) == 3
    metrics = manager.metrics()
    assert metrics["throughput"] == pytest.approx(1000.0 * 3 / len(manager.gantt_ticks))
    assert metrics["throughput"] > 0
