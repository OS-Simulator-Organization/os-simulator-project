# Shared Data Model (`src/core/models.py`)

This document outlines the core entities and enumeration states maintained in `src/core/models.py`.

---

## 1. System States and Enumerations

| Enumeration | Allowed Values | Description |
| :--- | :--- | :--- |
| **`ProcessState`** | `NEW`, `READY`, `RUNNING`, `WAITING`, `TERMINATED` | OS process scheduling states[cite: 3, 4]. |
| **`DeviceType`** | `DISK`, `PRINTER`, `KEYBOARD`, `DISPLAY`, `SENSOR` | Hardware device categories managed by the system[cite: 3, 4]. |
| **`DeviceState`** | `AVAILABLE`, `BUSY`, `OFFLINE`, `ERROR` | Hardware operational statuses[cite: 1]. |
| **`DeviceRequestStatus`** | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELED` | Lifecycle tracking for I/O requests[cite: 1, 3, 4]. |
| **`PacketStatus`** | `QUEUED`, `TRANSMITTING`, `DELIVERED`, `DROPPED`, `EXPIRED` | Lifecycle tracking for network packets[cite: 1, 3, 4]. |
| **`TaskState`** | `NEW`, `READY`, `RUNNING`, `BLOCKED`, `COMPLETED` | Multicore parallel thread/task execution states[cite: 1]. |

---

## 2. Entity Models

### 1. Process Manager
* **`Process`**: Represents an OS process[cite: 3, 4].
  * `pid` (*str*): Unique process identifier[cite: 4].
  * `owner_id` (*str*): User ID of the owner[cite: 4].
  * `arrival_time` (*int*): Simulation tick when process arrives[cite: 1, 4].
  * `burst_time` (*int*): Total CPU execution time required[cite: 1, 4].
  * `priority` (*int*): Scheduling priority rank[cite: 1, 4].
  * `remaining_time` (*int*): Remaining CPU burst needed[cite: 4].
  * `state` (*ProcessState*): Current state (default: `NEW`)[cite: 4].
  * `allocated_frames` (*List[int]*): Assigned memory frames[cite: 4].
  * `open_files` (*List[str]*): Active file handles[cite: 4].

### 2. Memory Manager
* **`PageFrame`**: Represents a physical RAM frame[cite: 3, 4].
  * `frame_id` (*int*): Physical frame index[cite: 4].
  * `page_number` (*Optional[int]*): Virtual page mapped to frame[cite: 1, 4].
  * `pid` (*Optional[str]*): Process holding the frame[cite: 4].
  * `is_modified` (*bool*): Dirty bit flag[cite: 1, 4].
  * `last_accessed` (*int*): Clock tick used for LRU eviction[cite: 1, 4].

### 3. File System Manager
* **`FileNode`**: Represents a virtual file or directory[cite: 1, 3, 4].
  * `path` (*str*): Absolute path[cite: 1, 4].
  * `name` (*str*): Node name[cite: 1, 4].
  * `is_dir` (*bool*): True if directory, False if file[cite: 1, 4].
  * `owner_id` (*str*): Owner user ID[cite: 1, 4].
  * `permissions` (*str*): Permission string (e.g., `"rwx"`)[cite: 1, 4].
  * `size` (*int*): File size in bytes[cite: 1, 4].
  * `content` (*str*): Simulated string content[cite: 1, 4].
  * `parent_path` (*Optional[str]*): Path to parent directory[cite: 4].
  * `children` (*Dict[str, FileNode]*): Map of child nodes[cite: 1, 4].

### 4. Security Manager
* **`User`**: Account record[cite: 1, 3, 4].
  * `user_id` (*str*), `username` (*str*), `role` (*str*), `permissions` (*List[str]*)[cite: 4].
* **`SecurityContext`**: Active session token[cite: 3, 4].
  * `context_id` (*str*), `user_id` (*str*), `token` (*str*), `effective_permissions` (*List[str]*)[cite: 4].

### 5. Device Manager
* **`Device`**: Hardware device state[cite: 1].
  * `device_id` (*str*), `device_type` (*DeviceType*), `state` (*DeviceState*), `current_request_id` (*Optional[str]*)[cite: 1, 4].
* **`DeviceRequest`**: I/O queue item[cite: 1, 3, 4].
  * `request_id` (*str*), `device_id` (*str*), `process_id` (*str*), `operation_type` (*str*), `status` (*DeviceRequestStatus*)[cite: 1, 4].

### 6. Network Manager
* **`Packet`**: Transmitted network payload[cite: 1, 3, 4].
  * `packet_id` (*str*), `source_node` (*str*), `dest_node` (*str*), `source_process_id` (*str*), `payload_size` (*int*), `ttl` (*int*), `status` (*PacketStatus*)[cite: 1, 4].

### 7. Parallel Computing Component
* **`Task`**: Multicore execution thread[cite: 1].
  * `task_id` (*str*), `parent_job_id` (*str*), `arrival_time` (*float*), `work_burst` (*float*), `priority` (*int*), `assigned_core` (*Optional[int]*), `state` (*TaskState*), `dependencies` (*List[str]*)[cite: 1].
* **`SynchronizationPrimitive`**: Concurrency control object[cite: 1].
  * `primitive_id` (*str*), `type_name` (*str*: `"MUTEX"`, `"SEMAPHORE"`, or `"BARRIER"`), `is_locked` (*bool*), `counter` (*int*), `waiting_tasks` (*List[str]*)[cite: 1].
