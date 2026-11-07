# Tie-Breaking Documentation

This document outlines the tie-breaking criteria used in each CPU scheduling and memry page replacement algorithm in the OS simulator.

## CPU Scheduling Algorithms

CPU tie-breaking happens during Ready Queue updates and sorting (at process arrival or unblocking) and during preemption checks when selecting the next process to execute.

### Typical Ordering

When multiple processes share the same parameters (burst time, remaining time, priority), ties are broken using a specific order of comparisons:

1. Primary Algorithm Metric (Burst Time, Remaining Time, or Priority Level)

2. Arrival Time (earlier arrival gets higher preference)

3. Process ID (numerical order)

## Scheduling Algorithms

### 1. First-Come, First-Served (FCFS)

* Type: Non-preemptive

* Sorting: Ready queue maintains arrival order based on process admission time.

* Tie-Breaking Rule:

  - If two processes arrive at the exact same tick (arrival_time), they are admitted to the ready queue in the order they appear in the workload list or processing array.
  - Execution follows standard First-In, First-Out queue ordering based on arrival order.

### 2. Shortest Job First (SJF)

* Type: Non-preemptive

* Primary Sorting: Lowest remaining_time (initial total burst time upon arrival).

* Tie-Breaking Rule:

  - 1st Tie-Breaker: Earliest arrival_time.

  - 2nd Tie-Breaker: Process ID comparison.

* Implementation:
  ready_queue.sort(key=lambda p: (p.remaining_time, p.arrival_time, p.pid))



### 3. Shortest Remaining Time First (SRTF)
* Type: Preemptive

* Primary Sorting: Lowest remaining_time.

* Tie-Breaking Rule:

  - 1st Tie-Breaker: Earliest arrival_time.

  - 2nd Tie-Breaker: Process ID comparison.

* Implementation:
  ready_queue.sort(key=lambda p: (p.remaining_time, p.arrival_time, p.pid))


* Preemption Checks: When evaluating whether a newly ready/arrived process should preempt the currently RUNNING process, tuple comparison is enforced:

    * Preemption occurs ONLY if: tuple(next_process) < tuple(running_process) where tuple = (remaining_time, arrival_time, pid).

    * If next_process and running_process have equal remaining_time, preemption only happens the if next_process arrived earlier 
    
    * If next_process and running_process have equal arrival_time, preemption only happens if next_process has a lower pid 

   * Implementation:\
   next_tuple = (next_process.remaining_time, next_process.arrival_time, next_process.pid)\
   running_tuple = (self.running_process.remaining_time, self.running_process.arrival_time, self.running_process.pid)\
   if next_tuple < running_tuple:
      preempt = True


### 4. Priority Scheduling
* Type: Non-preemptive (with optional Aging support)

* Primary Sorting: Lowest priority (Lower numerical value = Higher priority).

* Tie-Breaking Rule:

  - 1st Tie-Breaker: Earliest arrival_time.

  - 2nd Tie-Breaker: Process ID comparison.

* Implementation Reference:\
  ready_queue.sort(key=lambda p: (p.priority, p.arrival_time, p.pid))

* Aging Consideration: When aging is enabled (aging_interval > 0), waiting processes decrease their priority numerical value by 1 every aging_interval ticks. Re-sorting after aging preserves the arrival time and PID tie-breaker order.



### 5. Round Robin (RR)
* Type: Preemptive (Time Quantum-based)

* Queue Behavior: FIFO behavior, no sorting.

* Tie-Breaking Rule:

  - Processes arriving at the exact same tick are appended to the tail of the ready queue in order of workload intake (usually Process ID).

  - Upon time quantum expiration (slice == 0):

    * If other processes exist in the ready queue, the preempted process is appended to the back of the queue, allowing the head of the queue to be dispatched next.

    * If the ready queue is empty when quantum expires, the running process continues for another quantum slice without context switching.



## Memory Page Replacement Algorithms
Memory page eviction tie-breaking occurs when a page fault happens and all physical frames are allocated

### 6. Least Recently Used (LRU)
* Policy: Evicts the page frame whose contents were accessed furthest in the past.

* Primary Target: Minimum last_accessed tick timestamp.

* Tie-Breaking Rule:

  - 1st Tie-Breaker: Oldest page (Earliest load_tick).

  - 2nd Tie-Breaker: Lowest physical frame_id.

* Implementation Reference:\

  target_frame = min(self.frames, key=lambda f: (f.last_accessed, f.load_tick, f.frame_id))



### 7. First-In, First-Out (FIFO)
* Policy: Evicts the oldest loaded physical frame.

* Primary Target: First entry in the FIFO queue (oldest page).

* Tie-Breaking Rule:

    * 1st Tie-Breaker: Minimum load_tick timestamp.

    * 2nd Tie-Breaker: Lowest physical frame_id.

* Implementation Reference:\

  target_frame = min(self.frames, key=lambda f: (f.load_tick, f.frame_id))
  Optimal (OPT)



### 8. Optimal
* Policy: Evicts the page frame whose contents will be accessed furthest in the future.

* Primary Target: Maximum next_access tick timestamp (or infinity if never accessed again).

* Tie-Breaking Rule:

    * 1st Tie-Breaker: Oldest page (Earliest load_tick).

    * 2nd Tie-Breaker: Lowest physical frame_id.

* Implementation Reference:\

  target_frame = max(self.frames, key=lambda f: (f.next_access, -f.load_tick, f.frame_id))
