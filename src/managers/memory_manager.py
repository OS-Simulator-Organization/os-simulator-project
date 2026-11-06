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
        super().__init__("Memory")
        self.is_configured: bool = False
        self.algorithm: str = ""
        self.page_size: int = 0
        self.total_frames: int = 0
        self.fault_latency: float = 0.0 # Penalty for page fault

        self.current_time: float = 0.0
        self.frames: List[PageFrame] = [] # List of all frames
        self.fault_latencies: Dict[str, int] = {} # Each process that is in a fault latency and the duration left
        self.fifo_queue: List[str] = []
        self.page_tables: Dict[str, Dict[int, int]] = {} # Stores every page table for all the processes 
        self.traces: Dict[str, List[int]] = {} # Stores trace list for each process
        self.trace_pointers: Dict[str, int] = {} # Keeps track of the trace address that each process is on

        # Metrics
        self.total_requests: int = 0
        self.page_fault_count: int = 0
        self.hit_count: int = 0
        self.eviction_count: int = 0



    # Exposed manager API methods
    def configure(self, config: Dict[str, Any]) -> None:
        """Initialize memory settings from configuration dictionary"""
        if not config:
            raise ValueError("Configuration dictionary is empty")
        
        # Extract configuration fields with default fallback values
        self.algorithm = config.get("algorithm", "FIFO")
        self.page_size = config.get("page_size", 0)
        self.fault_latency = config.get("fault_latency", 0)
        self.total_frames = config.get("total_frames", 0)
        
        # Initialize empty physical frames
        self.frames = [
        PageFrame(
            frame_id=i, 
            page_number=None, 
            pid=None,
            is_modified=False,
            last_accessed=0,
            load_tick=0
        )for i in range(self.total_frames)]

        # Mark manager as configured for the controller
        self.is_configured = True

    def load(self, initial_state: Dict[str, Any]) -> None:
        """Pre-populates memory frames, initializes per-process page tables, and loads address traces before simulation begins"""
        self.current_time = 0.0
        self.page_fault_count = 0
        
        # Reset all physical frames to empty state
        for frame in self.frames:
            frame.pid = None
            frame.page_number = None
            frame.is_modified = False
            frame.last_accessed = 0
            frame.load_tick = 0    
        
        # Load pre-populated initial frame allocations and sync page tables
        initial_frames = initial_state.get("frames", [])
        for i, frame_data in enumerate(initial_frames):
            if i < len(self.frames):
                pid = frame_data.get("pid")
                page_number = frame_data.get("page_number")
                
                if pid is not None and page_number is not None:
                    self.frames[i].pid = pid
                    self.frames[i].page_number = page_number
                    self.frames[i].is_modified = frame_data.get("is_modified", False)
                    self.frames[i].last_accessed = frame_data.get("last_accessed", 0)
                    self.frames[i].load_tick = frame_data.get("load_tick", 0)

                    # Ensure process page table entry exists and maps this page to frame i
                    if pid not in self.page_tables:
                        self.page_tables[pid] = {}
                    self.page_tables[pid][page_number] = i
        
        # Load address traces per process
        # Supports structured dict format or list format with embedded PIDs
        raw_traces = initial_state.get("traces", initial_state.get("trace", {}))
        if raw_traces and isinstance(raw_traces, dict):
            for pid, addresses in raw_traces.items():
                parsed_addresses = []
                for addr in addresses:
                    if isinstance(addr, str):
                        parsed_addresses.append(int(addr, 16) if addr.startswith("0x") else int(addr))
                    else:
                        parsed_addresses.append(int(addr))
                self.traces[pid] = parsed_addresses
                self.trace_pointers[pid] = 0
                if pid not in self.page_tables:
                    self.page_tables[pid] = {}
                
        elif raw_traces and isinstance(raw_traces, list):
            for item in raw_traces:
                if isinstance(item, dict):
                    pid = item.get("pid")
                    raw_addr = item.get("address", 0)
                    addr = int(raw_addr, 16) if isinstance(raw_addr, str) and raw_addr.startswith("0x") else int(raw_addr)
                    if pid not in self.traces:
                        self.traces[pid] = []
                        self.trace_pointers[pid] = 0
                    if pid not in self.page_tables:
                        self.page_tables[pid] = {}
                    self.traces[pid].append(addr)

    def reset(self) -> None:
        """
        Return the manager to initial state without discarding the workload
        Resets the clock, fault metrics, physical frames, page tables, and trace pointers
        """
        self.current_time = 0.0
        self.page_fault_count = 0
        self.fifo_queue.clear()
        self.fault_latencies.clear()
        
        # Clear all physical frames back to an unallocated state
        for frame in self.frames:
            frame.pid = None
            frame.page_number = None
            frame.is_modified = False
            frame.last_accessed = 0
            frame.load_tick = 0

        # Clear per-process page table mappings if initialized
        for pid in self.page_tables:
            self.page_tables[pid].clear()

        # Set all per-process address trace pointers to index 0
        for pid in self.trace_pointers:
            self.trace_pointers[pid] = 0

    def step(self, current_time: float, running_process: Optional[Process] = None, terminated_processes: Optional[List[Process]] = None) -> List[EventRecord]:
        """
        Advance memory simulation by one tick
        Updates the internal clock and processes memory requests or active fault latencies for this tick
        """
        self.current_time = current_time
        events: List[EventRecord] = []

        # Unallocated memory of recently terminated processes
        if terminated_processes:
            events.extend(self._unallocate_frames(terminated_processes))
        
        # Decrment fault latency countdowns
        events.extend(self._update_fault_latency())

        # Process virtual address lookups, hits, faults, and replacements
        events.extend(self._process_page_requests(running_process))

        return events

    def run(self, stop_condition: Optional[Any] = None) -> List[EventRecord]:
        """
        Continuously execute simulation steps until all process address traces 
        are fully consumed, fault penalties are resolved, or a stop condition is met
        """
        all_events: List[EventRecord] = []
        steps_executed = 0

        if not self.is_configured:
            return all_events
        
        while not self.is_finished():
            # Check stop condition if provided
            if stop_condition is not None:
                if callable(stop_condition) and stop_condition(self):
                    break

            # Execute single tick and accumulate events
            step_events = self.step(self.current_time)
            all_events.extend(step_events)

            # Advance simulation clock and step tracker
            self.current_time += 1
            steps_executed += 1

        return all_events
    
    def snapshot(self) -> Dict[str, Any]:
        """
        Capture a snapshot of the current physical memory state, 
        per-process page tables, trace progress, and fault metrics
        """
        return {
            "current_time": self.current_time,
            "algorithm": self.algorithm,
            "page_size": self.page_size,
            "total_frames": self.total_frames,
            "total_requests": self.total_requests,
            "hit_count": self.hit_count,
            "page_fault_count": self.page_fault_count,
            "eviction_count": self.eviction_count,
            # Capture global physical frame table state
            "frames": [
                {
                    "frame_id": frame.frame_id,
                    "process_id": frame.pid,
                    "page_number": frame.page_number,
                    "is_modified": getattr(frame, "is_modified", False),
                    "last_accessed": getattr(frame, "last_accessed", 0),
                    "load_tick": getattr(frame, "load_tick", 0),
                }
                for frame in self.frames
            ],
            # Capture individual process page table mappings
            "page_tables": {
                pid: {str(v_page): f_id for v_page, f_id in page_table.items()}
                for pid, page_table in getattr(self, "page_tables", {}).items()
            },
            # Capture current progress of per-process address traces
            "trace_pointers": dict(getattr(self, "trace_pointers", {})),
            # Capture active fault latencies if any processes are currently blocked
            "fault_latencies": dict(getattr(self, "fault_latencies", {})),
        }

    def metrics(self) -> Dict[str, Any]:
        """
        Return comprehensive memory subsystem performance metrics, 
        including hit/fault counts, operational rates, and physical frame utilization
        """
        
        # Calculate hit/fault rates based on request counts
        hit_rate = 0.0
        fault_rate = 0.0
        if self.total_requests > 0:
            fault_rate = ((self.page_fault_count * 1.0) / self.total_requests) * 100
            hit_rate = ((self.hit_count * 1.0) / self.total_requests)  * 100

        # Gather other metrics
        allocated_frames = sum(1 for f in self.frames if f.pid is not None)
        free_frames = self.total_frames - allocated_frames
        utilization = (allocated_frames / self.total_frames) if self.total_frames > 0 else 0.0

        hit_cost = 1
        fault_cost = hit_cost + self.fault_latency
        total_cost = (self.hit_count * hit_cost) + (self.page_fault_count * fault_cost)
        avg_access_time = (total_cost / self.total_requests) if self.total_requests > 0 else 0.0
        return {
            "total_memory_references": self.total_requests,
            "page_hits": self.hit_count,
            "page_faults": self.page_fault_count,
            "eviction_count": self.eviction_count,
            "page_fault_rate": round(fault_rate, 4),
            "page_hit_rate": round(hit_rate, 4),
            "total_cost": total_cost,
            "avg_access_time": round(avg_access_time, 4),
            "total_frames": self.total_frames,
            "allocated_frames": allocated_frames,
            "free_frames": free_frames,
            "frame_utilization": round(utilization, 4)
        }

    def validate(self) -> List[str]:
        """
        Validate memory manager configuration parameters
        Returns a list of error messages if validation fails or an empty list if valid
        """
        errors: List[str] = []

        # Validate replacement algorithm selection
        algorithm = self.algorithm
        supported_algorithms = {"FIFO", "LRU"}
        if not algorithm:
            errors.append(f"No algorithm given: Must be one of {supported_algorithms}")
        else:
            if algorithm not in supported_algorithms:
                errors.append(f"Unsupported replacement algorithm: '{algorithm}': Must be one of {supported_algorithms}")

        # Validate page size: must be a positive integer and standard power of 2
        page_size = self.page_size
        if not page_size:
            errors.append(f"No page size given")
        else:
            if not isinstance(page_size, int) or page_size <= 0:
                errors.append(f"Invalid page_size: '{page_size}': Must be a positive integer")
            elif (page_size & (page_size - 1)) != 0:
                errors.append(f"Invalid page_size: '{page_size}': Must be a power of 2")

        # Validate total frames count
        total_frames = self.total_frames
        if not total_frames:
            errors.append(f"No frame count given")
        else:
            if not isinstance(total_frames, int) or total_frames <= 0:
                errors.append(f"Invalid total_frames: '{total_frames}': Must be a positive integer greater than 0")

        return errors
    
    def export(self, export_format: str = "json") -> Any:
        """
        Produce results, event metrics, and state data
        """
        format_lower = export_format.lower()
        
        # Compile export json
        export_data = {
            "manager": self.name,
            "configuration": {
                "algorithm": self.algorithm,
                "page_size": self.page_size,
                "total_frames": self.total_frames,
                "fault_latency": self.fault_latency,
            },
            "metrics": self.metrics(),
            "snapshot": self.snapshot(),
            "frames": [
                {
                    "frame_id": f.frame_id,
                    "pid": f.pid,
                    "page_number": f.page_number,
                    "is_modified": f.is_modified,
                    "last_accessed": f.last_accessed,
                    "load_tick": f.load_tick,
                }
                for f in self.frames
            ]
        }

        if format_lower == "json":
            return export_data
        elif format_lower == "csv":
            # CSV formatting for physical frames
            csv_lines = ["frame_id,pid,page_number,is_modified,last_accessed,load_tick"]
            for f in self.frames:
                csv_lines.append(
                    f"{f.frame_id},{f.pid},{f.page_number},{f.is_modified},{f.last_accessed},{f.load_tick}"
                )
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {export_format}. Use 'json' or 'csv'.")

    
    def is_finished(self) -> bool:
        """
        Returns True when all process address traces have been fully consumed 
        and there are no pending page fault latencies
        """
        # Check if traces exist and all pointers have reached the end of their lists
        if self.traces:
            for pid, trace in self.traces.items():
                pointer = self.trace_pointers.get(pid, 0)
                if pointer < len(trace):
                    return False
        
        # Continue if any processes are still blocked on fault latencies
        if self.fault_latencies:
            if any(remaining > 0 for remaining in self.fault_latencies.values()):
                return False

        return True

    # Manager helper functions
    def _unallocate_frames(self, terminated_processes: List[Process] ) -> List[EventRecord]:
        events: List[EventRecord] = []

        if not terminated_processes:
            return events

        terminated_pids = {p.pid for p in terminated_processes}

        for f in self.frames:
            if f.pid in terminated_pids:
                t_pid = f.pid
                f.pid = None
                f.page_number = None
                f.is_modified = False
                f.last_accessed = 0
                f.load_tick = 0
                
                events.append(EventRecord(
                    timestamp=self.current_time,
                    manager="Memory",
                    event_type="FRAME_UNALLOCATED",
                    entity_id=f.frame_id,
                    action="FREE",
                    previous_state="ALLOCATED",
                    new_state="FREE",
                    outcome="SUCCESS"
                ))

                if f.frame_id in self.fifo_queue:
                    self.fifo_queue.remove(f.frame_id)
        return events

    def _update_fault_latency(self) -> List[EventRecord]:
        """
        Decrement active page fault countdowns for blocked processes, 
        handle fault resolution when penalties expire, and generate shared event records.
        """
        events: List[EventRecord] = []
        resolved_pids: List[str] = []

        if not self.traces:
            return events

        # Decrement fault latency countdown for each process currently blocked on a page fault
        for pid, remaining_ticks in self.fault_latencies.items():
            if remaining_ticks > 0:
                self.fault_latencies[pid] = remaining_ticks - 1
                
                # Check if the fault latency penalty has completed
                if self.fault_latencies[pid] <= 0:
                    resolved_pids.append(pid)
                else:
                    # If fault latency is 0, resolve it on the next tick
                    self.fault_latencies[pid] = 1

        # Clean up resolved latencies and emit fault resolution events
        for pid in resolved_pids:
            del self.fault_latencies[pid]

            events.append(EventRecord(
                timestamp=self.current_time,
                manager="Memory",
                event_type="PAGE_FAULT_RESOLVED",
                entity_id=pid,
                action="UNBLOCK",
                previous_state="WAITING",
                new_state="READY",
                outcome="SUCCESS"
            ))

        return events
    
    def _process_page_requests(self, running_process: Optional[Process]) -> List[EventRecord]:
        """
        Process virtual address lookups for active processes, handling hits,
        page faults, FIFO/LRU replacements, and fault latency blocking.
        """
        events: List[EventRecord] = []

        if not self.traces:
            return events
        
        if not running_process:
            return events
    
        pid = running_process.pid
        trace = self.traces.get(pid, [])
        # Skip blocked processes
        if pid in self.fault_latencies and self.fault_latencies[pid] > 0:
            return events

        # Skip processed all traces
        pointer = self.trace_pointers.get(pid, 0)
        if pointer >= len(trace):
            return events

        address = trace[pointer]
        page_number = address // self.page_size
        self.total_requests += 1

        # Ensure process page table exists
        page_table = self.page_tables.setdefault(pid, {})

        # Page hit
        if page_number in page_table:
            self.hit_count += 1
            frame_id = page_table[page_number]
            
            # Update frame access timestamp for LRU
            for f in self.frames:
                if f.frame_id == frame_id:
                    f.last_accessed = self.current_time
                    break

            # Advance trace pointer on hit
            self.trace_pointers[pid] = pointer + 1

            events.append(EventRecord(
                timestamp=self.current_time,
                manager="Memory",
                event_type="PAGE_HIT",
                entity_id=pid,
                action="ACCESS",
                previous_state="READY",
                new_state="READY",
                outcome="SUCCESS"
            ))
        
        # Page fault
        else:
            self.page_fault_count += 1
            target_frame = None

            # Search for an unallocated physical frame first
            free_frame = next((f for f in self.frames if f.pid is None), None)
            if free_frame is not None:
                target_frame = free_frame
            
            # Evict a victim frame if memory is full
            else:
                # LRU Policy
                if self.algorithm == "LRU":
                    target_frame = min(self.frames, key=lambda f: (f.last_accessed, f.load_tick, f.frame_id))
                    self.eviction_count += 1

                # FIFO Policy
                else:
                    frame_ids = {f.frame_id for f in self.frames if f.pid is not None}
                    self.fifo_queue = [fid for fid in self.fifo_queue if fid in frame_ids]
                    
                    if self.fifo_queue:
                        victim_fid = self.fifo_queue.pop(0)
                        target_frame = next(f for f in self.frames if f.frame_id == victim_fid)
                    else:
                        # Fallback if queue desyncs
                        target_frame = min(self.frames, key=lambda f: (f.load_tick, f.frame_id))
                    self.eviction_count += 1

                # Remove old page mapping from the victim process's page table
                if target_frame.pid is not None and target_frame.page_number is not None:
                    old_pid = target_frame.pid
                    old_page = target_frame.page_number
                    if old_pid in self.page_tables and old_page in self.page_tables[old_pid]:
                        del self.page_tables[old_pid][old_page]

            # Load new virtual page into the target physical frame
            target_frame.pid = pid
            target_frame.page_number = page_number
            target_frame.is_modified = False
            target_frame.last_accessed = self.current_time
            target_frame.load_tick = self.current_time

            # Map page in the process page table
            self.page_tables[pid][page_number] = target_frame.frame_id

            # Track frame load order for FIFO
            if self.algorithm == "FIFO":
                if target_frame.frame_id not in self.fifo_queue:
                    self.fifo_queue.append(target_frame.frame_id)

            # Advance trace pointer and trigger fault latency blocking state
            self.trace_pointers[pid] = pointer + 1
            if self.fault_latency > 0:
                self.fault_latencies[pid] = self.fault_latency
                events.append(EventRecord(
                    timestamp=self.current_time,
                    manager="Memory",
                    event_type="PAGE_FAULT",
                    entity_id=pid,
                    action="BLOCK",
                    previous_state="READY",
                    new_state="WAITING",
                    outcome="SUCCESS"
                ))
            else:
                events.append(EventRecord(
                    timestamp=self.current_time,
                    manager="Memory",
                    event_type="PAGE_FAULT_RESOLVED",
                    entity_id=pid,
                    action="UNBLOCK",
                    previous_state="WAITING",
                    new_state="READY",
                    outcome="SUCCESS"
                ))

        return events



    
