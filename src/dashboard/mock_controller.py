"""Scripted stand-in for SimulationController so the dashboard can be built
before the real managers work. Only the process manager is scripted so far with
a fixed FCFS run of three processes. The seed and scenario do not change the output.
"""

from typing import Dict, List, Optional

from src.core.controller_api import (
    PROCESS_METRIC_UNITS,
    ControllerStateError,
    Metric,
    RunConfig,
    RunStatus,
    SchedulingPolicy,
    Snapshot,
    StepResult,
)
from src.core.events import EventRecord
from src.core.models import ProcessState

NEW, READY, RUNNING, TERMINATED = (
    ProcessState.NEW.value,
    ProcessState.READY.value,
    ProcessState.RUNNING.value,
    ProcessState.TERMINATED.value,
)

ARRIVE = ("PROCESS_ARRIVE", "ADMIT", NEW, READY)
DISPATCH = ("PROCESS_DISPATCH", "DISPATCH", READY, RUNNING)
TERMINATE = ("PROCESS_TERMINATE", "EXIT", RUNNING, TERMINATED)

# Events produced by each step, indexed by the tick being processed. A step covers
# [tick, tick + 1), so a process that finishes during it terminates at tick + 1.
PROCESS_TIMELINE = [
    [(0, "P1", ARRIVE), (0, "P1", DISPATCH)],
    [(1, "P2", ARRIVE)],
    [(2, "P3", ARRIVE)],
    [(4, "P1", TERMINATE)],
    [(4, "P2", DISPATCH)],
    [],
    [(7, "P2", TERMINATE)],
    [(7, "P3", DISPATCH)],
    [(9, "P3", TERMINATE)],
]


def _process_event(timestamp: int, pid: str, kind: tuple) -> EventRecord:
    event_type, action, previous_state, new_state = kind
    return EventRecord(
        timestamp=timestamp,
        manager="Process",
        event_type=event_type,
        entity_id=pid,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        outcome="SUCCESS",
        explanatory_message=f"{pid}: {previous_state} -> {new_state}",
    )


class MockController:
    supported_policies = frozenset({SchedulingPolicy.FCFS})

    def __init__(self):
        self._config: Optional[RunConfig] = None
        self._run_count = 0
        self._run_id = ""
        self._tick = 0
        self._events: List[EventRecord] = []

    def load(self, config: RunConfig) -> Snapshot:
        errors = config.validate()
        if config.process.policy not in self.supported_policies:
            errors.append(f"{config.process.policy.value} is not supported yet.")
        if errors:
            raise ValueError(" ".join(errors))
        self._config = config
        return self._start()

    def step(self) -> StepResult:
        self._require(RunStatus.READY)
        new_events = [_process_event(timestamp, pid, kind) for timestamp, pid, kind in PROCESS_TIMELINE[self._tick]]
        self._events.extend(new_events)
        self._tick += 1
        return StepResult(self.snapshot(), new_events)

    def run(self, until_tick: Optional[int] = None) -> StepResult:
        self._require(RunStatus.READY)
        new_events = []
        while self._status() is RunStatus.READY and (until_tick is None or self._tick < until_tick):
            new_events.extend(self.step().events)
        return StepResult(self.snapshot(), new_events)

    def reset(self) -> Snapshot:
        if self._config is None:
            raise ControllerStateError("reset() requires a loaded run.")
        return self._start()

    def snapshot(self) -> Snapshot:
        return Snapshot(
            run_id=self._run_id,
            tick=self._tick,
            status=self._status(),
            config=self._config or RunConfig(),
            metrics={"Process": self._process_metrics()} if self._config else {},
        )

    def _start(self) -> Snapshot:
        self._run_count += 1
        self._run_id = f"mock-{self._run_count}"
        self._tick = 0
        self._events = []
        return self.snapshot()

    def _status(self) -> RunStatus:
        if self._config is None:
            return RunStatus.NOT_LOADED
        if self._tick >= len(PROCESS_TIMELINE):
            return RunStatus.FINISHED
        return RunStatus.READY

    def _require(self, status: RunStatus) -> None:
        if self._status() is not status:
            raise ControllerStateError(f"Requires {status.value}, run is {self._status().value}.")

    def _process_metrics(self) -> Dict[str, Metric]:
        times: Dict[str, Dict[str, int]] = {}
        for e in self._events:
            times.setdefault(e.entity_id, {})[e.event_type] = e.timestamp

        dispatched = [t for t in times.values() if "PROCESS_DISPATCH" in t]
        finished = [t for t in dispatched if "PROCESS_TERMINATE" in t]
        turnaround = [t["PROCESS_TERMINATE"] - t["PROCESS_ARRIVE"] for t in finished]
        burst = [t["PROCESS_TERMINATE"] - t["PROCESS_DISPATCH"] for t in finished]
        busy = sum(t.get("PROCESS_TERMINATE", self._tick) - t["PROCESS_DISPATCH"] for t in dispatched)

        values = {
            "avg_waiting_time": _mean([ta - b for ta, b in zip(turnaround, burst)]),
            "avg_turnaround_time": _mean(turnaround),
            "avg_response_time": _mean([t["PROCESS_DISPATCH"] - t["PROCESS_ARRIVE"] for t in dispatched]),
            "cpu_utilization": 100 * busy / self._tick if self._tick else 0.0,
            "throughput": 1000 * len(finished) / self._tick if self._tick else 0.0,
            "context_switches": max(len(dispatched) - 1, 0),
        }
        return {key: Metric(values[key], unit) for key, unit in PROCESS_METRIC_UNITS.items()}


def _mean(values: List[int]) -> float:
    return sum(values) / len(values) if values else 0.0
