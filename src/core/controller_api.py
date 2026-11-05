"""Public API of the simulation controller, as used by the dashboard.

One tick is one simulated millisecond, always an int. Commands called in a
state that does not allow them raise ControllerStateError.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Protocol

from src.core.events import EventRecord

# Process maanger configuration
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
    aging_interval: int = 0
    custom_workload: List[Dict[str, Any]] = field(default_factory=list)
    
    def validate(self) -> List[str]:
            errors = []
            if self.policy is SchedulingPolicy.ROUND_ROBIN:
                if self.quantum_ms is None or self.quantum_ms < 1:
                    errors.append("Round Robin needs a time quantum of at least 1 ms.")
            elif self.quantum_ms is not None:
                errors.append("Time quantum only applies to Round Robin.")
            if self.context_switch_ms < 0:
                errors.append("Context switch cost cannot be negative.")
            return errors


# Memory manager configuration
class ReplacementAlgorithm(Enum):
    FIFO = "FIFO"
    LRU = "LRU"

@dataclass(frozen=True)
class MemoryConfig:
    algorithm: ReplacementAlgorithm = ReplacementAlgorithm.FIFO
    page_size: int = 4096
    total_frames: int = 4
    fault_latency: int = 2
    traces: Dict[str, List[Any]] = field(default_factory=lambda: {
        "P1": ["0x0040", "0x10A0", "0x0044", "0x20B0"]
    })
    def validate(self) -> List[str]:
        errors = []
        if self.page_size <= 0 or (self.page_size & (self.page_size - 1)) != 0:
            errors.append("Page size must be a positive integer and a power of 2.")
        if self.total_frames <= 0:
            errors.append("Total frames must be greater than 0.")
        if self.fault_latency < 0:
            errors.append("Fault latency cannot be negative.")
        return errors



@dataclass(frozen=True)
class RunConfig:
    """Every setting that affects a run's results. The run ID is assigned by load()."""
    seed: int = 0
    scenario_id: str = "baseline"
    process: ProcessConfig = field(default_factory=ProcessConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # Validate each manager config based on its own validate method
    def validate(self) -> List[str]:
        errors = []
        errors.extend(self.process.validate())
        errors.extend(self.memory.validate())
        return errors

   


class RunStatus(Enum):
    NOT_LOADED = "NOT_LOADED"
    READY = "READY"
    FINISHED = "FINISHED"
    PAUSED = "PAUSED"
    RUNNING = "RUNNING"


@dataclass(frozen=True)
class Metric:
    value: float
    unit: str


METRIC_UNITS = {
    # Process metrics
    "avg_waiting_time": "ms",
    "avg_turnaround_time": "ms",
    "avg_response_time": "ms",
    "cpu_utilization": "%",
    "throughput": "processes/s",
    "context_switches": "count",
    
    # Memory metrics
    "total_memory_references": "count",
    "page_hits": "count",
    "page_faults": "count",
    "eviction_count": "count",
    "page_fault_rate": "%",
    "page_hit_rate": "%",
    "total_cost": "ms",
    "avg_access_time": "ms",
    "total_frames": "count",
    "allocated_frames": "count",
    "free_frames": "count",
    "frame_utilization": "%",
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
