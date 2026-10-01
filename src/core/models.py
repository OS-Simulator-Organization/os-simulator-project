from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ==========================================
# System States and Enumerations
# ==========================================

class ProcessState(Enum):
    """Lifecycle states for a process."""
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


class DeviceType(Enum):
    """Categories of system devices managed by the device manager."""
    DISK = "DISK"
    PRINTER = "PRINTER"
    KEYBOARD = "KEYBOARD"


# Entity Models

# Process Manager
@dataclass
class Process:
    """Represents a process scheduled or managed by the operating system."""
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
    """Represents a physical memory frame and its virtual page mapping."""
    frame_id: int
    page_number: Optional[int] = None
    pid: Optional[str] = None
    is_modified: bool = False
    last_accessed: int = 0


# File System Manager
@dataclass
class FileNode:
    """Represents a file or directory node in the virtual file system tree."""
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
    """Represents a registered user account in the system."""
    user_id: str
    username: str
    role: str
    permissions: List[str] = field(default_factory=list)


@dataclass
class SecurityContext:
    """Represents an active authenticated session or security context."""
    context_id: str
    user_id: str
    token: str
    effective_permissions: List[str] = field(default_factory=list)


# Device Manager
@dataclass
class DeviceRequest:
    """Represents an I/O request submitted by a process to a target device."""
    request_id: str
    device_id: str
    process_id: str
    operation_type: str
    status: str = "PENDING"  # Supported states: PENDING, IN_PROGRESS, COMPLETED, FAILED


# Network Manager
@dataclass
class Packet:
    """Represents a network packet moving between network nodes."""
    packet_id: str
    source_node: str
    dest_node: str
    source_process_id: str
    payload_size: int
    hop_limit: int = 64
    creation_time: int = 0
    status: str = "QUEUED"  # Supported states: QUEUED, TRANSMITTING, DELIVERED, DROPPED