from typing import Dict, List, Any, Optional, Set
from dataclasses import asdict
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import DeviceRequest, DeviceType, DeviceRequestStatus, DeviceState

class DeviceManager(BaseManager):
    """
    Manages hardware devices (Disk, Printer, Keyboard), request queueing,
    disk scheduling algorithms (FCFS, SSTF, SCAN), device states, failure/recovery,
    and process block/unblock interactions.
    """

    def __init__(self):
        super().__init__("Device")
        self.devices: Dict[str, Dict[str, Any]] = {
            "DISK_1": {"type": DeviceType.DISK, "status": DeviceState.AVAILABLE, "head_position": 0, "max_cylinder": 200, "scan_direction": 1},
            "PRINTER_1": {"type": DeviceType.PRINTER, "status": DeviceState.AVAILABLE, "head_position": 0},
            "KEYBOARD_1": {"type": DeviceType.KEYBOARD, "status": DeviceState.AVAILABLE, "head_position": 0},
        }
        self.request_queue: List[DeviceRequest] = []
        self.completed_requests: List[DeviceRequest] = []
        self.active_requests: Dict[str, DeviceRequest] = {}
        self.request_remaining_time: Dict[str, int] = {}  # Tracks service time safely without altering DeviceRequest
        self.blocked_processes: Set[str] = set()
        self.disk_policy: str = "FCFS"
        self.head_movements: List[Dict[str, Any]] = []
        self.total_seek_distance: int = 0
        self.failure_count: int = 0
        self.total_wait_time: int = 0
        self.total_service_time: int = 0
        self.idle_ticks: int = 0

    def configure(self, config: Dict[str, Any]) -> None:
        self.disk_policy = config.get("disk_policy", "SSTF")
        self.is_configured = True

    def load(self, input_data: Any) -> None:
        if isinstance(input_data, dict):
            reqs = input_data.get("io_requests", [])
            for r in reqs:
                req_id = r.get("request_id", f"REQ-{len(self.request_queue) + len(self.completed_requests) + 1}")
                req = DeviceRequest(
                    request_id=req_id,
                    device_id=r.get("device_id", "DISK_1"),
                    process_id=r.get("pid", "P1"),
                    operation_type=r.get("operation_type", "READ:50"),
                    status=DeviceRequestStatus.PENDING,
                    arrival_time=float(r.get("arrival_time", 0.0))
                )
                self.request_queue.append(req)
                # Store service duration separately since DeviceRequest lacks burst_time
                self.request_remaining_time[req_id] = int(r.get("burst_time", 5))
        elif isinstance(input_data, list):
            self.request_queue.extend(input_data)

    def reset(self) -> None:
        self.request_queue.clear()
        self.completed_requests.clear()
        self.active_requests.clear()
        self.request_remaining_time.clear()
        self.blocked_processes.clear()
        self.head_movements.clear()
        self.total_seek_distance = 0
        self.failure_count = 0
        self.total_wait_time = 0
        self.total_service_time = 0
        self.idle_ticks = 0
        for dev_id, dev in self.devices.items():
            dev["status"] = DeviceState.AVAILABLE
            dev["head_position"] = 0
            if dev["type"] == DeviceType.DISK:
                dev["scan_direction"] = 1

    def fail_device(self, dev_id: str) -> None:
        if dev_id in self.devices:
            self.devices[dev_id]["status"] = DeviceState.ERROR
            self.failure_count += 1
            if dev_id in self.active_requests:
                req = self.active_requests.pop(dev_id)
                req.status = DeviceRequestStatus.FAILED
                self.completed_requests.append(req)

    def recover_device(self, dev_id: str) -> None:
        if dev_id in self.devices:
            self.devices[dev_id]["status"] = DeviceState.AVAILABLE

    def step(self, current_time: float) -> List[EventRecord]:
        events: List[EventRecord] = []

        # Track idle time if all devices are available and queue is empty
        if not self.request_queue and not self.active_requests:
            self.idle_ticks += 1

        # 1. Update queue waiting times for pending requests
        for req in self.request_queue:
            if req.arrival_time <= current_time:
                req.waiting_time += 1
                self.total_wait_time += 1

        # 2. Process active requests nearing completion
        finished_devices = []
        for dev_id, req in list(self.active_requests.items()):
            rem_time = self.request_remaining_time.get(req.request_id, 0) - 1
            self.request_remaining_time[req.request_id] = rem_time

            if rem_time <= 0 or self.devices[dev_id]["status"] in (DeviceState.OFFLINE, DeviceState.ERROR):
                if self.devices[dev_id]["status"] in (DeviceState.OFFLINE, DeviceState.ERROR):
                    req.status = DeviceRequestStatus.FAILED
                else:
                    req.status = DeviceRequestStatus.COMPLETED
                    req.completion_time = float(current_time)
                    self.total_service_time += 1

                self.completed_requests.append(req)
                if req.process_id in self.blocked_processes:
                    self.blocked_processes.remove(req.process_id)

                self.devices[dev_id]["status"] = DeviceState.AVAILABLE
                finished_devices.append(dev_id)

                events.append(
                    EventRecord(
                        timestamp=float(current_time),
                        manager=self.name,
                        event_type="DEVICE_COMPLETED",
                        entity_id=req.process_id,
                        action="COMPLETE_IO",
                        previous_state="IN_PROGRESS",
                        new_state="COMPLETED",
                        duration_or_cost=max(0, rem_time),
                        outcome="SUCCESS" if req.status == DeviceRequestStatus.COMPLETED else "FAILED",
                        explanatory_message=f"Request {req.request_id} for PID {req.process_id} completed on {dev_id}."
                    )
                )

        for dev_id in finished_devices:
            del self.active_requests[dev_id]

        # 3. Schedule pending requests from queue to available devices
        ready_requests = [r for r in self.request_queue if r.arrival_time <= current_time]
        if ready_requests:
            next_req = self._schedule_next_request(ready_requests)
            if next_req and self.devices[next_req.device_id]["status"] == DeviceState.AVAILABLE:
                self.request_queue.remove(next_req)
                next_req.status = DeviceRequestStatus.IN_PROGRESS
                next_req.start_time = float(current_time)
                self.active_requests[next_req.device_id] = next_req
                self.devices[next_req.device_id]["status"] = DeviceState.BUSY
                self.blocked_processes.add(next_req.process_id)

                # Disk seek tracking for SSTF / SCAN
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
                        "seek": seek,
                        "request_id": next_req.request_id
                    })

                rem_burst = self.request_remaining_time.get(next_req.request_id, 0)
                events.append(
                    EventRecord(
                        timestamp=float(current_time),
                        manager=self.name,
                        event_type="DEVICE_BLOCKED",
                        entity_id=next_req.process_id,
                        action="REQUEST_DEVICE",
                        previous_state="READY",
                        new_state="WAITING",
                        duration_or_cost=rem_burst,
                        outcome="SUCCESS",
                        explanatory_message=f"PID {next_req.process_id} blocked waiting on device {next_req.device_id} (burst: {rem_burst} ms)."
                    )
                )
                

        return events

    def _schedule_next_request(self, ready_requests: List[DeviceRequest]) -> Optional[DeviceRequest]:
        if not ready_requests:
            return None
        
        available_devs = {d_id for d_id, info in self.devices.items() if info["status"] == DeviceState.AVAILABLE}
        eligible = [r for r in ready_requests if r.device_id in available_devs]
        if not eligible:
            return None

        # FCFS should schedule the earliest eligible request across all devices
        if self.disk_policy == "FCFS":
            return eligible[0]

        disk_reqs = [r for r in eligible if self.devices[r.device_id]["type"] == DeviceType.DISK]
        other_reqs = [r for r in eligible if self.devices[r.device_id]["type"] != DeviceType.DISK]

        if other_reqs and not disk_reqs:
            return other_reqs[0]

        if not disk_reqs:
            return eligible[0]

        if self.disk_policy == "SSTF":
            disk_pos = self.devices["DISK_1"]["head_position"]
            return min(
                disk_reqs,
                key=lambda r: abs(int(r.operation_type.split(":")[-1]) if ":" in r.operation_type else 0 - disk_pos)
            )

        elif self.disk_policy == "SCAN":
            disk = self.devices["DISK_1"]
            pos = disk["head_position"]
            direction = disk.get("scan_direction", 1)
            ahead = [r for r in disk_reqs if (int(r.operation_type.split(":")[-1]) - pos) * direction >= 0]
            if ahead:
                return min(ahead, key=lambda r: abs(int(r.operation_type.split(":")[-1]) - pos))
            else:
                disk["scan_direction"] *= -1
                return min(disk_reqs, key=lambda r: abs(int(r.operation_type.split(":")[-1]) - pos))

        return eligible[0]

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        all_events = []
        while self.request_queue or self.active_requests:
            all_events.extend(self.step(len(all_events)))
        return all_events


    def snapshot(self) -> Dict[str, Any]:
        return {
            "devices": {
                dev_id: {
                    "status": info["status"].value if hasattr(info["status"], "value") else info["status"], 
                    "head_pos": info["head_position"]
                } 
                for dev_id, info in self.devices.items()
            },
            "queue_length": len(self.request_queue),
            "pending_requests": [req.request_id for req in self.request_queue],
            "active_requests": {dev_id: req.request_id for dev_id, req in self.active_requests.items()},
            "disk_head_movements": self.head_movements,
            "completed_requests": [
                {
                    **asdict(r),
                    "status": r.status.value if hasattr(r.status, "value") else r.status
                } 
                for r in self.completed_requests
            ],
        }

    def metrics(self) -> Dict[str, Any]:
        total_reqs = len(self.completed_requests) + len(self.request_queue)
        completed = len(self.completed_requests)
        return {
            "completed_requests": completed,
            "pending_requests": len(self.request_queue),
            "total_seek_distance": self.total_seek_distance,
            "device_failures": self.failure_count,
            "device_throughput": float(completed / max(1, total_reqs)),
            "device_utilization": float(100 * len(self.active_requests) / max(1, len(self.devices))),
            "avg_device_wait": float(self.total_wait_time / max(1, completed)),
            "avg_queue_length": float(len(self.request_queue)),
            "idle_time": self.idle_ticks,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.disk_policy not in ["FCFS", "SSTF", "SCAN"]:
            errors.append(f"Invalid disk policy: {self.disk_policy}")
        return errors

    def export(self, export_format: str = "json") -> Any:
        return {
            "metrics": self.metrics(),
            "completed": [asdict(req) for req in self.completed_requests],
            "head_history": self.head_movements
        }