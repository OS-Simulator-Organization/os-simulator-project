from typing import Dict, List, Any, Optional
from src.core.base_manager import BaseManager
from src.core.models import PageFrame, Process
from src.core.events import EventRecord



class MemoryManager(BaseManager):
    def __init__(self):
        """
        Initializes all object fields to defaults
        Might change later depening on what bahavior we want
        """
        self.config: Dict[str, Any] = {}
        self.current_time: float = 0.0
        
        # Memory state tracking
        self.total_frames: int = 0
        self.page_size: int = 0
        self.algorithm: str = "FIFO"
        self.frames: List[PageFrame] = []
        self.page_fault_count: int = 0

    # Exposed manager API methods
    def configure(self, config: Dict[str, Any]) -> None:
        """Initialize memory settings from configuration dictionary."""
        self.config = config
        
        # Setting default values
        self.algorithm = config.get("algorithm", "FIFO")
        self.page_size = config.get("page_size", 4096)
        num_frames = config.get("total_frames", 16)
        
        # Initialize empty frames
        self.frames = [
            PageFrame(frame_id=i, page_number=None, process_id=None)
            for i in range(num_frames)
        ]
        self.total_frames = len(self.frames)

    def load(self, initial_state: Dict[str, Any]) -> None:
        """Pre-populate memory frames or page state before simulation begins."""
        self.current_time = 0.0
        self.page_fault_count = 0
        
        # Load any initial frame allocations provided in state
        initial_frames = initial_state.get("frames", [])
        for i, frame_data in enumerate(initial_frames):
            if i < len(self.frames):
                self.frames[i].process_id = frame_data.get("process_id")
                self.frames[i].page_number = frame_data.get("page_number")

    def step(self, current_time: float) -> List[EventRecord]:
        """Advance memory simulation by one tick."""
        self.current_time = current_time
        events: List[EventRecord] = []

        # Process pending page requests/lookups for this tick
        self._process_page_requests()

        return events

    def run(self, stop_condition: Optional[Any] = None) -> List[EventRecord]:
        """Continuously execute steps until stop condition is met or work finishes."""
        all_events: List[EventRecord] = []

        while True:
            # Check stop condition if provided
            if stop_condition is not None and self._should_stop():
                break

            # Perform single tick execution
            step_events = self.step(self.current_time)
            all_events.extend(step_events)

            # Advance clock
            self.current_time += 1.0

            # Stop when no active page requests remain
            if self._is_finished():
                break

        return all_events

    def snapshot(self) -> Dict[str, Any]:
        """Capture current physical memory state for visualization/debugging."""
        return {
            "current_time": self.current_time,
            "algorithm": self.algorithm,
            "total_frames": self.total_frames,
            "page_fault_count": self.page_fault_count,
            "frames": [
                {
                    "frame_id": frame.frame_id,
                    "process_id": frame.process_id,
                    "page_number": frame.page_number,
                }
                for frame in self.frames
            ],
        }

    def metrics(self) -> Dict[str, Any]:
        """Return memory subsystem performance metrics."""
        return {
            "page_fault_count": self.page_fault_count,
            "total_frames": self.total_frames,
            "allocated_frames": sum(1 for f in self.frames if f.process_id is not None),
            "free_frames": sum(1 for f in self.frames if f.process_id is None),
        }

    def validate(self) -> List[str]:
            """
            Validate input given from parser
            """
            errors = []
            valid_algos = ["FIFO", "LRU"]
            if self.algorithm not in valid_algos:
                errors.append(f"Invalid replacement algorithm: {self.algorithm}")
            return errors
    
    def export(self, export_format: str = "json") -> Any:
        """
        Return snapshot of current Memory
        """
        return self.snapshot()
    
    # Manager helper functions
    def _should_stop():
        pass

    def _is_finished():
        pass

    def _process_page_requests():
        pass