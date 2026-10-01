from typing import Dict, List, Any, Optional
from src.core.base_manager import BaseManager
from src.core.models import FileNode
from src.core.events import EventRecord


class FileManager(BaseManager):

    def __init__(self):
        """
        Initializes all object fields to defaults
        Might change later depening on what bahavior we want
        """
        self.config: Dict[str, Any] = {}
        self.current_time: float = 0.0
        self.root: Optional[FileNode] = None
        self.pending_io_operations: List[Dict[str, Any]] = []
        self.reads_count: int = 0
        self.writes_count: int = 0
        self.bytes_read: int = 0
        self.bytes_written: int = 0

    def configure(self, config: Dict[str, Any]) -> None:
        """Initialize disk geometry and allocation policies"""
        self.config = config

        # Create root directory node
        self.root = FileNode(
            name="/",
            is_directory=True,
            size=0,
            children={},
            blocks=[]
        )

    def load(self, initial_state: Dict[str, Any]) -> None:
        """Pre populate the file system structure or pending I/O work"""
        self.current_time = 0.0
        self.reads_count = 0
        self.writes_count = 0
        self.bytes_read = 0
        self.bytes_written = 0

        # Load initial directory structure or initial file allocations
        initial_files = initial_state.get("files", [])
        for file_info in initial_files:
            self._create_file_node(file_info)

        # Queue initial scheduled file requests/workload
        self.pending_io_operations = initial_state.get("io_requests", [])

    def step(self, current_time: float) -> List[EventRecord]:
        """Advance file system state by one tick, processing scheduled I/O requests"""
        self.current_time = current_time
        events: List[EventRecord] = []

        if not self.pending_io_operations:
            return events

        # Process active I/O requests for this tick
        remaining_requests = []
        for req in self.pending_io_operations:
            if req.get("arrival_time", 0.0) <= self.current_time:
                # Execute file system operation (e.g., CREATE, READ, WRITE, DELETE)
                op_events = self._execute_io_operation(req)
                events.extend(op_events)
            else:
                remaining_requests.append(req)

        self.pending_io_operations = remaining_requests
        return events

    def run(self, stop_condition: Optional[Any] = None) -> List[EventRecord]:
        """Continuously run file system steps until requests are fulfilled or stopped"""
        all_events: List[EventRecord] = []

        while True:
            if stop_condition is not None and self._should_stop(stop_condition):
                break

            step_events = self.step(self.current_time)
            all_events.extend(step_events)

            self.current_time += 1.0

            if self._is_finished():
                break

        return all_events

    def snapshot(self) -> Dict[str, Any]:
        """Capture current file system tree and block usage for dashboard rendering."""
        return {
            "current_time": self.current_time,
            "file_tree": self._serialize_tree(self.root) if self.root else {},
        }

    def metrics(self) -> Dict[str, Any]:
        """Return I/O and storage utilization performance metrics"""
        allocated = sum(1 for free in self.free_block_bitmap if not free)
        return {
            "reads_count": self.reads_count,
            "writes_count": self.writes_count,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written
        }

    # Internal helper methods
    def _execute_io_operation():
        pass

    def _create_file_node():
        pass

    def _serialize_tree():
        pass

    def _should_stop():
        pass

    def _is_finished():
        pass