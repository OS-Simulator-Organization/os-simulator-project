from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


# SYSTEM STATES & ENUMS (Used across all managers to track status)
class ProcessState(Enum):
    NEW = "NEW"           
    READY = "READY"       
    RUNNING = "RUNNING"   
    WAITING = "WAITING"   # Waiting on I/O, page fault, or network packet
    TERMINATED = "TERMINATED"  

class DeviceType(Enum):
    DISK = "DISK"         # Storage drive (uses SSTF / SCAN scheduling)
    PRINTER = "PRINTER"   # Output device (uses FCFS)
    KEYBOARD = "KEYBOARD" # Input device (uses FCFS)


class DeviceOperation(Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"

class DeviceRequestStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED" 

class PacketStatus(Enum):
    QUEUED = "QUEUED"
    TRANSMITTING = "TRANSMITTING"
    DELIVERED = "DELIVERED"
    DROPPED = "DROPPED"

# 1. PROCESS MANAGER ENTITIES
@dataclass
class Process:
    pid: str                    
    owner_id: str               
    arrival_time: int         
    burst_time: int            
    priority: int              
    remaining_time: int        # CPU time left (used for SRTF & Round-Robin)
    state: ProcessState = ProcessState.NEW
    
    # Resource handles currently held by this process (cleaned up on termination)
    allocated_frames: List[int] = field(default_factory=list) 
    open_files: List[str] = field(default_factory=list)       


# 2. MEMORY MANAGER ENTITIES
@dataclass
class PageFrame:
    frame_id: int              # Physical memory slot number in hardware
    page_number: Optional[int] = None # Virtual page currently loaded inside frame
    pid: Optional[str] = None  
    is_modified: bool = False     
    last_accessed: int = 0     

# 3. FILE SYSTEM MANAGER ENTITIES
@dataclass
class FileNode:
    path: str                  # Absolute path (e.g., "/docs/notes.txt")
    name: str                  # File or folder name (e.g., "notes.txt")
    is_dir: bool               # True if folder, False if file
    owner_id: str             
    permissions: str = "rwx"   
    size: int = 0             
    content: str = ""          
    
    # Navigation & Metadata Properties
    parent_path: Optional[str] = None  # Enables upward tree navigation (e.g., "cd ..")
    created_at: int = 0               
    modified_at: int = 0              
    
    # Nested Children Dictionary:
    # Keys are child names (e.g., "notes.txt"), Values are complete child FileNode objects
    children: Dict[str, 'FileNode'] = field(default_factory=dict)



# 4. SECURITY MANAGER ENTITIES
@dataclass
class User:
    user_id: str               
    username: str              
    role: str                  
    permissions: List[str] = field(default_factory=list) # Assigned permission flags


@dataclass
class SecurityContext:
    context_id: str            # Active session ID
    user_id: str               
    token: str                 # Temporary authentication token
    effective_permissions: List[str] = field(default_factory=list) # Active rights



# 5. DEVICE MANAGER ENTITIES
@dataclass
class DeviceRequest:
    request_id: str            
    device_id: str             # Target device ID (e.g., "DISK_1")
    process_id: str            
    operation_type: str        
    status:DeviceRequestStatus = DeviceRequestStatus.PENDING



# 6. NETWORK MANAGER ENTITIES
@dataclass
class Packet:
    packet_id: str            
    source_node: str          
    dest_node: str             
    source_process_id: str     #
    payload_size: int          # Packet size in bytes
    hop_limit: int = 64        # Time-To-Live (decrements on each hop)
    creation_time: int = 0     
    status: PacketStatus = PacketStatus.QUEUED