# src/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

# =====================================================================
# SYSTEM STATES & ENUMS (Used across all managers to track status)
# =====================================================================

class ProcessState(Enum):
    NEW = "NEW"           # Just created, waiting to enter ready queue
    READY = "READY"       # In ready queue, waiting for CPU time
    RUNNING = "RUNNING"   # Currently executing on CPU
    BLOCKED = "BLOCKED"   # Waiting on I/O, page fault, or network packet
    TERMINATED = "TERMINATED"  # Finished execution, resources being freed


class DeviceType(Enum):
    DISK = "DISK"         # Storage drive (uses SSTF / SCAN scheduling)
    PRINTER = "PRINTER"   # Output device (uses FCFS)
    KEYBOARD = "KEYBOARD" # Input device (uses FCFS)


# =====================================================================
# 1. PROCESS MANAGER ENTITIES
# =====================================================================

@dataclass
class Process:
    pid: str                    # Unique process identifier (e.g., "P1")
    owner_id: str               # User ID who launched this process (for security)
    arrival_time: int          # Clock tick when process arrives in system
    burst_time: int            # Total CPU time needed to complete
    priority: int              # Priority level (for Priority scheduling algorithms)
    remaining_time: int        # CPU time left (used for SRTF & Round-Robin)
    state: ProcessState = ProcessState.NEW
    
    # Resource handles currently held by this process (cleaned up on termination)
    allocated_frames: List[int] = field(default_factory=list) # Memory frames held
    open_files: List[str] = field(default_factory=list)       # Open file handles held


# =====================================================================
# 2. MEMORY MANAGER ENTITIES
# =====================================================================

@dataclass
class PageFrame:
    frame_id: int              # Physical memory slot number in hardware
    page_number: Optional[int] = None # Virtual page currently loaded inside frame
    pid: Optional[str] = None  # Process owning this page frame
    is_modified: bool = False     # True if memory was modified (needs write back)
    last_accessed: int = 0     # Timestamp of last access (used for LRU replacement)


# =====================================================================
# 3. FILE SYSTEM MANAGER ENTITIES
# =====================================================================

@dataclass
class FileNode:
    path: str                  # Absolute path (e.g., "/docs/notes.txt")
    name: str                  # File or folder name (e.g., "notes.txt")
    is_dir: bool               # True if folder, False if file
    owner_id: str              # User who created this node
    permissions: str = "rwx"    # Access rights string (e.g., "rwx")
    size: int = 0              # File size in bytes (0 for directories)
    content: str = ""          # File text content (empty for directories)
    
    # Navigation & Metadata Properties
    parent_path: Optional[str] = None  # Enables upward tree navigation (e.g., "cd ..")
    created_at: int = 0               # Simulation tick when created
    modified_at: int = 0              # Simulation tick when last updated
    
    # Nested Children Dictionary:
    # Keys are child names (e.g., "notes.txt"), Values are complete child FileNode objects!
    children: Dict[str, 'FileNode'] = field(default_factory=dict)


# =====================================================================
# 4. SECURITY MANAGER ENTITIES
# =====================================================================

@dataclass
class User:
    user_id: str               # Unique user ID (e.g., "U101")
    username: str              # Login handle (e.g., "admin")
    role: str                  # Role level (e.g., "ADMIN", "GUEST")
    permissions: List[str] = field(default_factory=list) # Assigned permission flags


@dataclass
class SecurityContext:
    context_id: str            # Active session ID
    user_id: str               # User associated with this active session
    token: str                  # Temporary authentication token
    effective_permissions: List[str] = field(default_factory=list) # Active rights


# =====================================================================
# 5. DEVICE MANAGER ENTITIES
# =====================================================================

@dataclass
class DeviceRequest:
    request_id: str            # Unique request ID
    device_id: str             # Target device ID (e.g., "DISK_1")
    process_id: str            # Process requesting the I/O operation
    operation_type: str        # Operation requested: "READ", "WRITE"
    status: str = "PENDING"    # "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"


# =====================================================================
# 6. NETWORK MANAGER ENTITIES
# =====================================================================

@dataclass
class Packet:
    packet_id: str             # Unique network packet ID
    source_node: str           # Source node ID
    dest_node: str             # Target node ID
    source_process_id: str     # Process that sent the packet
    payload_size: int          # Packet size in bytes
    hop_limit: int = 64        # Time-To-Live (decrements on each hop)
    creation_time: int = 0     # Clock tick when packet was sent
    status: str = "QUEUED"     # "QUEUED", "TRANSMITTING", "DELIVERED", "DROPPED"