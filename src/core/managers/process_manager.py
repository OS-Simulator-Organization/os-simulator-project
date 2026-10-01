
from typing import Any, Dict, List, Optional
from src.core.base_manager import BaseManager
from src.core.events import EventRecord 
from src.core.models import Process, ProcessState

class ProcessManager(BaseManager):
    def __init__(self):
        # Initializes all object fields to defaults
        # Might change later depening on what bahavior we want
        self.algorithm: str = "FCFS"             
        self.quantum: int = 4
        self.context_switch_cost: int = 0
        self.ready_queue: List[Process] = []
        self.running_process: Optional[Process] = None
        self.workload: List[Process] = []
        self.current_time: float = 0.0
# Manager helper functions

def update_ready_queue():
    pass
def select_work():
    pass
def execute_work():
    pass
def handle_state_transitions():
    pass
    

# Exposed manager methods
    def configure(self, config: Dict[str, Any]) -> None:
        # Each expects a key (first argument) and return default value if none found (second argument)
        self.algorithm = config.get("algorithm", "FCFS")
        self.quantum = config.get("quantum", 4)
        self.context_switch_cost = config.get("context_switch_cost", 0)

    def load(self, input_data: List[Process]) -> None:
        # Gets total workload from input
        self.workload = input_data

    def reset(self) -> None:
        # Clear out runtime changes, set CPU to beginning
        self.ready_queue.clear()
        self.running_process = None
        self.workload.clear()
        self.current_time = 0.0

    def step(self, current_time: float) -> List[EventRecord]:
        self.current_time = current_time
        events: List[EventRecord] = []

        # Check for arrivals
        update_ready_queue()

        # CPU Dispatcher Logic
        select_work()

        # Process Execution
        execute_work()

        # Process any state transitions caused from executing work
        handle_state_transitions()

        # Return event log of tick
        return events

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        all_events = []

        # Run CPU until all processes are terminated or stop condition has been reached
        while any(p.state != ProcessState.TERMINATED for p in self.all_processes):
            if(stop_condition):
                break
            step_events = self.step(self.current_time)
            all_events.extend(step_events)

        # Return all events 
        return all_events

    def snapshot(self) -> Dict[str, Any]:
        # Return current state of CPU
        return {
            "running_pid": self.running_process.pid if self.running_process else None,
            "ready_queue": [p.pid for p in self.ready_queue],
            "algorithm": self.algorithm,
        }

    def metrics(self) -> Dict[str, Any]:
        # Return base metrics of completed processes, will add more down the line
        completed = [p for p in self.workload if p.state == ProcessState.TERMINATED]
        return {
            "total_processes": len(self.workload),
            "completed_processes": len(completed),
            "useful_cpu_utilization": 100.0 if self.running_process else 0.0,
        }

    def validate(self) -> List[str]:
        # Validate input given from parser
        errors = []
        valid_algos = ["FCFS", "SJF", "SRTF", "RR", "PRIORITY"]
        if self.algorithm not in valid_algos:
            errors.append(f"Invalid scheduling algorithm: {self.algorithm}")
        return errors

    def export(self, export_format: str = "json") -> Any:
        # Return snapshot of current CPU
        return self.snapshot()


    