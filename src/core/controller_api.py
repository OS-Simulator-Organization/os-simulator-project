"""Public API of the simulation controller, as used by the dashboard.

One tick is one simulated millisecond, always an int. Commands called in a
state that does not allow them raise ControllerStateError.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Protocol

from src.core.events import EventRecord


class SchedulingPolicy(Enum):
    FCFS = "FCFS"
    SJF = "SJF"
    SRTF = "SRTF"
    ROUND_ROBIN = "ROUND_ROBIN"
    PRIORITY = "PRIORITY"


@dataclass(frozen=True)
class ProcessConfig:
    policy: SchedulingPolicy = SchedulingPolicy.FCFS
    quantum_ms: Optional[int] = None
    context_switch_ms: int = 0


@dataclass(frozen=True)
class RunConfig:
    """Every setting that affects a run's results. The run ID is assigned by load()."""

    seed: int = 0
    scenario_id: str = "baseline"
    process: ProcessConfig = field(default_factory=ProcessConfig)

    def validate(self) -> List[str]:
        errors = []
        p = self.process
        if p.policy is SchedulingPolicy.ROUND_ROBIN:
            if p.quantum_ms is None or p.quantum_ms < 1:
                errors.append("Round Robin needs a time quantum of at least 1 ms.")
        elif p.quantum_ms is not None:
            errors.append("Time quantum only applies to Round Robin.")
        if p.context_switch_ms < 0:
            errors.append("Context switch cost cannot be negative.")
        return errors


class RunStatus(Enum):
    NOT_LOADED = "NOT_LOADED"
    READY = "READY"
    FINISHED = "FINISHED"


@dataclass(frozen=True)
class Metric:
    value: float
    unit: str


PROCESS_METRIC_UNITS = {
    "avg_waiting_time": "ms",
    "avg_turnaround_time": "ms",
    "avg_response_time": "ms",
    "cpu_utilization": "%",
    "throughput": "processes/s",
    "context_switches": "count",
}


@dataclass(frozen=True)
class Snapshot:
    run_id: str
    tick: int
    status: RunStatus
    config: RunConfig
    metrics: Dict[str, Dict[str, Metric]]


@dataclass(frozen=True)
class StepResult:
    snapshot: Snapshot
    events: List[EventRecord]


class ControllerStateError(RuntimeError):
    pass


class ControllerAPI(Protocol):
    supported_policies: FrozenSet[SchedulingPolicy]

    def load(self, config: RunConfig) -> Snapshot:
        """Start a new run at tick 0. Raises ValueError if config.validate() fails
        or its policy is not in supported_policies."""
        ...

    def step(self) -> StepResult:
        """Advance one tick. Requires READY."""
        ...

    def run(self, until_tick: Optional[int] = None) -> StepResult:
        """Step until FINISHED or until_tick. Requires READY."""
        ...

    def reset(self) -> Snapshot:
        """Restart the current config at tick 0. Requires a loaded run."""
        ...

    def snapshot(self) -> Snapshot:
        ...
