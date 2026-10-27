
from typing import Any, Dict, List, Optional
from src.core.base_manager import BaseManager
from src.core.events import EventRecord 
from src.core.models import Process, ProcessState

class ProcessManager(BaseManager):
    def __init__(self):
        """
        Initializes all object fields to defaults
        """
        super().__init__("Process")
        
        self.algorithm: str = "FCFS"

        self.quantum: int = 0
        self.slice: int = 0

        self.context_switch_cost: int = 0
        self.cs_ticks_remaining: int = 0
        self.context_switch_time: int = 0

        self.aging_interval: int = 0
        
        self.running_process: Optional[Process] = None
        self.ready_queue: List[Process] = []
        self.workload: List[Process] = []
        self.completed_processes: int = 0

        self.idle_time: int = 0
        self.current_time: int = 0

        self.gantt_ticks: List[Dict[str, Any]] = []
        



    # Exposed manager API methods

    def configure(self, config: Dict[str, Any]) -> None:
        """Apply manager-specific configuration (based on RealController.load())"""
        if not config:
            raise ValueError("Configuration dictionary is empty")
            
        # Extract fields matching what RealController.load() provides and mark manager as configured
        # I'm not 100% about the structure of config so this may end up changing in the future
        self.algorithm = config.get("policy", "FCFS")
        self.quantum = config.get("quantum_ms", None)
        self.context_switch_cost = config.get("context_switch_ms", 0)
        self.aging_interval = config.get("aging_interval", 0)
        self.is_configured = True

    def load(self, input_data: List[Process]) -> None:
        """
        Gets total workload from, sets remaining time, process state, and sorts workload by arrival time
        """

        for p in input_data:
            p.state = ProcessState.NEW
            p.remaining_time = p.burst_time
            self.workload.append(p)
            
        # Sort workload chronologically by arrival time
        self.workload.sort(key=lambda p: p.arrival_time)

    def reset(self) -> None:
        """
        Clear out runtime changes, reset processes to initial NEW state, reset clock
        """
        self.ready_queue.clear()
        self.running_process = None
        self.current_time = 0.0
        self.gantt_ticks.clear()
    
        # Reset all loaded processes back to their initial state
        for p in self.workload:
            p.state = ProcessState.NEW
            p.remaining_time = p.burst_time

    def step(self, current_time: int) -> List[EventRecord]:
        """
        Run CPU for exactly 1 tick
        """
        self.current_time = current_time
        events: List[EventRecord] = []
        
        # 1. Check for arrivals (and append generated events)
        events.extend(self._update_ready_queue())
        
        # 2. CPU Dispatcher Logic (handles context switches, selection, preemption)
        if self.cs_ticks_remaining == 0:
            events.extend(self._select_work())

        # 3. Process Execution (decrements remaining time for running process)
        events.extend(self._execute_work())

        # Return event log of this tick
        return events

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        """
        Run CPU until all processes are terminated or stop condition has been reached
        """
        all_events: List[EventRecord] = []
        
        if not self.is_configured:
            return all_events

        while not self.is_finished():
            # Check stop condition if provided
            if stop_condition is not None:
                if callable(stop_condition) and stop_condition(self):
                    break

            # Advance simulation by 1 tick
            step_events = self.step(self.current_time + 1)
            all_events.extend(step_events)

        return all_events

    def snapshot(self) -> Dict[str, Any]:
        """
        Return current state of the Process Manager for dashboard rendering and tests
        """
        return {
            "algorithm": self.algorithm,
            "quantum": self.quantum,
            "context_switch_cost": self.context_switch_cost,
            "cs_ticks_remaining": self.cs_ticks_remaining,
            "current_time": self.current_time,
            "running_pid": self.running_process.pid if self.running_process else None,
            "running_process": {
                "pid": self.running_process.pid,
                "remaining_time": self.running_process.remaining_time,
                "burst_time": self.running_process.burst_time,
                "state": self.running_process.state.value,
                "priority": self.running_process.priority,
            } if self.running_process else None,
            "ready_queue": [
                {
                    "pid": p.pid,
                    "arrival_time": p.arrival_time,
                    "remaining_time": p.remaining_time,
                    "priority": p.priority,
                    "state": p.state.value,
                }
                for p in self.ready_queue
            ],
            "workload": [
                {
                    "pid": p.pid,
                    "arrival_time": p.arrival_time,
                    "burst_time": p.burst_time,
                    "remaining_time": p.remaining_time,
                    "priority": p.priority,
                    "state": p.state.value,
                    "completion_time": getattr(p, "completion_time", None),
                    "turnaround_time": getattr(p, "turnaround_time", -1),
                    "wait_time": getattr(p, "wait_time", -1),
                    "response_time": getattr(p, "response_time", -1),
                }
                for p in self.workload
            ],
            "completed_processes": self.completed_processes,
        }

    def metrics(self) -> Dict[str, Any]:
        """
        Return measurements and performance statistics for completed and active processes
        """
        total_processes = len(self.workload)
        completed = [p for p in self.workload if p.state == ProcessState.TERMINATED]
        

        # Calculate averages
        if self.completed_processes > 0:
            avg_waiting_time = sum(p.wait_time for p in completed) / self.completed_processes
            avg_turnaround_time = sum(p.turnaround_time for p in completed) / self.completed_processes
            avg_response_time = sum(p.response_time for p in completed) / self.completed_processes
        else:
            avg_waiting_time = 0.0
            avg_turnaround_time = 0.0
            avg_response_time = 0.0

        # Completetion time of last process - first start time of first process
        makespan = completed[-1].completion_time - completed[0].first_start
        
        # Calculate throughput
        throughput = (self.completed_processes / makespan) if makespan > 0 else 0.0

        # Makespan - idle - switch time
        useful_execution = makespan - self.idle_time - self.context_switch_time

        utilization = float(useful_execution) / makespan * 100 if makespan > 0 else 0.0

        return {
            "total_processes": int(total_processes),
            "completed_processes": int(self.completed_processes),
            "avg_waiting_time": float(avg_waiting_time),
            "avg_turnaround_time": float(avg_turnaround_time),
            "avg_response_time": float(avg_response_time),
            "makespan": float(makespan),
            "utilization": float(utilization),
            "throughput": float(throughput),
            "context_switches": int(getattr(self, "context_switch_time", 0) / self.context_switch_cost if self.context_switch_cost > 0 else 0),
            "queue_length": int(len(self.ready_queue)),
        }

    def validate(self) -> List[str]:
        """
        Validate internal configuration and workload state, returning a list of error strings
        """
        errors = []
        valid_algs = ["FCFS", "SJF", "SRTF", "ROUND_ROBIN", "PRIORITY"]
        
        # 1. Validate scheduling algorithm name
        if self.algorithm not in valid_algs:
            errors.append(f"Invalid scheduling algorithm: {self.algorithm}. Must be one of {valid_algs}")
            
        # 2. Validate Round Robin time quantum rules
        if self.algorithm == "ROUND_ROBIN":
            if self.quantum is None or self.quantum < 1:
                errors.append("Round Robin scheduling requires a time quantum of at least 1 ms.")
        elif self.quantum is not None and self.quantum > 0:
            errors.append("Time quantum only applies to Round Robin.")
            
        # 3. Validate context switch cost
        if self.context_switch_cost < 0:
            errors.append("Context switch cost cannot be negative.")
            
        # 4. Validate workload
        unique_pids = set()
        for p in self.workload:
            if p.pid in unique_pids:
                errors.append(f"Duplicate process ID detected: {p.pid}")
            unique_pids.add(p.pid)
            
            if p.arrival_time < 0:
                errors.append(f"Process {p.pid} has a negative arrival time: {p.arrival_time}")
            if p.burst_time <= 0:
                errors.append(f"Process {p.pid} must have a positive burst time: {p.burst_time}")
            if p.priority < 0:
                errors.append(f"Process {p.pid} has an invalid negative priority: {p.priority}")

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
                "quantum": self.quantum,
                "context_switch_cost": self.context_switch_cost,
            },
            "metrics": self.metrics(),
            "snapshot": self.snapshot(),
            "gantt_chart_csv": self._gantt_chart(),
            "processes": [
                {
                    "pid": p.pid,
                    "owner_id": p.owner_id,
                    "arrival_time": p.arrival_time,
                    "burst_time": p.burst_time,
                    "priority": p.priority,
                    "state": p.state.value,
                    "completion_time": getattr(p, "completion_time", None),
                    "turnaround_time": getattr(p, "turnaround_time", -1),
                    "response_time": getattr(p, "response_time", -1),
                    "wait_time": getattr(p, "wait_time", -1),
                }
                for p in self.workload
            ]
        }

        if format_lower == "json":
            return export_data
        elif format_lower == "csv":
            # CSV formatting for per-process metrics
            csv_lines = ["pid,arrival_time,burst_time,priority,state,completion_time,turnaround_time,wait_time,response_time"]
            for p in self.workload:
                csv_lines.append(
                    f"{p.pid},{p.arrival_time},{p.burst_time},{p.priority},{p.state.value},"
                    f"{getattr(p, 'completion_time', '')},{getattr(p, 'turnaround_time', -1)},"
                    f"{getattr(p, 'wait_time', -1)},{getattr(p, 'response_time', -1)}"
                )
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {export_format}. Use 'json' or 'csv'.")

    def is_finished(self) -> bool:
        """
        Returns True if all loaded processes have reached the TERMINATED state.
        Used by the simulation controller to determine run completion.
        """
        if not self.workload:
            return False
        return all(p.state == ProcessState.TERMINATED for p in self.workload)

    def is_idle(self) -> bool:
        """
        Returns True if the CPU has no running process, no items in the ready queue,
        no pending context switch ticks, and no new processes left to arrive.
        """
        has_future_arrivals = any(p.state == ProcessState.NEW for p in self.workload)
        return (
            self.running_process is None 
            and not self.ready_queue 
            and self.cs_ticks_remaining == 0 
            and not has_future_arrivals
        )

    # Manager helper functions

    def _update_ready_queue(self) -> List[EventRecord]:
        """
        Move newly arrived processes into the readyq and create event.
        Re-sort ready queue based on algorithm.
        Age priority when applicable
        """

        events: List[EventRecord] = []
            # Check if any new processes have arrived
        for p in self.workload:
            if p.arrival_time == self.current_time:
                # Add new processes to rq and set to READY
                self.ready_queue.append(p)
                p.state = ProcessState.READY
                # Create event
                events.append(EventRecord(
                    timestamp=self.current_time,
                    manager="Process",
                    event_type="PROCESS_ARRIVE",
                    entity_id=p.pid,
                    action="ADMIT",
                    previous_state="NEW",
                    new_state="READY",
                    outcome="SUCCESS"
                ))

        
        if self.algorithm == "SJF" or self.algorithm == "SRTF":
            self.ready_queue.sort(key=lambda p: (p.remaining_time, p.arrival_time)) # Second sorting criterea arrival time to break ties
        
        elif self.algorithm == "PRIORITY":
            self.ready_queue.sort(key=lambda p: (p.priority, p.arrival_time)) # Second sorting criterea arrival time to break ties

            # Age Waiting Processes
            if self.aging_interval > 0:
                for p in self.ready_queue:
                    response = p.first_start - p.arrival_time if p.first_start != -1 else 0
                    execution_time = p.burst_time - p.remaining_time
                    current_waiting_time = self.current_time - execution_time - response

                    if current_waiting_time % self.aging_interval == 0 and p.priority > 0:
                        p.priority -= 1
                        # Create event
                        events.append(EventRecord(
                            timestamp=self.current_time,
                            manager="Process",
                            event_type="PROCESS_AGE",
                            entity_id=p.pid,
                            action="AGE_PRIORITY",
                            previous_state="READY",
                            new_state=f"READY",
                            outcome="SUCCESS"
                        ))

        return events

        
    def _select_work(self) -> List[EventRecord]:
        """
        Select the next process to run based on algorithm, the ready queue, and the current process (skipped during a context switch)
        """
        events: List[EventRecord] = []

        if self.algorithm in ["SJF", "FCFS", "PRIORITY"]: # Non preemptive work selection
            
            if self.running_process == None: # If the cpu is idle select next process
                if not self.ready_queue:
                    # cpu idle
                    print()
                else:
                    # Set next process as running process, change its state, set start time
                    self.running_process = self.ready_queue.pop(0)
                    self.running_process.state = ProcessState.RUNNING
                    self.running_process.first_start = self.current_time
                    self.running_process.dispatches += 1
                    

                    # Create event
                    events.append(EventRecord(
                        timestamp=self.current_time,
                        manager="Process",
                        event_type="PROCESS_DISPATCH",
                        entity_id=self.running_process.pid,
                        action="DISPATCH",
                        previous_state="READY",
                        new_state="RUNNING",
                        outcome="SUCCESS"
                    ))
        
        elif self.algorithm == "SRTF": # Preemptive SRTF work selection
            
            if self.running_process and self.ready_queue: # Preemption check while cpu is running and readyq has items
                preempt = False
                next_process = self.ready_queue[0]

                # Evaluate if preempt is necessary
                if next_process.remaining_time < self.running_process.remaining_time: # Preempt Condition
                    preempt = True
                elif next_process.remaining_time == self.running_process.remaining_time: # Tiebreak condition
                        # Break based on arrival order: If current process arrived before or at the same time as next process, it stays
                        if next_process.arrival_time < self.running_process.arrival_time:
                            preempt = True
                # Preempt
                if preempt == True:
                    # Requeue current process
                    self.running_process.state = ProcessState.READY
                    self.ready_queue.append(self.running_process)
                    self.running_process.preemptions += 1

                    # Create event
                    events.append(EventRecord(
                        timestamp=self.current_time,
                        manager="Process",
                        event_type="PROCESS_PREEMPT",
                        entity_id=self.running_process.pid,
                        action="REQUEUE",
                        previous_state="RUNNING",
                        new_state="READY",
                        outcome="SUCCESS"
                    ))

                    self.running_process = None
                    # Start context switch if applicable
                    if self.context_switch_cost > 0:
                        self.cs_ticks_remaining = self.context_switch_cost

            if self.running_process == None and self.cs_ticks_remaining == 0: # If the cpu is idle and not in a cs, select next process
                if not self.ready_queue:
                    # cpu idle
                    print()
                else:
                    # Set next process as running process, change its state, set start time
                    self.running_process = self.ready_queue.pop(0)
                    self.running_process.state = ProcessState.RUNNING
                    self.running_process.first_start = self.current_time if self.running_process.first_start == -1 else self.running_process.first_start
                    self.running_process.dispatches += 1

                    # Create event
                    events.append(EventRecord(
                        timestamp=self.current_time,
                        manager="Process",
                        event_type="PROCESS_DISPATCH",
                        entity_id=self.running_process.pid,
                        action="DISPATCH",
                        previous_state="READY",
                        new_state="RUNNING",
                        outcome="SUCCESS"
                    ))
        
        elif self.algorithm == "ROUND_ROBIN": # Preemptive RR selection

            if self.running_process == None and self.cs_ticks_remaining == 0: # If the cpu is idle and not in a cs, select next process
                if not self.ready_queue:
                    # cpu idle
                    print()
                else:
                    # Set next process as running process, change its state, set start time
                    self.running_process = self.ready_queue.pop(0)
                    self.running_process.state = ProcessState.RUNNING
                    self.running_process.first_start = self.current_time if self.running_process.first_start == -1 else self.running_process.first_start
                    self.running_process.dispatches += 1
                    self.slice = self.quantum

                    # Create event
                    events.append(EventRecord(
                        timestamp=self.current_time,
                        manager="Process",
                        event_type="PROCESS_DISPATCH",
                        entity_id=self.running_process.pid,
                        action="DISPATCH",
                        previous_state="READY",
                        new_state="RUNNING",
                        outcome="SUCCESS"
                    ))
            
        return(events)


    def _execute_work(self) -> List[EventRecord]:
        events: List[EventRecord] = []

        # Skip execution during a context switch
        if self.cs_ticks_remaining > 0:
            self.cs_ticks_remaining -= 1
            self.context_switch_time += 1
            self.gantt_ticks.append({
                "start": self.current_time - 1,
                "end": self.current_time,
                "label": "cs"
            })

            if self.cs_ticks_remaining == 0:
                self._select_work()

            return events

        # Check if there is a process in CPU
        if self.running_process:

            # Simulate execution, decrement slice if applicaple
            self.running_process.remaining_time -= 1
            if self.algorithm == "ROUND_ROBIN" and self.slice > 0:
                self.slice -= 1

            # Record tick for the running process
            self.gantt_ticks.append({
                "start": self.current_time - 1,
                "end": self.current_time,
                "label": self.running_process.pid
            })
           
            # Process cleanup and metric calculation
            if self.running_process.remaining_time == 0:
                p = self.running_process
                self.running_process = None

                p.state = ProcessState.TERMINATED
                p.completion_time = self.current_time
                p.turnaround_time = p.completion_time - p.arrival_time
                p.response_time = p.first_start - p.arrival_time
                p.wait_time = p.turnaround_time - p.burst_time
                self.completed_processes += 1

                # Create termination event
                events.append(EventRecord(
                    timestamp=self.current_time,
                    manager="Process",
                    event_type="PROCESS_TERMINATE",
                    entity_id=p.pid,
                    action="TERMINATE",
                    previous_state="RUNNING",
                    new_state="TERMINATED",
                    outcome="SUCCESS"
                ))

            # Only preempt process after slice ending IF there are processes waiting in the readyq, otherwise continue
            elif self.algorithm == "ROUND_ROBIN" and self.slice == 0:
                if self.ready_queue:
                    p = self.running_process
                    p.state = ProcessState.READY
                    self.ready_queue.append(p)
                    p.preemptions += 1

                    events.append(EventRecord(
                        timestamp=self.current_time,
                        manager="Process",
                        event_type="PROCESS_PREEMPT",
                        entity_id=p.pid,
                        action="QUANTUM_EXPIRED",
                        previous_state="RUNNING",
                        new_state="READY",
                        outcome="SUCCESS"
                    ))

                    self.running_process = None
                    if self.context_switch_cost > 0:
                        self.cs_ticks_remaining = self.context_switch_cost
                else:
                    self.slice = self.quantum
        else:
            self.idle_time += 1
            self.gantt_ticks.append({
                "start": self.current_time - 1,
                "end": self.current_time,
                "label": "idle"
            })


    def _gantt_chart(self) -> str:
        """
        Compresses tick records into [start, end) intervals  and returns a CSV string with columns: start,end,label
        """
        csv_lines = ["start,end,label"]
        if not self.gantt_ticks:
            return "\n".join(csv_lines)

        compressed = []
        current_interval = self.gantt_ticks[0].copy()

        for tick in self.gantt_ticks[1:]:
            if tick["label"] == current_interval["label"] and tick["start"] == current_interval["end"]:
                current_interval["end"] = tick["end"]
            else:
                compressed.append(current_interval)
                current_interval = tick.copy()
        compressed.append(current_interval)

        for interval in compressed:
            csv_lines.append(f"{interval['start']},{interval['end']},{interval['label']}")

        return "\n".join(csv_lines)