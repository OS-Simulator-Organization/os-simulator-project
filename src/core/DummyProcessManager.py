from typing import Dict, Any, List
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import Process, ProcessState

class DummyProcessManager(BaseManager):
    def __init__(self):
        super().__init__("Process")
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

