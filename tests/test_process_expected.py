"""Checks the process manager against the hand-worked Round Robin baseline in expected_results/."""

import json
from pathlib import Path

import pytest

from src.core.models import Process
from src.managers.process_manager import ProcessManager

EXPECTED = json.loads((Path(__file__).parent.parent / "expected_results" / "process_baseline.json").read_text())


@pytest.fixture(scope="module")
def manager():
    manager = ProcessManager()
    manager.configure({"policy": EXPECTED["policy"], "quantum_ms": EXPECTED["quantum_ms"],
                       "context_switch_ms": EXPECTED["context_switch_ms"]})
    manager.load([Process(owner_id="u", **process) for process in EXPECTED["workload"]])
    tick = 0
    while not manager.is_finished() and tick < 1000:
        manager.step(tick)
        tick += 1
    return manager


@pytest.mark.parametrize("pid", sorted(EXPECTED["per_process"]))
def test_round_robin_baseline_per_process(manager, pid):
    process = next(p for p in manager.completed_processes if p.pid == pid)
    actual = {"completion": process.completion_time, "turnaround": process.turnaround_time,
              "waiting": process.wait_time, "response": process.response_time}
    assert actual == EXPECTED["per_process"][pid]


def test_round_robin_baseline_averages(manager):
    metrics = manager.metrics()
    system = EXPECTED["system"]
    actual = {"makespan": metrics["makespan"], "completed_processes": metrics["completed_processes"],
              "avg_turnaround": metrics["avg_turnaround_time"], "avg_waiting": metrics["avg_waiting_time"],
              "avg_response": metrics["avg_response_time"]}
    assert actual == {key: system[key] for key in actual}
