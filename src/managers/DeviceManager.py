from typing import Dict, List, Any, Optional
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import DeviceRequest, DeviceType, DeviceRequestStatus, DeviceState


class DeviceManager(BaseManager):
    """
    Manages hardware devices (Disk, Printer, Keyboard), request queueing,
    disk scheduling algorithms (FCFS, SSTF, SCAN), and device status transitions.
    """

    def __init__(self):
        super().__init__("Device")
        self.devices: Dict[str, Dict[str, Any]] = {
            "DISK_1": {"type": DeviceType.DISK, "status": DeviceState.AVAILABLE, "head_position": 0},
            "PRINTER_1": {"type": DeviceType.PRINTER, "status": DeviceState.AVAILABLE, "head_position": 0},
            "KEYBOARD_1": {"type": DeviceType.KEYBOARD, "status": DeviceState.AVAILABLE, "head_position": 0},
        }
        self.request_queue: List[DeviceRequest] = []
        self.completed_requests: List[DeviceRequest] = []
        self.active_requests: Dict[str, DeviceRequest] = {}
        self.disk_policy: str = "SSTF"  # FCFS, SSTF, SCAN
        self.head_movements: List[Dict[str, Any]] = []  # Visual history for disk plots
        self.total_seek_distance: int = 0

    def configure(self, config: Dict[str, Any]) -> None:
        self.disk_policy = config.get("disk_policy", "SSTF")
        self.is_configured = True

    def load(self, input_data: List[DeviceRequest]) -> None:
        self.request_queue.extend(input_data)

    def reset(self) -> None:
        self.request_queue.clear()
        self.completed_requests.clear()
        self.active_requests.clear()
        self.head_movements.clear()
        self.total_seek_distance = 0
        for dev in self.devices.values():
            dev["status"] = DeviceState.AVAILABLE
            dev["head_position"] = 0

    def step(self, current_time: float) -> List[EventRecord]:
        events: List[EventRecord] = []

        # Process active requests nearing completion
        finished_devices = []
        for dev_id, req in list(self.active_requests.items()):
            req.status = DeviceRequestStatus.COMPLETED
            self.completed_requests.append(req)
            self.devices[dev_id]["status"] = DeviceState.AVAILABLE
            finished_devices.append(dev_id)

            events.append(
                EventRecord(
                    timestamp=current_time,
                    manager=self.name,
                    event_type="DEVICE_COMPLETED",
                    entity_id=req.request_id,
                    action="COMPLETE_IO",
                    previous_state="IN_PROGRESS",
                    new_state="COMPLETED",
                    outcome="SUCCESS",
                    explanatory_message=f"Request {req.request_id} completed on {dev_id}."
                )
            )

        for dev_id in finished_devices:
            del self.active_requests[dev_id]

        # Schedule pending requests from queue
        if self.request_queue:
            next_req = self._schedule_next_request()
            if next_req and self.devices[next_req.device_id]["status"] == DeviceState.AVAILABLE:
                self.request_queue.remove(next_req)
                next_req.status = DeviceRequestStatus.IN_PROGRESS
                self.active_requests[next_req.device_id] = next_req
                self.devices[next_req.device_id]["status"] = DeviceState.BUSY

                # Track movement for disk plot UI
                if self.devices[next_req.device_id]["type"] == DeviceType.DISK:
                    target_cylinder = int(next_req.operation_type.split(":")[-1]) if ":" in next_req.operation_type else 50
                    prev_pos = self.devices[next_req.device_id]["head_position"]
                    seek = abs(target_cylinder - prev_pos)
                    self.total_seek_distance += seek
                    self.devices[next_req.device_id]["head_position"] = target_cylinder
                    
                    self.head_movements.append({
                        "timestamp": current_time,
                        "from": prev_pos,
                        "to": target_cylinder,
                        "seek": seek
                    })

                events.append(
                    EventRecord(
                        timestamp=current_time,
                        manager=self.name,
                        event_type="DEVICE_START",
                        entity_id=next_req.request_id,
                        action="START_IO",
                        previous_state="PENDING",
                        new_state="IN_PROGRESS",
                        outcome="SUCCESS",
                        explanatory_message=f"Request {next_req.request_id} assigned to {next_req.device_id}."
                    )
                )

        return events

    def _schedule_next_request(self) -> Optional[DeviceRequest]:
        if not self.request_queue:
            return None
        
        if self.disk_policy == "FCFS":
            return self.request_queue[0]
            
        elif self.disk_policy == "SSTF":
            disk_pos = self.devices["DISK_1"]["head_position"]
            return min(
                self.request_queue,
                key=lambda r: abs((int(r.operation_type.split(":")[-1]) if ":" in r.operation_type else 0) - disk_pos)
            )
        return self.request_queue[0]

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        all_events = []
        while self.request_queue or self.active_requests:
            all_events.extend(self.step(len(all_events)))
        return all_events

    def snapshot(self) -> Dict[str, Any]:
        """UI Snapshot format for device queues, device states, and disk head movements."""
        return {
            "devices": {dev_id: {"status": info["status"], "head_pos": info["head_position"]} 
                        for dev_id, info in self.devices.items()},
            "queue_length": len(self.request_queue),
            "pending_requests": [req.request_id for req in self.request_queue],
            "active_requests": {dev_id: req.request_id for dev_id, req in self.active_requests.items()},
            "disk_head_movements": self.head_movements,
        }

    def metrics(self) -> Dict[str, Any]:
        """UI metrics format for performance charts."""
        total_requests = len(self.completed_requests) + len(self.request_queue)
        return {
            "completed_requests": len(self.completed_requests),
            "pending_requests": len(self.request_queue),
            "total_seek_distance": self.total_seek_distance,
            "policy": self.disk_policy,
            "throughput": len(self.completed_requests) / max(1, len(self.completed_requests) + len(self.request_queue))
        }

    def validate(self) -> List[str]:
        errors = []
        if self.disk_policy not in ["FCFS", "SSTF", "SCAN"]:
            errors.append(f"Invalid disk policy: {self.disk_policy}")
        return errors

    def export(self, export_format: str = "json") -> Any:
        return {
            "metrics": self.metrics(),
            "completed": [req.__dict__ for req in self.completed_requests],
            "head_history": self.head_movements
        }