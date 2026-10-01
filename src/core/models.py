from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# System States and Enumerations

class ProcessState(Enum):
    """Lifecycle states for a process[cite: 3, 4]."""
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


class DeviceType(Enum):
    """Categories of system devices managed by the device manager[cite: 3, 4]."""
    DISK = "DISK"
    PRINTER = "PRINTER"
    KEYBOARD = "KEYBOARD"
    DISPLAY = "DISPLAY"
    SENSOR = "SENSOR"


class DeviceState(Enum):
    """Operational states for physical/simulated devices[cite: 1]."""
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class DeviceRequestStatus(Enum):
    """Lifecycle states for an I/O device request[cite: 1, 3, 4]."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class PacketStatus(Enum):
    """Lifecycle states for a network packet[cite: 1, 3, 4]."""
    QUEUED = "QUEUED"
    TRANSMITTING = "TRANSMITTING"
    DELIVERED = "DELIVERED"
    DROPPED = "DROPPED"
    EXPIRED = "EXPIRED"


class TaskState(Enum):
    """Lifecycle states for parallel tasks/threads[cite: 1]."""
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"



# Entity Models

# Process Manager
@dataclass
class Process:
    """Represents a process scheduled or managed by the operating system[cite: 3, 4]."""
    pid: str
    owner_id: str
    arrival_time: int
    burst_time: int
    priority: int
    remaining_time: int
    state: ProcessState = ProcessState.NEW
    allocated_frames: List[int] = field(default_factory=list)
    open_files: List[str] = field(default_factory=list)


# Memory Manager
@dataclass
class PageFrame:
    """Represents a physical memory frame and its virtual page mapping[cite: 3, 4]."""
    frame_id: int
    page_number: Optional[int] = None
    pid: Optional[str] = None
    is_modified: bool = False
    last_accessed: int = 0


# File System Manager
@dataclass
class FileNode:
    """Represents a file or directory node in the virtual file system tree[cite: 3, 4]."""
    path: str
    name: str
    is_dir: bool
    owner_id: str
    permissions: str = "rwx"
    size: int = 0
    content: str = ""
    parent_path: Optional[str] = None
    created_at: int = 0
    modified_at: int = 0
    children: Dict[str, "FileNode"] = field(default_factory=dict)


# Security Manager
@dataclass
class User:
    """Represents a registered user account in the system[cite: 3, 4]."""
    user_id: str
    username: str
    role: str
    permissions: List[str] = field(default_factory=list)


@dataclass
class SecurityContext:
    """Represents an active authenticated session or security context[cite: 3, 4]."""
    context_id: str
    user_id: str
    token: str
    effective_permissions: List[str] = field(default_factory=list)


# Device Manager
@dataclass
class Device:
    """Represents a simulated hardware device[cite: 1]."""
    device_id: str
    device_type: DeviceType
    state: DeviceState = DeviceState.AVAILABLE
    current_request_id: Optional[str] = None


@dataclass
class DeviceRequest:
    """Represents an I/O request submitted by a process to a target device[cite: 3, 4]."""
    request_id: str
    device_id: str
    process_id: str
    operation_type: str
    status: DeviceRequestStatus = DeviceRequestStatus.PENDING
    arrival_time: float = 0.0
    start_time: Optional[float] = None
    completion_time: Optional[float] = None


# Network Manager
@dataclass
class Packet:
    """Represents a network packet moving between network nodes[cite: 3, 4]."""
    packet_id: str
    source_node: str
    dest_node: str
    source_process_id: str
    payload_size: int
    ttl: int = 64
    priority: int = 0
    creation_time: float = 0.0
    status: PacketStatus = PacketStatus.QUEUED


# Parallel Computing Component
@dataclass
class Task:
    """Represents a task/thread scheduled across parallel cores[cite: 1]."""
    task_id: str
    parent_job_id: str
    arrival_time: float
    work_burst: float
    priority: int = 0
    assigned_core: Optional[int] = None
    state: TaskState = TaskState.NEW
    dependencies: List[str] = field(default_factory=list)


@dataclass
class SynchronizationPrimitive:
    """Represents a lock, semaphore, or barrier for task synchronization[cite: 1]."""
    primitive_id: str
    type_name: str  # "MUTEX", "SEMAPHORE", "BARRIER"
    is_locked: bool = False
    counter: int = 1
    waiting_tasks: List[str] = field(default_factory=list)
