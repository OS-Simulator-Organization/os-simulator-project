from src.core.models import Process
from src.managers.process_manager import ProcessManager


def make_manager(processes, policy="FCFS"):
    manager = ProcessManager()
    manager.configure({"policy": policy})
    manager.load(processes)
    return manager


def baseline():
    return [
        Process(pid="P1", owner_id="u", arrival_time=0, burst_time=8, priority=3),
        Process(pid="P2", owner_id="u", arrival_time=1, burst_time=4, priority=1),
        Process(pid="P3", owner_id="u", arrival_time=2, burst_time=9, priority=4),
        Process(pid="P4", owner_id="u", arrival_time=3, burst_time=5, priority=2),
    ]


def test_utilization_stays_within_bounds_every_tick():
    manager = make_manager(baseline())
    for tick in range(26):
        manager.step(tick)
        assert 0 <= manager.metrics()["utilization"] <= 100, f"tick {tick}"


def test_utilization_is_busy_share_of_elapsed_ticks():
    # The CPU busy since tick 0 reads 100% even before any process finishes.
    manager = make_manager(baseline())
    for tick in range(5):
        manager.step(tick)
    assert manager.metrics()["utilization"] == 100


def test_idle_ticks_lower_utilization_and_throughput():
    # Idle for ticks 0-1, then runs P1 for ticks 2-3: 2 busy of 4 elapsed, 1 process in 4 ms.
    manager = make_manager([Process(pid="P1", owner_id="u", arrival_time=2, burst_time=2, priority=1)])
    for tick in range(4):
        manager.step(tick)
    metrics = manager.metrics()
    assert metrics["utilization"] == 50
    assert metrics["throughput"] == 250
