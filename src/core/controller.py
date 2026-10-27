import heapq
import uuid
import random

from typing import Dict, List, Any, Optional, Set
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import Process
from src.core.importers import load_and_validate_processes

from src.core.controller_api import (
    #Eventually, we can import all the necessary classes from controller_api.py here. For now, we will import the ones we need.
    ControllerAPI,
    ControllerStateError,
    Metric,
    ProcessConfig,
    RunConfig,
    RunStatus,
    SchedulingPolicy,
    Snapshot,
    StepResult,
)

from src.managers.process_manager import ProcessManager

class SimulationController:
    """
    Central Discrete-Event Engine maintaining simulation clock, global run state,
    and event synchronization across all manager modules.
    """

    def __init__(self, seed: int = 42):
        self.clock: int = 0 # Simulation clock in milliseconds set to int to match the requirement that one tick is one simulated millisecond
        self.seed: int = seed
        self.is_running: bool = False
        self.event_queue: List[EventRecord] = []
        self.managers: Dict[str, BaseManager] = {}
        self.global_event_log: List[EventRecord] = []

    def schedule_event(self, event: EventRecord) -> None:
        """Pushes an event onto the priority queue (ordered by timestamp)."""
        heapq.heappush(self.event_queue, event)

    def set_seed(self, seed: int) -> None:
        """Sets the random seed for reproducibility of stochastic events."""
        self.seed = seed
        random.seed(seed)
    
    def register_manager(self, manager: BaseManager) -> None:
        """Registers an OS Manager module adhering to the BaseManager interface."""
        self.managers[manager.name] = manager

    def get_manager(self, name: str) -> Optional[BaseManager]:
        """Retrieves a registered manager instance by name."""
        return self.managers.get(name)

    def configure_all(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """Configures all registered managers using a mapped configuration dictionary."""
        for manager_name, config in configs.items():
            if manager_name in self.managers:
                self.managers[manager_name].configure(config)

    def step(self) -> List[EventRecord]:
        """
        Advances simulation clock by 1 tick per step call and executes step()
        across all registered managers. Gathers and returns newly generated EventRecords.
        """
        step_events: List[EventRecord] = []


        # 1. Pop and process all events scheduled for current or earlier timestamp
        while self.event_queue and self.event_queue[0].timestamp <= self.clock:
            evt = heapq.heappop(self.event_queue)
            self.global_event_log.append(evt)
            step_events.append(evt)      

        # 2. Step through each manager deterministically for current clock
        for manager in self.managers.values():
            new_events = manager.step(self.clock)
            for evt in new_events:
                if evt.timestamp > self.clock:
                    self.schedule_event(evt)     # future event, schedule for later  
                else:
                    self.global_event_log.append(evt)
                    step_events.append(evt)

       
        self.clock += 1
          
        return step_events

    def run(self, max_ticks: int = 100) -> List[EventRecord]:
        """Runs the simulation continuously until max ticks or empty queue."""
        self.is_running = True
        all_run_events: List[EventRecord] = []

        start_tick = self.clock
        while self.is_running and (self.clock - start_tick) < max_ticks:
            if not self.event_queue and all(getattr(m, 'is_idle', lambda: True)() for m in self.managers.values()):
                # Engine stopping condition if all managers are idle and queue is empty
                break
            events = self.step()
            all_run_events.extend(events)

        self.is_running = False
        return all_run_events
    def pause(self) -> None:
        self.is_running =False
    

    def reset(self) -> None:
        """Resets the simulation engine clock, event queue, logs, and manager states."""
        self.clock = 0
        self.is_running = False
        self.event_queue.clear()
        self.global_event_log.clear()
        self.set_seed(self.seed)
        
        for manager in self.managers.values():
            manager.reset()
    

    def get_system_snapshot(self) -> Dict[str, Any]:
        """Compiles a complete snapshot of all managers for dashboard updates."""
        return {
            "clock": self.clock,
            "queue_length": len(self.event_queue),
            "managers": {
                name: manager.snapshot() for name, manager in self.managers.items()
            }
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Gathers runtime metrics across all managers for analytics and export."""
        return {
            name: manager.metrics() for name, manager in self.managers.items()
        }


class RealController:
    """
    Adapter class fulfilling the ControllerAPI protocol for the Streamlit Dashboard,
    wrapping the underlying SimulationController discrete event engine.
    """

    supported_policies: Set[SchedulingPolicy] = {
        SchedulingPolicy.FCFS,
        SchedulingPolicy.SJF,
        SchedulingPolicy.SRTF,
        SchedulingPolicy.ROUND_ROBIN,
        SchedulingPolicy.PRIORITY,
    }

    def __init__(self, engine: Optional[SimulationController] = None):
        self.engine = engine if engine else SimulationController()

        self.engine.register_manager(ProcessManager())

        self.current_config: Optional[RunConfig] = None
        self.run_id: Optional[str] = None
        self.status: RunStatus = RunStatus.NOT_LOADED

    def load(self, config: RunConfig) -> Snapshot:
        """Loads a new configuration, validates it, and resets simulation state."""
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid RunConfig: {', '.join(errors)}")

        if config.process.policy not in self.supported_policies:
            raise ValueError(f"Unsupported scheduling policy: {config.process.policy}")

        self.current_config = config
        self.run_id = f"run-{uuid.uuid4().hex[:8]}"
        self.engine.reset()
        self.engine.set_seed(config.seed)

        # Configure managers with new run settings
        proc_mgr = self.engine.get_manager("Process")
        if proc_mgr:
            proc_mgr.configure({
                "policy": config.process.policy.value,
                "quantum_ms": config.process.quantum_ms,
                "context_switch_ms": config.process.context_switch_ms,
                "aging_interval": config.process.aging_interval,
            })
            # Test hardcoded values
            baseline_workload = [
                Process(pid="P1", arrival_time=0, burst_time=8, priority=3, owner_id=1),
                Process(pid="P2", arrival_time=1, burst_time=4, priority=1, owner_id=1),
                Process(pid="P3", arrival_time=2, burst_time=9, priority=4, owner_id=1),
                Process(pid="P4", arrival_time=3, burst_time=5, priority=2, owner_id=1),
            ]
            proc_mgr.load(baseline_workload)



            workload_file = getattr(config.process, "workload_file", "data/processes.csv")
            try:
                processes = load_and_validate_processes(workload_file)
                if hasattr(proc_mgr, "load_processes"):
                    proc_mgr.load_processes(processes)
            except Exception:
                pass
            
        self.status = RunStatus.READY
        return self.snapshot()

    def step(self) -> StepResult:
        """Advances simulation by 1 step/tick. Requires status READY."""
        if self.status not in (RunStatus.READY, RunStatus.PAUSED, RunStatus.RUNNING):
            raise ControllerStateError("Cannot step simulation unless status is READY or PAUSED.")

        step_events = self.engine.step()

        # Check if all work across managers is completed
        proc_mgr = self.engine.get_manager("Process")
        if proc_mgr and proc_mgr.is_finished():
            self.status = RunStatus.FINISHED

        return StepResult(snapshot=self.snapshot(), events=step_events)

    def run(self, until_tick: Optional[int] = None) -> StepResult:
        """Steps simulation until finished or target tick reached."""
        if self.status not in (RunStatus.READY, RunStatus.PAUSED, RunStatus.RUNNING):
            raise ControllerStateError("Cannot run simulation unless status is READY.")

        self.status = RunStatus.RUNNING
        accumulated_events: List[EventRecord] = []
        while self.status == RunStatus.RUNNING:
            if until_tick is not None and self.engine.clock >= until_tick:
                self.status = RunStatus.PAUSED
                break
            res = self.step()
            accumulated_events.extend(res.events)
            if self.status == RunStatus.FINISHED:
                break

        return StepResult(snapshot=self.snapshot(), events=accumulated_events)

    def pause(self) -> Snapshot:
        if self.status == RunStatus.RUNNING:
            self.status = RunStatus.PAUSED
        self.engine.pause()
        return self.snapshot()
    
    def reset(self) -> Snapshot:
        """Restarts current config at tick 0. Requires loaded run."""
        if self.current_config is None:
            raise ControllerStateError("No configuration loaded to reset.")
        return self.load(self.current_config)

    def snapshot(self) -> Snapshot:
        """Builds a UI-compatible Snapshot structure for the dashboard."""
        if not self.current_config or not self.run_id:
            return Snapshot(
                run_id="",
                tick=0,
                status=RunStatus.NOT_LOADED,
                config=RunConfig(),
                metrics={},
            )

        # Gather metrics from managers and wrap into Metric dataclasses
        raw_metrics = self.engine.get_system_metrics()
        formatted_metrics: Dict[str, Dict[str, Metric]] = {}

        for mgr_name, mgr_metrics in raw_metrics.items():
            formatted_metrics[mgr_name] = {}
            for metric_key, val in mgr_metrics.items():
                formatted_metrics[mgr_name][metric_key] = Metric(
                    value=float(val),
                    unit="ms" if "time" in metric_key else ("%" if "utilization" in metric_key else "count"),
                )

        return Snapshot(
            run_id=self.run_id,
            tick=self.engine.clock,
            status=self.status,
            config=self.current_config,
            metrics=formatted_metrics,
        )