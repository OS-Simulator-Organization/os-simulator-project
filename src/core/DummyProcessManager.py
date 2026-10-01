import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict, Any, List
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.controller import SimulationController
from src.core.models import Process, ProcessState

class DummyProcessManager(BaseManager):
    def __init__(self):
        super().__init__("process_manager")
        self.queue: List[Process] = []

    def configure(self, config: Dict[str, Any]) -> None:
        self.is_configured = True

    def load(self, input_data: Any) -> None:
        self.queue = input_data

    def reset(self) -> None:
        self.queue.clear()

    def step(self, current_time: float) -> List[EventRecord]:
        events = []
        for p in self.queue:
            if p.arrival_time == current_time:
                p.state = ProcessState.READY
                events.append(
                    EventRecord(
                        timestamp=current_time,
                        manager=self.name,
                        event_type="PROCESS_ARRIVE",
                        entity_id=p.pid,
                        action="ARRIVED",
                        previous_state=ProcessState.NEW.value,
                        new_state=ProcessState.READY.value,
                        outcome="SUCCESS",
                        explanatory_message=f"Process {p.pid} owned by {p.owner_id} arrived."
                    )
                )
        return events

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        return []

    def snapshot(self) -> Dict[str, Any]:
        return {"queue_length": len(self.queue)}

    def metrics(self) -> Dict[str, Any]:
        return {"total_processes": len(self.queue)}

    def validate(self) -> List[str]:
        return []

    def export(self, export_format: str = "json") -> Any:
        return {}


def run_pipeline_test():
    controller = SimulationController(seed=42)
    proc_manager = DummyProcessManager()
    controller.register_manager(proc_manager)

    # Load test processes matching data_model.md specifications
    test_processes = [
        Process(pid="P1", owner_id="user_admin", arrival_time=0, burst_time=5, priority=1, remaining_time=5),
        Process(pid="P2", owner_id="user_guest", arrival_time=1, burst_time=3, priority=2, remaining_time=3)
    ]
    proc_manager.load(test_processes)

    events_tick_0 = controller.step()
    events_tick_1 = controller.step()

    assert len(events_tick_0) == 1, "Tick 0 should trigger arrival for P1"
    assert events_tick_0[0].entity_id == "P1"
    assert len(events_tick_1) == 1, "Tick 1 should trigger arrival for P2"
    assert events_tick_1[0].entity_id == "P2"

    print("Shared Data Model Pipeline Integration Test PASSED!")
    print("Snapshot:", controller.get_system_snapshot())

if __name__ == "__main__":
    run_pipeline_test()