# Shared Data Model Specification

## Overview
The Shared Data Model serves as the central state repository for all six OS managers (Process, Memory, File System, Security, Device, Network). It contains no domain logic or scheduling algorithms; it only stores system entity states.

## Core Entities

### 1. Process (`Process`)
Represents an OS process managed by the Process Manager.
- `pid` (str): Unique process identifier.
- `owner_id` (str): User ID associated with the process owner.
- `arrival_time` (int): Simulation tick when the process arrives.
- `burst_time` (int): Total CPU time required.
- `remaining_time` (int): CPU time remaining (used for SRTF and Round-Robin).
- `priority` (int): Priority level (used for Priority scheduling with aging).
- `state` (ProcessState): Current state (`NEW`, `READY`, `RUNNING`, `BLOCKED`, `TERMINATED`).

### 2. PageFrame (`PageFrame`)
Represents a physical/simulated memory slot managed by the Memory Manager.
- `frame_id` (int): Hardware memory frame index.
- `page_number` (int): Virtual page number currently loaded.
- `pid` (str): Process owning this frame.
- `last_accessed` (int): Simulation tick of last access (used for LRU replacement).

### 3. FileNode (`FileNode`)
Represents a node in the hierarchical file system managed by the File System Manager.
- `path` (str): Absolute file system path (e.g., `/docs/file.txt`).
- `is_dir` (bool): Identifies if the node is a directory or file.
- `owner_id` (str): Creator user ID.
- `permissions` (str): Access rights string (e.g., `rwx`).

### 4. SecurityContext & User (`User`, `SecurityContext`)
Handles authentication and authorization data for the Security Manager.
- Stores user roles, permission lists, and active session tokens.

### 5. DeviceRequest (`DeviceRequest`)
Represents an I/O request queued for hardware devices (Disk, Printer, Keyboard).

### 6. Packet (`Packet`)
Represents network communication data transmitted across nodes by the Network Manager.